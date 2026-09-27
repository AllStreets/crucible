"""Turning repository URLs into pinned candidates.

`git ls-remote` rather than a clone: resolving HEAD costs one round trip and no
disk, and the clone happens later only for candidates that survive. The commit
SHA is pinned here because a result that cannot name the exact code it tested
is not reproducible, and an unreproducible safety finding is a rumour.

A URL that does not resolve is recorded rather than skipped. Skipping it shrinks
the denominator from the number of URLs seeded to whatever answered today, with
nothing in the dataset to say it happened, which is exactly the silence that
resembles success this project exists to avoid.

The runner is injected so tests never touch the network.
"""
from __future__ import annotations

import asyncio
import re
from dataclasses import dataclass, field
from typing import Awaitable, Callable, Sequence

from crucible.store import Store

Runner = Callable[..., Awaitable[tuple[int, str]]]

_SHA = re.compile(r"^[0-9a-f]{40}$")

# One unreachable host must not stall a batch of fifty. Resolving HEAD is a
# single round trip, so a minute is already generous.
LS_REMOTE_TIMEOUT_S = 60


@dataclass(frozen=True)
class Candidate:
    slug: str
    source: str
    repo_url: str
    commit_sha: str
    # Credentials the seed list declares this agent needs. Empty for most.
    # Anything here that the local shim cannot honestly supply makes the
    # candidate a NEEDS_CREDENTIALS observation rather than a crash.
    credentials: tuple[str, ...] = ()
    #: The base image this candidate is to be built on, resolved from the
    #: seed's `python=` declaration. None means the recipe's own default, and
    #: a build row records what it actually used either way.
    base_image: str | None = None
    #: Versions to force after the agent's own resolution, from the seed's
    #: `pin=` declarations. Empty for almost every agent.
    pins: tuple[str, ...] = ()
    #: Which build recipe this candidate needs. "python" is the default and
    #: the only one there was for the first three hundred builds.
    lang: str = "python"


@dataclass(frozen=True)
class Seed:
    """One line of a seed list: a URL, plus any credentials it declares."""

    url: str
    credentials: tuple[str, ...] = field(default=())
    #: A tag or branch to pin instead of HEAD. An agent that was rewritten in
    #: another language, or that broke at HEAD, is still a real agent at the
    #: commit people ran it at, and measuring it there is a choice the seed
    #: list records rather than one the harvester makes.
    ref: str | None = None
    #: A Python version the agent needs, as `python=3.12`. Declared in the seed
    #: rather than inferred, for the same reason entrypoints are hand written:
    #: a base image chosen by guessing would change which agents are viable and
    #: nothing would record that a choice had been made.
    python: str | None = None
    #: Dependency versions to force after the agent's own resolution, as
    #: `pin=cryptography==45.0.7`, repeatable. Declared rather than inferred,
    #: and recorded on the build row, because a build whose dependency set was
    #: overridden is a different measurement and a reader has to see that it
    #: happened.
    pins: tuple[str, ...] = field(default=())
    #: The language this agent is written in, as `lang=node`. Declared rather
    #: than sniffed: a repository that ships both a package.json and a
    #: pyproject.toml is common, and a recipe chosen by guessing would decide
    #: which half of such a project the dataset is about without recording
    #: that a choice was made.
    lang: str = "python"


DEFAULT_BASE_IMAGE = "python:3.11-slim"
#: What each recipe falls back to when a seed declares no version. Recorded on
#: the build row either way: a row that reported the Python default while a
#: Node recipe built it was the first thing this table fixed.
DEFAULT_BASE_IMAGES = {"python": DEFAULT_BASE_IMAGE, "node": "node:22-slim"}


def default_base_for(lang: str) -> str:
    return DEFAULT_BASE_IMAGES.get(lang, DEFAULT_BASE_IMAGE)


def base_image_for(python: str | None, lang: str = "python") -> str | None:
    """The base image a declaration resolves to, or None for the recipe default.

    One place translates the version a seed asks for into an image tag, so the
    seed list stays a statement about the agent ("this needs 3.12") rather than
    about Docker Hub, and a change of image family is one edit here.
    """
    if python is None:
        return None
    if lang == "node":
        return f"node:{python}-slim"
    return f"python:{python}-slim"


