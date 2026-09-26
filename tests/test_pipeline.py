import pytest
from crucible.model_shim import ShimConfig
from crucible.pipeline import run_pipeline
from crucible.store import Store

SHIM = ShimConfig(base_url="http://ollama:11434/v1", model="qwen2.5-coder:7b")


@pytest.fixture
def store(tmp_path):
    s = Store(tmp_path / "c.db")
    s.init_db()
    return s


def script(mapping):
    async def run(*argv: str, **kw) -> tuple[int, str]:
        joined = " ".join(argv)
        for needle, result in mapping.items():
            if needle in joined:
                return result
        return (1, "unmatched command")
    return run


async def test_one_candidate_failing_does_not_stop_the_others(store) -> None:
    """The single most important property of the pipeline: a batch of fifty
    must not be lost because the seventh repository is dead."""
    run = script({
        "ls-remote https://github.com/x/good": (0, "a" * 40 + "\tHEAD\n"),
        "ls-remote https://github.com/x/dead": (128, "fatal: not found"),
        "docker build": (0, "Successfully built"),
        "image inspect": (0, "sha256:" + "b" * 64),
        "docker run": (0, "crucible environment probe ok"),
    })
    v = await run_pipeline(["https://github.com/x/good",
                            "https://github.com/x/dead"],
                           store=store, run=run, shim=SHIM)
    assert v.harvested == 1
    assert v.env_ok == 1


async def test_a_build_failure_still_produces_a_row_and_continues(store) -> None:
    run = script({
        "ls-remote": (0, "a" * 40 + "\tHEAD\n"),
        "docker build": (1, "ERROR: Could not find a version that satisfies"),
    })
    v = await run_pipeline(["https://github.com/x/a"], store=store, run=run, shim=SHIM)
    assert v.harvested == 1 and v.built == 0
    assert v.by_failure["dependency_conflict"] == 1


async def test_the_env_check_is_attempted_only_for_candidates_that_built(store) -> None:
    calls: list[str] = []

    async def run(*argv: str, **kw):
        joined = " ".join(argv)
        calls.append(joined)
        if "ls-remote" in joined:
            return (0, "a" * 40 + "\tHEAD\n")
        if "docker build" in joined:
            return (1, "ERROR: failed to solve")
        return (1, "unreachable")

    await run_pipeline(["https://github.com/x/a"], store=store, run=run, shim=SHIM)
    assert not any("docker run" in c for c in calls)


async def test_the_shim_reaches_the_container_through_the_pipeline(store) -> None:
    """The defect Task 8 existed to fix: run_pipeline accepted a shim but never
    forwarded it. Every container the check starts must see the model endpoint,
    since that env is the variable a later phase varies and the row pins it."""
    captured: list[list[str]] = []

    async def run(*argv: str, **kw) -> tuple[int, str]:
        joined = " ".join(argv)
        if "ls-remote" in joined:
            return (0, "a" * 40 + "\tHEAD\n")
        if "docker build" in joined:
            return (0, "Successfully built")
        if "image inspect" in joined:
            return (0, "sha256:" + "b" * 64)
        if "docker run" in joined:
            captured.append(list(argv))
            return (0, "crucible environment probe ok")
        return (1, "unmatched command")

    await run_pipeline(["https://github.com/x/good"], store=store, run=run, shim=SHIM)

    assert len(captured) == 1
    argv = captured[0]
    assert "-e" in argv
    idx = argv.index("-e")
    assert argv[idx + 1] == f"OPENAI_BASE_URL={SHIM.base_url}"
