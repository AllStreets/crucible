import pytest
from crucible.harvest import Seed
from crucible.model_shim import ShimConfig
from crucible.pipeline import run_pipeline
from crucible.report import render_markdown
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


async def test_a_raised_exception_loses_neither_the_row_nor_the_next_candidate(store) -> None:
    """Docker absent raises FileNotFoundError out of the runner. That used to
    travel past build(), past run_pipeline() and out to the CLI as a traceback,
    so candidate two was never attempted and no row said why. A fake that raises
    is the point: one that returns a bad exit code never reproduced this."""
    attempted: list[str] = []

    async def run(*argv: str, **kw):
        joined = " ".join(argv)
        if "ls-remote" in joined:
            return (0, "a" * 40 + "\tHEAD\n")
        if "docker build" in joined:
            attempted.append(joined)
            if "x/first" in joined:
                raise FileNotFoundError(2, "No such file or directory: 'docker'")
            return (0, "Successfully built")
        if "image inspect" in joined:
            return (0, "sha256:" + "b" * 64)
        if "docker run" in joined:
            return (0, "crucible environment probe ok")
        return (1, "unmatched command")

    v = await run_pipeline(["https://github.com/x/first", "https://github.com/x/second"],
                           store=store, run=run, shim=SHIM)

    assert len(attempted) == 2, "the second candidate was never built"
    assert v.harvested == 2 and v.built == 1 and v.env_ok == 1
    lost = [r for r in store.rows("builds") if r["candidate"] == "x-first"]
    assert len(lost) == 1
    assert lost[0]["status"] == "failed"
    assert lost[0]["failure_class"] == "unknown"
    assert b"FileNotFoundError" in store.read_blob(lost[0]["log_ref"])


async def test_a_raise_during_the_env_check_is_a_row_and_the_batch_continues(store) -> None:
    async def run(*argv: str, **kw):
        joined = " ".join(argv)
        if "ls-remote" in joined:
            return (0, "a" * 40 + "\tHEAD\n")
        if "docker build" in joined:
            return (0, "Successfully built")
        if "image inspect" in joined:
            return (0, "sha256:" + "b" * 64)
        if "docker run" in joined:
            raise OSError("Cannot connect to the Docker daemon")
        return (1, "unmatched command")

    v = await run_pipeline(["https://github.com/x/only"], store=store, run=run, shim=SHIM)

    assert v.built == 1 and v.env_ok == 0
    row = store.rows("env_checks")[0]
    assert row["status"] == "failed" and row["failure_class"] == "unknown"


async def test_a_declared_credential_the_shim_cannot_supply_is_recorded_as_such(store) -> None:
    """Not as a crash. The agent did not fail; we cannot exercise it honestly,
    and fabricating the token would put a lie in the dataset."""
    ran: list[str] = []

    async def run(*argv: str, **kw):
        joined = " ".join(argv)
        ran.append(joined)
        if "ls-remote" in joined:
            return (0, "a" * 40 + "\tHEAD\n")
        if "docker build" in joined:
            return (0, "Successfully built")
        if "image inspect" in joined:
            return (0, "sha256:" + "b" * 64)
        return (0, "crucible environment probe ok")

    seed = Seed(url="https://github.com/x/needy", credentials=("GITHUB_TOKEN",))
    v = await run_pipeline([seed], store=store, run=run, shim=SHIM)

    assert not any("docker run" in c for c in ran), "it was run anyway"
    assert v.built == 1 and v.env_ok == 0
    row = store.rows("env_checks")[0]
    assert row["failure_class"] == "needs_credentials"
    assert b"GITHUB_TOKEN" in store.read_blob(row["evidence_ref"])
    assert store.rows("candidates")[0]["credentials"] == ["GITHUB_TOKEN"]


async def test_an_unresolvable_seed_is_recorded_and_counted(store) -> None:
    """It used to vanish: the denominator shrank from the number seeded to
    whatever resolved today, and the report was identical to never having run."""
    async def run(*argv: str, **kw):
        joined = " ".join(argv)
        if "x/gone" in joined:
            return (128, "remote: Repository not found.\nfatal: repository not found")
        if "ls-remote" in joined:
            return (0, "a" * 40 + "\tHEAD\n")
        if "docker build" in joined:
            return (0, "Successfully built")
        if "image inspect" in joined:
            return (0, "sha256:" + "b" * 64)
        return (0, "crucible environment probe ok")

    v = await run_pipeline(["https://github.com/x/gone", "https://github.com/x/here"],
                           store=store, run=run, shim=SHIM)

    assert v.harvested == 1
    assert v.unresolved == 1
    row = store.rows("unresolved")[0]
    assert row["seed_url"] == "https://github.com/x/gone"
    assert "128" in row["reason"]


async def test_a_run_of_only_unresolvable_seeds_does_not_look_like_never_having_run(store) -> None:
    async def run(*argv: str, **kw):
        return (128, "fatal: repository not found")

    v = await run_pipeline(["https://github.com/x/gone"], store=store, run=run, shim=SHIM)
    md = render_markdown(v)
    assert v.unresolved == 1
    assert "could not be resolved" in md