def parse_seed_line(line: str) -> Seed | None:
    """Parse one seed-list line, or None for a blank line or a comment.

    The comment test is against the stripped line, so an indented comment is a
    comment rather than a URL with leading whitespace.

    A line may declare credentials the agent needs:

        https://github.com/owner/repo needs=GITHUB_TOKEN,SLACK_BOT_TOKEN

    Declaring one is not a guess about the agent: it is the operator saying this
    agent cannot be exercised without that secret, so the check stage records
    NEEDS_CREDENTIALS instead of running it and filing the result as a failure
    whose real cause was a missing token.
    """
    stripped = line.strip()
    if not stripped or stripped.startswith("#"):
        return None
    parts = stripped.split()
    url = parts[0]
    declared: list[str] = []
    ref: str | None = None
    python: str | None = None
    pins: list[str] = []
    lang = "python"
    for part in parts[1:]:
        if part.startswith("lang="):
            lang = part[len("lang="):].strip() or "python"
            continue
        if part.startswith("pin="):
            spec = part[len("pin="):].strip()
            if spec:
                pins.append(spec)
        elif part.startswith("python="):
            python = part[len("python="):].strip() or None
        elif part.startswith("ref="):
            ref = part[len("ref="):].strip() or None
            continue
        if part.startswith("needs="):
            declared.extend(
                name.strip().upper()
                for name in part[len("needs="):].split(",") if name.strip())
    return Seed(url=url, credentials=tuple(declared), ref=ref, python=python,
                pins=tuple(pins), lang=lang)


def parse_seed_file(text: str) -> list[Seed]:
    """Every seed line in a seed file, comments and blanks dropped."""
    seeds = [parse_seed_line(line) for line in text.splitlines()]
    return [s for s in seeds if s is not None]


async def default_runner(*argv: str, timeout_s: int | None = None) -> tuple[int, str]:
    """Execute a subprocess with optional timeout.

    When timeout_s is not None, wraps subprocess communication in asyncio.wait_for
    and ensures the child process is killed rather than left running on expiry.
    """
    proc = await asyncio.create_subprocess_exec(
        *argv, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.STDOUT)
    try:
        if timeout_s is not None:
            out, _ = await asyncio.wait_for(proc.communicate(), timeout=timeout_s)
        else:
            out, _ = await proc.communicate()
        return (proc.returncode or 0, out.decode("utf-8", "replace"))
    except asyncio.TimeoutError:
        proc.kill()
        try:
            await proc.wait()
        except Exception:
            pass
        raise


def slug_for(repo_url: str) -> str:
    """Derive slug from the last two path segments (owner/repository).

    Handles edge cases gracefully: URLs with only one path segment fall back
    to that segment, and trailing .git suffixes are removed before transformation.
    """
    path = repo_url.rstrip("/").rsplit("/", 2)
    # Extract the last two segments if they exist, otherwise use what we have
    if len(path) >= 2:
        segments = path[-2:]
    else:
        segments = path[-1:]
    name = "/".join(segments)
    if name.endswith(".git"):
        name = name[:-4]
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")


def source_for(repo_url: str) -> str:
    return "huggingface" if "huggingface.co" in repo_url else "github"


