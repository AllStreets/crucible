"""Build a candidate, then check the container it produced.

Building is the easy half and the misleading one, so the build and the check
that follows it are separate recorded stages with their own failure classes, and
"built" never implies "works".

The check is an environment probe and nothing more. It starts the built image
with egress denied and runs the image's default command, which is the probe the
Dockerfile installs: start the interpreter, print one line, exit. That proves the
image runs in a clean sandbox. It does not prove the agent runs, and it does not
invoke the agent. The agents in the seed list share no entrypoint, and with no
network and no credentials an invocation would measure this harness rather than
the agent. Calling the probe a boot would make the passing count a restatement of
the built count under a name claiming more than was measured, which is the one
thing this project cannot afford to publish. So the stage, the rows, the failure
classes and the report all say environment check. Whether an agent actually runs
is a separate and harder measurement, and it is not reported here.

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
class EnvCheckResult:
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
        store.record("builds", candidate=c.slug, commit_sha=c.commit_sha,
                     status="failed", failure_class=str(failure), log_ref=log_ref)
        return BuildResult(False, None, failure, log_ref)

    # The image ID is the pin. A build we cannot pin is not a usable build.
    #
    # Deliberately {{.Id}} and not {{index .RepoDigests 0}}: RepoDigests is
    # populated only for an image that has a registry association, so for an
    # image we built here and never pushed it is an empty list, the Go template
    # errors, docker exits non-zero, and every genuinely viable agent in the
    # batch would be recorded as a build failure. Its entries are also formatted
    # `repo@sha256:...`, which would not satisfy the guard below. {{.Id}} is the
    # content-addressed image ID, is always present for a local build, and is
    # already formatted `sha256:...`. Do not "correct" this back.
    dcode, digest = await run("docker", "image", "inspect", tag,
                              "--format", "{{.Id}}")
    digest = digest.strip()
    if dcode != 0 or not digest.startswith("sha256:"):
        store.record("builds", candidate=c.slug, commit_sha=c.commit_sha,
                     status="failed", failure_class=str(FailureClass.BUILD_FAILED),
                     log_ref=log_ref)
        return BuildResult(False, None, FailureClass.BUILD_FAILED, log_ref)

    store.record("builds", candidate=c.slug, commit_sha=c.commit_sha,
                 status="built", image_digest=digest, log_ref=log_ref)
    return BuildResult(True, digest, FailureClass.NONE, log_ref)


async def verify_environment(image_digest: str, *, store: Store,
                             run: Runner = default_runner,
                             timeout_s: int = 60,
                             shim: ShimConfig | None = None) -> EnvCheckResult:
    """Run the built image's environment probe with egress denied.

    What this measures: the image starts in a clean sandbox and its default
    command, the probe the Dockerfile installs, runs to completion. What it does
    not measure: whether the agent runs. The probe does not start the agent. A
    row from this stage must never be read or reported as a boot.

    Network is off. A result that only holds because the container reached the
    internet is not reproducible, and this stage is about the image rather than
    about connectivity.

    When `shim` is given, its environment is passed in with one `-e KEY=VALUE`
    pair per entry, ahead of the image digest. The probe itself does not need a
    model endpoint, but the env is what a later phase will vary when it does
    invoke the agent, so the row pins the model and base URL it ran under: the
    same image checked under a different endpoint is a different measurement.
    """
    env_args: list[str] = []
    if shim is not None:
        for key, value in shim_env(shim, []).items():
            env_args.extend(["-e", f"{key}={value}"])
    model = shim.model if shim is not None else None
    base_url = shim.base_url if shim is not None else None

    started = time.monotonic()
    try:
        code, out = await run(
            "docker", "run", "--rm", "--network", "none",
            "--memory", "2g", "--cpus", "1",
            *env_args,
            image_digest, timeout_s=timeout_s)
    except (TimeoutError, asyncio.TimeoutError):
        ms = int((time.monotonic() - started) * 1000)
        ref = store.blob(b"environment check timed out with no output")
        store.record("env_checks", build=image_digest, status="failed",
                     failure_class=str(FailureClass.ENV_CHECK_TIMEOUT),
                     evidence_ref=ref, duration_ms=ms,
                     model=model, base_url=base_url)
        return EnvCheckResult(False, FailureClass.ENV_CHECK_TIMEOUT, ms, ref)

    ms = int((time.monotonic() - started) * 1000)
    ref = store.blob(out.encode())
    if code != 0:
        store.record("env_checks", build=image_digest, status="failed",
                     failure_class=str(FailureClass.ENV_CHECK_FAILED),
                     evidence_ref=ref, duration_ms=ms,
                     model=model, base_url=base_url)
        return EnvCheckResult(False, FailureClass.ENV_CHECK_FAILED, ms, ref)

    store.record("env_checks", build=image_digest, status="passed",
                 failure_class=None, evidence_ref=ref, duration_ms=ms,
                 model=model, base_url=base_url)
    return EnvCheckResult(True, FailureClass.NONE, ms, ref)
