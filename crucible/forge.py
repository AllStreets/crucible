"""Build a candidate, then find out whether it actually runs.

Building is the easy half and the misleading one. A container that builds and
exits on startup is not a usable agent, and counting it as a success would
overstate ecosystem viability, which is the exact number this project exists to
report honestly. So boot verification is a separate recorded stage with its own
failure classes, and "built" never implies "works".

Every outcome writes a row and stores its evidence, including successes. A
success with no stored evidence cannot be audited later, and an unauditable
success is indistinguishable from an assumed one.
"""
from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass

from crucible.failures import FailureClass, classify_build_log
from crucible.harvest import Candidate, Runner, default_runner
from crucible.model_shim import ShimConfig, shim_env
from crucible.store import Store


@dataclass(frozen=True)
class BuildResult:
    ok: bool
    image_digest: str | None
    failure: FailureClass
    log_ref: str


@dataclass(frozen=True)
class BootResult:
    ok: bool
    failure: FailureClass
    duration_ms: int
    evidence_ref: str


def _tag(c: Candidate) -> str:
    return f"crucible/{c.slug}:{c.commit_sha[:12]}"


async def build(c: Candidate, *, store: Store,
                run: Runner = default_runner) -> BuildResult:
    tag = _tag(c)
    code, log = await run(
        "docker", "build", "-t", tag,
        "--build-arg", f"REPO_URL={c.repo_url}",
        "--build-arg", f"COMMIT_PIN={c.commit_sha}",
        "-f", "docker/generic.Dockerfile", ".")
    log_ref = store.blob(log.encode())

    if code != 0:
        failure = classify_build_log(log, code)
        store.record("builds", candidate=c.slug, status="failed",
                     failure_class=str(failure), log_ref=log_ref)
        return BuildResult(False, None, failure, log_ref)

    # The digest is the pin. A build we cannot pin is not a usable build.
    dcode, digest = await run("docker", "image", "inspect", tag,
                              "--format", "{{index .RepoDigests 0}}")
    digest = digest.strip()
    if dcode != 0 or not digest.startswith("sha256:"):
        store.record("builds", candidate=c.slug, status="failed",
                     failure_class=str(FailureClass.BUILD_FAILED), log_ref=log_ref)
        return BuildResult(False, None, FailureClass.BUILD_FAILED, log_ref)

    store.record("builds", candidate=c.slug, status="built",
                 image_digest=digest, log_ref=log_ref)
    return BuildResult(True, digest, FailureClass.NONE, log_ref)


async def verify_boot(image_digest: str, *, store: Store,
                      run: Runner = default_runner,
                      timeout_s: int = 60,
                      shim: ShimConfig | None = None) -> BootResult:
    """Start the container with egress denied and see whether it survives.

    Network is off: a boot that only succeeds because it reached the internet is
    not a boot we can reproduce, and this stage is about the container, not
    connectivity.

    When `shim` is given, its environment is passed into the container with one
    `-e KEY=VALUE` pair per entry, ahead of the image digest. This is the first
    moment the container executes, so an agent that starts up and immediately
    tries to reach a model needs the endpoint set right here; otherwise a boot
    that fails only for lack of a model endpoint would be recorded as a false
    BOOT_CRASH. Network is still denied in this phase, so the endpoint is not
    actually reachable yet; wiring the env now is what lets a later phase attach
    a real network alias without touching this function again.
    """
    env_args: list[str] = []
    if shim is not None:
        for key, value in shim_env(shim, []).items():
            env_args.extend(["-e", f"{key}={value}"])

    started = time.monotonic()
    try:
        code, out = await run(
            "docker", "run", "--rm", "--network", "none",
            "--memory", "2g", "--cpus", "1",
            *env_args,
            image_digest, timeout_s=timeout_s)
    except (TimeoutError, asyncio.TimeoutError):
        ms = int((time.monotonic() - started) * 1000)
        ref = store.blob(b"boot timed out with no output")
        store.record("boots", build=image_digest, status="failed",
                     failure_class=str(FailureClass.BOOT_TIMEOUT),
                     evidence_ref=ref, duration_ms=ms)
        return BootResult(False, FailureClass.BOOT_TIMEOUT, ms, ref)

    ms = int((time.monotonic() - started) * 1000)
    ref = store.blob(out.encode())
    if code != 0:
        store.record("boots", build=image_digest, status="failed",
                     failure_class=str(FailureClass.BOOT_CRASH),
                     evidence_ref=ref, duration_ms=ms)
        return BootResult(False, FailureClass.BOOT_CRASH, ms, ref)

    store.record("boots", build=image_digest, status="booted",
                 failure_class=None, evidence_ref=ref, duration_ms=ms)
    return BootResult(True, FailureClass.NONE, ms, ref)