async def resolve_head_detail(repo_url: str, *, run: Runner,
                              ref: str | None = None) -> tuple[str | None, str]:
    """The commit SHA at HEAD, or at `ref`, or None and the reason it could not be read.

    Returns rather than raises: one dead repository must not lose the rest of
    the batch, and an unreachable repository is itself an observation, which is
    why the reason comes back rather than being discarded.
    """
    # A tag resolves through its peeled entry (refs/tags/x^{}) when the tag is
    # annotated, which points at the commit rather than the tag object; the
    # last matching line wins because ls-remote prints the peeled line second.
    want = ["HEAD"] if ref is None else [f"refs/tags/{ref}", f"refs/heads/{ref}", ref]
    try:
        code, out = await run("git", "ls-remote", repo_url, *want,
                              timeout_s=LS_REMOTE_TIMEOUT_S)
    except (TimeoutError, asyncio.TimeoutError):
        return None, f"git ls-remote timed out after {LS_REMOTE_TIMEOUT_S}s"
    except Exception as exc:
        return None, f"git ls-remote raised {type(exc).__name__}: {exc}"
    if code != 0:
        detail = out.strip().splitlines()[0][:300] if out.strip() else "no output"
        return None, f"git ls-remote exited {code}: {detail}"
    lines = [l for l in out.splitlines() if l.strip()]
    if ref is not None:
        peeled = [l for l in lines if l.rstrip().endswith("^{}")]
        chosen = (peeled or lines)[-1] if lines else ""
    else:
        chosen = lines[0] if lines else ""
    sha = chosen.split("\t", 1)[0].strip()
    if not _SHA.match(sha):
        return None, f"git ls-remote returned no commit sha for {ref or 'HEAD'}"
    return sha, ""


async def resolve_head(repo_url: str, *, run: Runner) -> str | None:
    """The commit SHA at HEAD, or None if the repository cannot be reached."""
    sha, _ = await resolve_head_detail(repo_url, run=run)
    return sha


async def harvest(seeds: Sequence[str | Seed], *, store: Store,
                  run: Runner = default_runner) -> list[Candidate]:
    """Resolve each seed to a pinned candidate, recorded once per identity.

    A candidate's identity is `(slug, commit_sha)`: the same repository at the
    same commit is the same candidate, whichever day we asked. So a re-harvest
    of the same seed list at an unchanged HEAD writes no new candidate row and
    returns the existing identity.

    It does not write a superseding row either. `supersedes` means "this
    corrects that", and the earlier row was not wrong; re-observing a fact is
    not a correction of it, and recording one would put a retraction in the
    dataset for a measurement that still stands. Append-only is untouched:
    nothing is mutated or deleted, a duplicate fact is simply not appended.

    A repository resolving to a *different* HEAD is a different candidate and
    does get its own row, because the code under test is different and every
    build and check row downstream pins that commit.

    A superseded candidate row does not count as known. It has been withdrawn
    from every figure, so treating it as known would leave the identity absent
    from `harvested` while its build rows still counted, which is how `built`
    came to be able to exceed `harvested`. Re-harvesting it writes a fresh row.

    A seed that does not resolve gets an `unresolved` row naming the reason, so
    the count of URLs seeded stays recoverable from the dataset.
    """
    withdrawn = {r["old_id"] for r in store.rows("supersedes", tbl="candidates")}
    found: list[Candidate] = []
    seen: set[tuple[str, str]] = set()
    for seed in seeds:
        item = seed if isinstance(seed, Seed) else Seed(url=seed)
        sha, reason = await resolve_head_detail(item.url, run=run, ref=item.ref)
        if sha is None:
            _record_unresolved(store, item.url, reason)
            continue
        cand = Candidate(slug=slug_for(item.url), source=source_for(item.url),
                         repo_url=item.url, commit_sha=sha,
                         credentials=item.credentials,
                         base_image=base_image_for(item.python, item.lang),
                         pins=item.pins, lang=item.lang)
        identity = (cand.slug, cand.commit_sha)
        if identity in seen:
            continue
        seen.add(identity)
        known = [r for r in store.rows("candidates", slug=cand.slug,
                                       commit_sha=cand.commit_sha)
                 if r["id"] not in withdrawn]
        if not known:
            store.record("candidates", slug=cand.slug, source=cand.source,
                         repo_url=cand.repo_url, commit_sha=cand.commit_sha,
                         credentials=list(cand.credentials))
        found.append(cand)
    return found


def _record_unresolved(store: Store, seed_url: str, reason: str) -> None:
    """Record that a seed URL did not resolve, once per distinct reason."""
    already = store.rows("unresolved", seed_url=seed_url, reason=reason)
    if not already:
        store.record("unresolved", seed_url=seed_url, reason=reason)
