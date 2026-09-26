import pytest
from crucible.failures import FailureClass
from crucible.forge import build, verify_environment
from crucible.harvest import Candidate
from crucible.model_shim import ShimConfig
from crucible.store import Store

CAND = Candidate(slug="demo", source="github",
                 repo_url="https://github.com/x/demo", commit_sha="a" * 40)


@pytest.fixture
def store(tmp_path):
    s = Store(tmp_path / "c.db")
    s.init_db()
    return s


def scripted(*results):
    calls = iter(results)

    async def run(*argv: str, **kw) -> tuple[int, str]:
        return next(calls)
    return run


# What a real `docker image inspect --format {{.Id}}` prints: the
# content-addressed image ID, with a trailing newline.
REAL_IMAGE_ID = "sha256:" + "b" * 64


def docker_like(recorder: list[list[str]] | None = None):
    """A fake that answers each docker command the way docker really answers it.

    `docker image inspect --format '{{index .RepoDigests 0}}'` on a locally
    built, never-pushed image does not print a digest: the field is an empty
    list, so the template errors and docker exits 1. This fake reproduces that,
    which is the behaviour the previous fixture hid by returning a digest for
    any format string.
    """
    async def run(*argv: str, **kw) -> tuple[int, str]:
        if recorder is not None:
            recorder.append(list(argv))
        joined = " ".join(argv)
        if "docker build" in joined:
            return (0, "#8 naming to docker.io/library/crucible\nSuccessfully built")
        if "image inspect" in joined:
            if "RepoDigests" in joined:
                return (1, "Template parsing error: template: :1:2: executing "
                           '"" at <index .RepoDigests 0>: error calling index: '
                           "index out of range: 0\n")
            return (0, REAL_IMAGE_ID + "\n")
        return (1, f"unexpected command: {joined}")
    return run


async def test_a_successful_build_records_a_pinned_digest(store) -> None:
    res = await build(CAND, store=store, run=docker_like())

    assert res.ok and res.image_digest == REAL_IMAGE_ID
    row = store.rows("builds")[0]
    assert row["status"] == "built" and row["image_digest"] == res.image_digest


async def test_the_pin_is_read_from_the_image_id_not_from_repodigests(store) -> None:
    """RepoDigests is empty for an image we built and never pushed, so asking
    for it fails every build. Regression guard: if this assertion is ever
    relaxed back to RepoDigests, no build can succeed against real Docker."""
    argv_seen: list[list[str]] = []
    res = await build(CAND, store=store, run=docker_like(argv_seen))

    inspect = [a for a in argv_seen if "inspect" in a]
    assert inspect, "build never inspected the image it produced"
    assert "{{.Id}}" in inspect[0]
    assert not any("RepoDigests" in part for part in inspect[0])
    assert res.ok and res.image_digest is not None
    assert res.image_digest.startswith("sha256:")


async def test_a_failed_build_is_recorded_with_its_class_and_full_log(store) -> None:
    log = "ERROR: Could not find a version that satisfies the requirement foo"
    res = await build(CAND, store=store, run=scripted((1, log)))

    assert not res.ok
    assert res.failure is FailureClass.DEPENDENCY_CONFLICT
    row = store.rows("builds")[0]
    assert row["status"] == "failed"
    assert row["failure_class"] == "dependency_conflict"
    assert store.read_blob(row["log_ref"]).decode() == log


async def test_a_build_never_records_a_digest_it_could_not_read(store) -> None:
    """Recording a placeholder digest would break reproducibility silently."""
    res = await build(CAND, store=store, run=scripted((0, "built"), (1, "no such image")))
    assert not res.ok
    assert res.failure is FailureClass.BUILD_FAILED
    assert store.rows("builds")[0]["image_digest"] is None


async def test_a_container_whose_probe_runs_to_completion_passes(store) -> None:
    res = await verify_environment("sha256:" + "b" * 64, store=store,
                                   run=scripted((0, "crucible environment probe ok")))
    assert res.ok and res.failure is FailureClass.NONE
    assert store.rows("env_checks")[0]["status"] == "passed"


async def test_a_container_whose_probe_exits_non_zero_is_a_failed_check(store) -> None:
    """It built fine and its environment is still broken. Reporting it as a
    successful build would overstate viability."""
    res = await verify_environment("sha256:" + "b" * 64, store=store,
                            run=scripted((1, "Traceback: ModuleNotFoundError")))
    assert not res.ok and res.failure is FailureClass.ENV_CHECK_FAILED
    assert store.rows("env_checks")[0]["status"] == "failed"


async def test_a_container_that_hangs_is_a_timeout_not_a_failure(store) -> None:
    async def hangs(*argv, **kw):
        raise TimeoutError()
    res = await verify_environment("sha256:" + "b" * 64, store=store, run=hangs)
    assert res.failure is FailureClass.ENV_CHECK_TIMEOUT


async def test_evidence_is_always_stored_even_on_success(store) -> None:
    res = await verify_environment("sha256:" + "b" * 64, store=store, run=scripted((0, "ready")))
    assert store.read_blob(res.evidence_ref)


async def test_the_check_passes_the_shim_env_into_the_container(store) -> None:
    """The env is what a later phase varies when it does invoke the agent, and
    the row pins what it ran under."""
    captured: list[str] = []

    async def recording(*argv: str, **kw) -> tuple[int, str]:
        captured.extend(argv)
        return (0, "ready")

    cfg = ShimConfig(base_url="http://ollama:11434/v1", model="qwen2.5-coder:7b")
    await verify_environment("sha256:" + "b" * 64, store=store, run=recording, shim=cfg)

    assert "-e" in captured
    idx = captured.index("-e")
    assert captured[idx + 1] == "OPENAI_BASE_URL=http://ollama:11434/v1"


