import pytest
from crucible.failures import FailureClass
from crucible.forge import build, verify_boot
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


async def test_a_container_that_starts_and_stays_up_counts_as_booted(store) -> None:
    res = await verify_boot("sha256:" + "b" * 64, store=store,
                            run=scripted((0, "ready")))
    assert res.ok and res.failure is FailureClass.NONE
    assert store.rows("boots")[0]["status"] == "booted"


async def test_a_container_that_exits_immediately_is_a_boot_crash(store) -> None:
    """This is the case the whole task exists for: it built fine and is still
    useless. Reporting it as a successful build would overstate viability."""
    res = await verify_boot("sha256:" + "b" * 64, store=store,
                            run=scripted((1, "Traceback: ModuleNotFoundError")))
    assert not res.ok and res.failure is FailureClass.BOOT_CRASH
    assert store.rows("boots")[0]["status"] == "failed"


async def test_a_container_that_hangs_is_a_timeout_not_a_crash(store) -> None:
    async def hangs(*argv, **kw):
        raise TimeoutError()
    res = await verify_boot("sha256:" + "b" * 64, store=store, run=hangs)
    assert res.failure is FailureClass.BOOT_TIMEOUT


async def test_evidence_is_always_stored_even_on_success(store) -> None:
    res = await verify_boot("sha256:" + "b" * 64, store=store, run=scripted((0, "ready")))
    assert store.read_blob(res.evidence_ref)


async def test_verify_boot_with_a_shim_passes_its_env_into_the_container(store) -> None:
    """A container that starts and immediately tries to reach a model needs the
    endpoint at exactly this moment, or it fails as a false BOOT_CRASH."""
    captured: list[str] = []

    async def recording(*argv: str, **kw) -> tuple[int, str]:
        captured.extend(argv)
        return (0, "ready")

    cfg = ShimConfig(base_url="http://ollama:11434/v1", model="qwen2.5-coder:7b")
    await verify_boot("sha256:" + "b" * 64, store=store, run=recording, shim=cfg)

    assert "-e" in captured
    idx = captured.index("-e")
    assert captured[idx + 1] == "OPENAI_BASE_URL=http://ollama:11434/v1"


async def test_verify_boot_without_a_shim_passes_no_env_flags(store) -> None:
    captured: list[str] = []

    async def recording(*argv: str, **kw) -> tuple[int, str]:
        captured.extend(argv)
        return (0, "ready")

    await verify_boot("sha256:" + "b" * 64, store=store, run=recording)

    assert "-e" not in captured
