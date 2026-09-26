"""Tests for the harvest module."""
import asyncio
import pytest
from crucible.harvest import Candidate, harvest, resolve_head, slug_for
from crucible.store import Store


@pytest.fixture
def store(tmp_path):
    s = Store(tmp_path / "c.db")
    s.init_db()
    return s


def fake_runner(mapping):
    async def run(*argv: str, **kw) -> tuple[int, str]:
        for needle, result in mapping.items():
            if needle in " ".join(argv):
                return result
        return (1, "unmatched")
    return run


async def test_resolves_head_to_a_pinned_sha() -> None:
    run = fake_runner({"aider": (0, "deadbeef" * 5 + "\trefs/heads/main\n")})
    assert await resolve_head("https://github.com/Aider-AI/aider", run=run) == "deadbeef" * 5


async def test_a_repo_that_cannot_be_resolved_returns_none_rather_than_raising() -> None:
    """One dead repository must not lose the other candidates in the batch."""
    run = fake_runner({"ghost": (128, "fatal: repository not found")})
    assert await resolve_head("https://github.com/x/ghost", run=run) is None


async def test_harvest_records_what_it_resolved_and_skips_what_it_could_not(store) -> None:
    run = fake_runner({
        "good": (0, "a" * 40 + "\trefs/heads/main\n"),
        "bad": (128, "fatal: repository not found"),
    })
    got = await harvest(["https://github.com/x/good", "https://github.com/x/bad"],
                        store=store, run=run)

    assert [c.slug for c in got] == ["good"]
    assert len(store.rows("candidates")) == 1
    assert store.rows("candidates")[0]["commit_sha"] == "a" * 40


async def test_harvest_never_writes_a_candidate_without_a_pinned_sha(store) -> None:
    run = fake_runner({"x": (0, "\trefs/heads/main\n")})
    await harvest(["https://github.com/x/x"], store=store, run=run)
    assert store.rows("candidates") == []


def test_slug_is_derived_from_the_repo_name() -> None:
    assert slug_for("https://github.com/Aider-AI/aider") == "aider"
    assert slug_for("https://github.com/x/My_Agent.git") == "my-agent"


async def test_default_runner_timeout_kills_child_process() -> None:
    """A runner call with a short timeout_s against a command that sleeps longer
    raises asyncio.TimeoutError, and the child process is killed."""
    with pytest.raises(asyncio.TimeoutError):
        from crucible.harvest import default_runner
        await default_runner("sleep", "10", timeout_s=1)


async def test_default_runner_without_timeout_works() -> None:
    """A normal call without timeout_s still returns its output."""
    from crucible.harvest import default_runner
    code, out = await default_runner("echo", "hello")
    assert code == 0
    assert "hello" in out