async def test_the_check_without_a_shim_passes_no_env_flags(store) -> None:
    captured: list[str] = []

    async def recording(*argv: str, **kw) -> tuple[int, str]:
        captured.extend(argv)
        return (0, "ready")

    await verify_environment("sha256:" + "b" * 64, store=store, run=recording)

    assert "-e" not in captured


async def test_a_build_row_pins_the_commit_it_built(store) -> None:
    """A row pinning only the slug resolves to no single commit once a
    repository has been harvested twice at two different HEADs."""
    await build(CAND, store=store, run=docker_like())
    row = store.rows("builds")[0]
    assert row["commit_sha"] == CAND.commit_sha


async def test_a_failed_build_row_pins_the_commit_too(store) -> None:
    await build(CAND, store=store, run=scripted((1, "ERROR: failed to solve")))
    assert store.rows("builds")[0]["commit_sha"] == CAND.commit_sha


async def test_the_check_row_pins_the_model_and_endpoint_it_ran_under(store) -> None:
    """The shim env changes what the container sees, so the same image checked
    against a different endpoint is a different measurement."""
    cfg = ShimConfig(base_url="http://ollama:11434/v1", model="qwen2.5-coder:7b")
    await verify_environment("sha256:" + "b" * 64, store=store,
                             run=scripted((0, "ok")), shim=cfg)
    row = store.rows("env_checks")[0]
    assert row["model"] == "qwen2.5-coder:7b"
    assert row["base_url"] == "http://ollama:11434/v1"


async def test_a_check_row_without_a_shim_pins_no_model(store) -> None:
    await verify_environment("sha256:" + "b" * 64, store=store, run=scripted((0, "ok")))
    row = store.rows("env_checks")[0]
    assert row["model"] is None and row["base_url"] is None


async def test_a_raised_exception_during_build_is_a_row_not_a_traceback(store) -> None:
    """Docker absent raises FileNotFoundError from the runner. The batch must
    survive it and the dataset must say what happened."""
    async def raising(*argv: str, **kw):
        raise FileNotFoundError(2, "No such file or directory: 'docker'")

    res = await build(CAND, store=store, run=raising)

    assert not res.ok and res.failure is FailureClass.UNKNOWN
    row = store.rows("builds")[0]
    assert row["status"] == "failed" and row["failure_class"] == "unknown"
    assert row["image_digest"] is None
    assert b"FileNotFoundError" in store.read_blob(row["log_ref"])


async def test_a_raise_while_reading_the_image_id_keeps_the_build_log(store) -> None:
    async def flaky(*argv: str, **kw):
        if "inspect" in " ".join(argv):
            raise OSError("Cannot connect to the Docker daemon")
        return (0, "Successfully built")

    res = await build(CAND, store=store, run=flaky)
    assert res.failure is FailureClass.UNKNOWN
    evidence = store.read_blob(store.rows("builds")[0]["log_ref"]).decode()
    assert "Successfully built" in evidence
    assert "OSError" in evidence


async def test_build_and_inspect_are_both_given_a_timeout(store) -> None:
    """One hung docker build stalls the whole batch forever."""
    kwargs: list[dict] = []

    async def recording(*argv: str, **kw):
        kwargs.append(kw)
        if "inspect" in " ".join(argv):
            return (0, REAL_IMAGE_ID)
        return (0, "Successfully built")

    await build(CAND, store=store, run=recording)
    assert len(kwargs) == 2
    assert all(kw.get("timeout_s") for kw in kwargs)


async def test_a_credential_the_shim_cannot_supply_is_not_a_crash(store) -> None:
    async def never_called(*argv: str, **kw):
        raise AssertionError("the container must not be run")

    res = await verify_environment("sha256:" + "b" * 64, store=store,
                                   run=never_called,
                                   declared_credentials=("GITHUB_TOKEN",))
    assert not res.ok and res.failure is FailureClass.NEEDS_CREDENTIALS
    assert store.rows("env_checks")[0]["failure_class"] == "needs_credentials"


async def test_a_credential_the_shim_can_supply_is_not_an_obstacle(store) -> None:
    res = await verify_environment("sha256:" + "b" * 64, store=store,
                                   run=scripted((0, "ok")),
                                   declared_credentials=("OPENAI_API_KEY",))
    assert res.ok


def test_every_build_row_pins_the_recipe_that_produced_it() -> None:
    """The recipe decides which agents are buildable at all, so it is an
    experimental variable and rows produced under different recipes are
    different measurements.

    This was found by running: the first live run failed AutoGPT and OpenHands
    only because the recipe looked for an installable manifest at the
    repository root, and a recipe that looks one directory down makes both
    viable. Without this pin that edit would silently redefine every figure in
    the dataset, and a distribution computed across two recipes would look
    exactly like one measurement.
    """
    from crucible.forge import RECIPE_PATH, recipe_sha

    sha = recipe_sha()
    assert sha.startswith("sha256:")
    assert len(sha) == 71

    # It is a digest of the recipe's actual bytes, not a constant.
    import hashlib
    from pathlib import Path
    expected = hashlib.sha256(Path(RECIPE_PATH).read_bytes()).hexdigest()
    assert sha == "sha256:" + expected

    # Editing the recipe must change the digest, or the pin records nothing.
    import tempfile
    with tempfile.NamedTemporaryFile("w", suffix=".Dockerfile", delete=False) as f:
        f.write("FROM python:3.11-slim\n")
        other = f.name
    assert recipe_sha(other) != sha
