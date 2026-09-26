"""Tests for the harvest module."""
import asyncio
import pytest
from crucible.harvest import (Candidate, harvest, parse_seed_file,
                             parse_seed_line, resolve_head, slug_for)
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

    assert [c.slug for c in got] == ["x-good"]
    assert len(store.rows("candidates")) == 1
    assert store.rows("candidates")[0]["commit_sha"] == "a" * 40


async def test_harvest_never_writes_a_candidate_without_a_pinned_sha(store) -> None:
    run = fake_runner({"x": (0, "\trefs/heads/main\n")})
    await harvest(["https://github.com/x/x"], store=store, run=run)
    assert store.rows("candidates") == []


def test_slug_is_derived_from_owner_and_repo() -> None:
    assert slug_for("https://github.com/Aider-AI/aider") == "aider-ai-aider"
    assert slug_for("https://github.com/x/My_Agent.git") == "x-my-agent"


def test_different_owners_with_same_repo_name_produce_different_slugs() -> None:
    """Slug collisions between different agents must be prevented."""
    slug1 = slug_for("https://github.com/foo/aider")
    slug2 = slug_for("https://github.com/bar/aider")
    assert slug1 == "foo-aider"
    assert slug2 == "bar-aider"
    assert slug1 != slug2


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


async def test_runner_exception_does_not_escape_resolve_head() -> None:
    """A runner that raises an exception causes resolve_head to return None
    rather than propagate, so one failing candidate does not lose the batch."""
    async def raising_runner(*argv: str, **kw) -> tuple[int, str]:
        raise OSError("simulated runner failure")
    result = await resolve_head("https://github.com/x/example", run=raising_runner)
    assert result is None


async def test_harvest_with_runner_exception_records_good_candidates(store) -> None:
    """When one URL's runner raises an exception, harvest still records the good ones."""
    call_count = 0
    async def selective_raising_runner(*argv: str, **kw) -> tuple[int, str]:
        nonlocal call_count
        call_count += 1
        if "good" in " ".join(argv):
            return (0, "b" * 40 + "\trefs/heads/main\n")
        elif "bad" in " ".join(argv):
            raise OSError("connection failed")
        return (1, "unmatched")

    got = await harvest(
        ["https://github.com/x/good", "https://github.com/x/bad"],
        store=store,
        run=selective_raising_runner
    )
    assert [c.slug for c in got] == ["x-good"]
    assert len(store.rows("candidates")) == 1
    assert store.rows("candidates")[0]["commit_sha"] == "b" * 40


async def test_harvesting_the_same_seed_list_twice_records_one_row_per_agent(store) -> None:
    """Re-running a seed file must not double the published harvested count.
    A candidate's identity is (slug, commit_sha): the same repository at the
    same commit is the same candidate, not a second one."""
    run = fake_runner({
        "one": (0, "a" * 40 + "\trefs/heads/main\n"),
        "two": (0, "b" * 40 + "\trefs/heads/main\n"),
    })
    urls = ["https://github.com/x/one", "https://github.com/x/two"]

    first = await harvest(urls, store=store, run=run)
    second = await harvest(urls, store=store, run=run)

    assert [c.slug for c in first] == [c.slug for c in second] == ["x-one", "x-two"]
    rows = store.rows("candidates")
    assert len(rows) == 2
    assert {r["slug"] for r in rows} == {"x-one", "x-two"}


async def test_the_same_repository_at_a_new_head_is_a_new_candidate(store) -> None:
    """Different code under test, so a distinct identity with its own row."""
    url = "https://github.com/x/one"
    await harvest([url], store=store, run=fake_runner({"one": (0, "a" * 40 + "\tHEAD\n")}))
    await harvest([url], store=store, run=fake_runner({"one": (0, "c" * 40 + "\tHEAD\n")}))

    rows = store.rows("candidates")
    assert len(rows) == 2
    assert {r["commit_sha"] for r in rows} == {"a" * 40, "c" * 40}


async def test_two_seed_urls_for_one_commit_are_harvested_once(store) -> None:
    """Two spellings of the same repository (a rename redirect, say) resolve to
    the same slug and the same commit, so they are one candidate."""
    run = fake_runner({"github.com": (0, "a" * 40 + "\tHEAD\n")})
    got = await harvest(["https://github.com/x/one", "https://github.com/x/one.git"],
                        store=store, run=run)
    assert len(got) == 1
    assert len(store.rows("candidates")) == 1


async def test_ls_remote_is_given_a_timeout(store) -> None:
    """One unreachable host must not stall a batch of fifty forever."""
    kwargs: list[dict] = []

    async def recording(*argv: str, **kw):
        kwargs.append(kw)
        return (0, "a" * 40 + "\tHEAD\n")

    await harvest(["https://github.com/x/one"], store=store, run=recording)
    assert kwargs[0].get("timeout_s")


async def test_an_unresolvable_seed_is_recorded_with_its_reason(store) -> None:
    run = fake_runner({"gone": (128, "remote: Repository not found.\nfatal: not found")})
    got = await harvest(["https://github.com/x/gone"], store=store, run=run)

    assert got == []
    rows = store.rows("unresolved")
    assert len(rows) == 1
    assert rows[0]["seed_url"] == "https://github.com/x/gone"
    assert "128" in rows[0]["reason"]


async def test_a_seed_that_times_out_says_so_rather_than_vanishing(store) -> None:
    async def hangs(*argv: str, **kw):
        raise TimeoutError()

    await harvest(["https://github.com/x/slow"], store=store, run=hangs)
    assert "timed out" in store.rows("unresolved")[0]["reason"]


async def test_the_same_unresolvable_seed_is_recorded_once(store) -> None:
    run = fake_runner({"gone": (128, "fatal: not found")})
    await harvest(["https://github.com/x/gone"], store=store, run=run)
    await harvest(["https://github.com/x/gone"], store=store, run=run)
    assert len(store.rows("unresolved")) == 1


def test_a_seed_line_declares_the_credentials_an_agent_needs() -> None:
    seed = parse_seed_line("https://github.com/x/y needs=GITHUB_TOKEN,slack_bot_token")
    assert seed is not None
    assert seed.url == "https://github.com/x/y"
    assert seed.credentials == ("GITHUB_TOKEN", "SLACK_BOT_TOKEN")


def test_an_indented_comment_is_a_comment_not_a_url() -> None:
    """startswith("#") on the unstripped line treated it as a repository URL."""
    assert parse_seed_line("   # an indented note") is None
    assert parse_seed_line("") is None
    assert parse_seed_line("   ") is None
    assert parse_seed_line("  https://github.com/x/y  ").url == "https://github.com/x/y"


def test_the_shipped_seed_list_has_one_entry_per_repository() -> None:
    """Two spellings of one repository resolve to the same commit and would have
    published one agent as two."""
    from pathlib import Path
    text = Path("seeds/first-fifty.txt").read_text()
    seeds = parse_seed_file(text)
    slugs = [slug_for(s.url) for s in seeds]
    assert len(slugs) == len(set(slugs)), "duplicate repository in the seed list"
    assert len(seeds) == 49
