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


async def test_a_successful_build_records_a_pinned_digest(store) -> None:
    run = scripted((0, "Successfully built"), (0, "sha256:" + "b" * 64))
    res = await build(CAND, store=store, run=run)

    assert res.ok and res.image_digest == "sha256:" + "b" * 64
    row = store.rows("builds")[0]
    assert row["status"] == "built" and row["image_digest"] == res.image_digest


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
