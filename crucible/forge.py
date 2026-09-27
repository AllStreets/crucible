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
import hashlib
import json
import time
from dataclasses import dataclass
from pathlib import Path

from crucible.failures import FailureClass, classify_build_log
from crucible.harvest import Candidate, Runner, default_runner
from crucible.model_shim import ShimConfig, shim_env, unsatisfiable
from crucible.store import Store

# A docker build clones a repository and installs its dependencies, so half an
# hour is realistic for a large agent and still bounded. Unbounded is not an
# option: one hung build stalls the whole batch forever, which loses every
# candidate after it.
BUILD_TIMEOUT_S = 1800
INSPECT_TIMEOUT_S = 60

RECIPE_PATH = "docker/generic.Dockerfile"


def recipe_sha(path: str = RECIPE_PATH) -> str:
    """sha256 of the build recipe, pinned into every build row.

    The recipe is an experimental variable. It decides which agents are
    buildable at all, and editing it changes the answer: the first live run
    failed two monorepos only because the recipe looked for an installable
    manifest at the repository root, and a recipe that looks one directory down
    makes both of them viable. Rows produced under different recipes are
    therefore different measurements, and a distribution computed across two of
    them is not one measurement.

    Recording it costs one file read per build and makes that boundary visible
    in the dataset instead of living in the commit history, where a reader of
    the numbers will never look.

    A recipe we cannot read is not a recipe we can attribute results to, so the
    exception propagates rather than defaulting to a placeholder digest that
    would make two different recipes look like one.
    """
    return "sha256:" + hashlib.sha256(Path(path).read_bytes()).hexdigest()


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


def _record_raised(c: Candidate, store: Store, stage: str,
                   exc: BaseException, prior_log: str = "",
                   recipe: str | None = None) -> BuildResult:
    """Turn a raised exception into a build row rather than a lost batch.

    Docker missing, the daemon down, a permission error: each raises
    FileNotFoundError or OSError from the runner, and each used to travel past
    build(), past run_pipeline() and out to the CLI as a traceback, taking every
    remaining candidate with it and writing no row to explain the loss.

    The class is UNKNOWN deliberately. An infrastructure failure on our side is
    not a fact about the agent, so it must not be filed as one; UNKNOWN is the
    bucket that shows up in the dataset asking to be looked at. The exception
    text is stored as the evidence so the row can be audited later.
    """
    detail = f"{stage} raised {type(exc).__name__}: {exc}"
    if prior_log:
        detail = f"{prior_log}\n\n{detail}"
    ref = store.blob(detail.encode())
    store.record("builds", candidate=c.slug, commit_sha=c.commit_sha,
                 status="failed", failure_class=str(FailureClass.UNKNOWN),
                 log_ref=ref, recipe_sha=recipe)
    return BuildResult(False, None, FailureClass.UNKNOWN, ref)


def declared_extras(slug: str, root: Path = Path("entrypoints")) -> str:
    """Extras an agent's entrypoint file declares for its build, comma-joined.

    Declared beside the invocation because the person who wrote the entrypoint
    is the one who found the agent could not reach a model without them, and
    recorded on the build row because an image built with extras is a
    different image.
    """
    path = root / f"{slug}.json"
    if not path.exists():
        return ""
    try:
        data = json.loads(path.read_text())
    except (OSError, ValueError):
        return ""
    return ",".join(str(x) for x in data.get("build_extras", []) or [])


async def build(c: Candidate, *, store: Store,
                run: Runner = default_runner,
                timeout_s: int = BUILD_TIMEOUT_S) -> BuildResult:
    tag = _tag(c)
    recipe = recipe_sha()
    extras = declared_extras(c.slug)
    try:
        code, log = await run(
            "docker", "build", "-t", tag,
            "--build-arg", f"REPO_URL={c.repo_url}",
            "--build-arg", f"COMMIT_PIN={c.commit_sha}",
            "--build-arg", f"EXTRAS={extras}",
            "-f", RECIPE_PATH, ".", timeout_s=timeout_s)
    except Exception as exc:
        return _record_raised(c, store, "docker build", exc, recipe=recipe)
    log_ref = store.blob(log.encode())

    if code != 0:
        failure = classify_build_log(log, code)
        store.record("builds", candidate=c.slug, commit_sha=c.commit_sha,
                     status="failed", failure_class=str(failure),
                     log_ref=log_ref, recipe_sha=recipe)
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
    try:
        dcode, digest = await run("docker", "image", "inspect", tag,
                                  "--format", "{{.Id}}",
                                  timeout_s=INSPECT_TIMEOUT_S)
    except Exception as exc:
        return _record_raised(c, store, "docker image inspect", exc,
                              prior_log=log, recipe=recipe)
    digest = digest.strip()
    if dcode != 0 or not digest.startswith("sha256:"):
        store.record("builds", candidate=c.slug, commit_sha=c.commit_sha,
                     status="failed", failure_class=str(FailureClass.BUILD_FAILED),
                     log_ref=log_ref, recipe_sha=recipe)
        return BuildResult(False, None, FailureClass.BUILD_FAILED, log_ref)

    store.record("builds", candidate=c.slug, commit_sha=c.commit_sha,
                 status="built", image_digest=digest, log_ref=log_ref,
                 recipe_sha=recipe, extras=extras or None)
    return BuildResult(True, digest, FailureClass.NONE, log_ref)


async def verify_environment(image_digest: str, *, store: Store,
                             run: Runner = default_runner,
                             timeout_s: int = 60,
                             shim: ShimConfig | None = None,
                             declared_credentials: tuple[str, ...] = (),
                             ) -> EnvCheckResult:
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

    A candidate declaring a credential the shim cannot supply is recorded as
    NEEDS_CREDENTIALS and not run. Running it would produce a failure whose real
    cause is a missing secret, filed under a class that blames the agent, and
    fabricating the secret would put a lie in the dataset.
    """
    missing = unsatisfiable(list(declared_credentials))
    if missing:
        ref = store.blob(
            ("declared credentials a local shim cannot honestly supply: "
             + ", ".join(missing)).encode())
        store.record("env_checks", build=image_digest, status="failed",
                     failure_class=str(FailureClass.NEEDS_CREDENTIALS),
                     evidence_ref=ref, duration_ms=0,
                     model=shim.model if shim is not None else None,
                     base_url=shim.base_url if shim is not None else None)
        return EnvCheckResult(False, FailureClass.NEEDS_CREDENTIALS, 0, ref)

    env_args: list[str] = []
    if shim is not None:
        for key, value in shim_env(shim).items():
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
    except Exception as exc:
        # Docker absent or the daemon down. Not a fact about the agent, so
        # UNKNOWN rather than a class that would blame it, and a row rather
        # than a traceback that loses every candidate after this one.
        ms = int((time.monotonic() - started) * 1000)
        ref = store.blob(
            f"docker run raised {type(exc).__name__}: {exc}".encode())
        store.record("env_checks", build=image_digest, status="failed",
                     failure_class=str(FailureClass.UNKNOWN),
                     evidence_ref=ref, duration_ms=ms,
                     model=model, base_url=base_url)
        return EnvCheckResult(False, FailureClass.UNKNOWN, ms, ref)

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
