"""Turning repository URLs into pinned candidates.

`git ls-remote` rather than a clone: resolving HEAD costs one round trip and no
disk, and the clone happens later only for candidates that survive. The commit
SHA is pinned here because a result that cannot name the exact code it tested
is not reproducible, and an unreproducible safety finding is a rumour.

The runner is injected so tests never touch the network.
"""
from __future__ import annotations

import asyncio
import re
from dataclasses import dataclass
from typing import Awaitable, Callable

from crucible.store import Store

Runner = Callable[..., Awaitable[tuple[int, str]]]

_SHA = re.compile(r"^[0-9a-f]{40}$")


@dataclass(frozen=True)
class Candidate:
    slug: str
    source: str
    repo_url: str
    commit_sha: str


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


async def resolve_head(repo_url: str, *, run: Runner) -> str | None:
    """The commit SHA at HEAD, or None if the repository cannot be reached.

    Returns rather than raises: one dead repository must not lose the rest of
    the batch, and an unreachable repository is itself an observation. Catches
    exceptions from the runner to prevent a single systemic failure from losing
    the entire batch.
    """
    try:
        code, out = await run("git", "ls-remote", repo_url, "HEAD")
    except Exception:
        return None
    if code != 0:
        return None
    first = out.split("\t", 1)[0].strip()
    return first if _SHA.match(first) else None


async def harvest(urls: list[str], *, store: Store,
                  run: Runner = default_runner) -> list[Candidate]:
    found: list[Candidate] = []
    for url in urls:
        sha = await resolve_head(url, run=run)
        if sha is None:
            continue
        cand = Candidate(slug=slug_for(url), source=source_for(url),
                         repo_url=url, commit_sha=sha)
        store.record("candidates", slug=cand.slug, source=cand.source,
                     repo_url=cand.repo_url, commit_sha=cand.commit_sha)
        found.append(cand)
    return found
