"""What went wrong, as a closed vocabulary.

The first paper reports a distribution over these, so they are defined once
here rather than as ad hoc strings. UNKNOWN exists and is load-bearing: an
unrecognized failure bucketed into a neighbouring class would silently distort
the published distribution, so anything unmatched is named as unmatched and
shows up in the dataset asking to be looked at.

UNKNOWN holds one more thing, and a reader of the distribution needs to know it:
two failures of this harness rather than of an agent are filed here too, because
neither is a fact about the agent and no build class would be honest. They are
the build timeout (30 minutes, which heavy agents will hit) and the docker
command failing to run at all. Both store the exception text as evidence, so
they are identifiable in the dataset, and the report says so in its limitations.
"""
from __future__ import annotations

from enum import StrEnum


class FailureClass(StrEnum):
    NONE = "none"
    CLONE_FAILED = "clone_failed"
    NO_INSTALLABLE_MANIFEST = "no_installable_manifest"
    AMBIGUOUS_MANIFEST = "ambiguous_manifest"
    PYTHON_VERSION_UNSUPPORTED = "python_version_unsupported"
    WORKSPACE_ROOT_NOT_INSTALLABLE = "workspace_root_not_installable"
    UNSUPPORTED_LANGUAGE = "unsupported_language"
    NO_BUILD_RECIPE = "no_build_recipe"
    DEPENDENCY_CONFLICT = "dependency_conflict"
    BUILD_FAILED = "build_failed"
    ENV_CHECK_TIMEOUT = "env_check_timeout"
    ENV_CHECK_FAILED = "env_check_failed"
    NEEDS_CREDENTIALS = "needs_credentials"
    UNKNOWN = "unknown"

    @property
    def label(self) -> str:
        return {
            FailureClass.NONE: "No failure",
            FailureClass.CLONE_FAILED: "Repository could not be cloned",
            FailureClass.NO_INSTALLABLE_MANIFEST:
                "No installable manifest at the repository root",
            FailureClass.AMBIGUOUS_MANIFEST:
                "Several installable subprojects, none of them obviously the agent",
            FailureClass.PYTHON_VERSION_UNSUPPORTED:
                "Requires a Python version the base image does not provide",
            FailureClass.WORKSPACE_ROOT_NOT_INSTALLABLE:
                "The manifest found is a workspace root, not an installable package",
            FailureClass.UNSUPPORTED_LANGUAGE:
                "Written in a language this recipe does not build",
            FailureClass.NO_BUILD_RECIPE: "No usable build recipe",
            FailureClass.DEPENDENCY_CONFLICT: "Dependencies could not be resolved",
            FailureClass.BUILD_FAILED: "Build failed",
            FailureClass.ENV_CHECK_TIMEOUT:
                "Container environment probe did not finish in time",
            FailureClass.ENV_CHECK_FAILED:
                "Container environment probe exited non-zero",
            FailureClass.NEEDS_CREDENTIALS: "Requires credentials we do not supply",
            FailureClass.UNKNOWN: "Unclassified failure",
        }[self]


# Order is load-bearing, and so is the specificity of each needle. First match
# wins, so a needle must be specific to the condition its class names, or every
# log that merely mentions it is mis-bucketed.
#
# Two needles that were here before are gone because of that:
#
#   "dockerfile"  BuildKit's error trailer prints the Dockerfile path and line
#                 number ("docker/generic.Dockerfile:16") in essentially every
#                 failed build, so a bare "dockerfile" claimed almost every
#                 genuine dependency or compile failure as "no build recipe",
#                 which means the opposite of what happened.
#   "repository"  appears in ordinary pip and apt index chatter, in package
#                 metadata, and in half the READMEs echoed during a build, so
#                 it claimed unrelated failures as clone failures. Git's own
#                 wording is matched instead.
#
# Within that, specific-before-general: pip's resolver messages come first
# because a dependency failure is also wrapped by BuildKit's generic
# "failed to solve", which is therefore last of all.
#
# A third element, when present, is a guard: the needle only decides the class if
# the log also contains one of the guard strings. It exists for needles that are
# specific to a message but not to a stage. "could not resolve host" is the case:
# git prints it when a clone cannot reach the remote, and so do apt, curl and pip
# when egress drops during the dependency step, so unguarded it published a
# mid-install network outage as a clone failure.
#
# The guard is git's own transport-failure wording rather than anything naming
# the clone step. "cloning into" and "git clone" are both useless as guards: the
# clone step's output and the Dockerfile line that ran it appear in the log of
# every failed build, including one that failed three steps later. A guarded
# match that finds no git transport failure falls through to the generic build
# classes, which is the honest place for an outage we cannot attribute.
#
# ("no matching distribution found" has the same shape but is already inside
# dependency_conflict, where a network fault during resolution belongs, so it
# needs no guard.)
_GIT_TRANSPORT_FAILURE = ("fatal: unable to access", "fatal: clone of",
                          "could not read from remote repository",
                          "error: rpc failed")

_BUILD_PATTERNS: tuple[tuple[str, FailureClass, tuple[str, ...]], ...] = (
    # Dependency resolution, as pip, uv and poetry actually word it.
    ("could not find a version that satisfies", FailureClass.DEPENDENCY_CONFLICT, ()),
    ("no matching distribution found", FailureClass.DEPENDENCY_CONFLICT, ()),
    ("conflicting dependencies", FailureClass.DEPENDENCY_CONFLICT, ()),
    ("resolutionimpossible", FailureClass.DEPENDENCY_CONFLICT, ()),
    ("the conflict is caused by", FailureClass.DEPENDENCY_CONFLICT, ()),
    ("no solution found when resolving dependencies", FailureClass.DEPENDENCY_CONFLICT, ()),
    # Clone, as git words it. Our Dockerfile clones inside the build, so these
    # arrive in the build log rather than from a separate clone step.
    ("fatal: repository", FailureClass.CLONE_FAILED, ()),
    ("repository not found", FailureClass.CLONE_FAILED, ()),
    ("could not read from remote repository", FailureClass.CLONE_FAILED, ()),
    ("fatal: unable to access", FailureClass.CLONE_FAILED, ()),
    # Guarded: apt, curl and pip print this too when egress drops mid-install.
    ("could not resolve host", FailureClass.CLONE_FAILED, _GIT_TRANSPORT_FAILURE),
    ("fatal: reference is not a tree", FailureClass.CLONE_FAILED, ()),
    # Two conditions that were one class until the first live run separated
    # them. The sentinel our own Dockerfile echoes means the clone succeeded and
    # the recipe ran, and only the root had nothing pip could install: the case
    # of a monorepo whose package sits one directory down, where the agent is
    # fine and our recipe is too shallow. Docker failing to read a Dockerfile at
    # all is the opposite situation. Filing both as "no build recipe" told a
    # reader of the summary table that we had no way to build these, when for
    # every monorepo in the first run the truthful statement was that we had not
    # looked in the right directory. Different cause, different fix, so a
    # distribution that merges them misdirects the work it exists to direct.
    # A Python floor above the base image is a fact about the agent and a fact
    # about our harness at once, and it is fixable on our side by offering more
    # than one base image. It gets its own class so the distribution can say how
    # much of the failure rate is that rather than something about the agent.
    # Found by running: AutoGPT's installable subproject requires >=3.12 and the
    # base image is 3.11.
    # A manifest that exists but defines a workspace rather than a package.
    # autogen is the case: python/pyproject.toml is a flat layout holding
    # samples, packages and templates, and setuptools refuses to guess which is
    # the distribution. Pooling this into build_failed would lose the one fact
    # that makes it actionable, which is that the agent is one directory below
    # a manifest we did find and needs a hand-written entrypoint naming it.
    ("multiple top-level packages discovered in a flat-layout",
     FailureClass.WORKSPACE_ROOT_NOT_INSTALLABLE, ()),
    ("requires a different python", FailureClass.PYTHON_VERSION_UNSUPPORTED, ()),
    ("requires python >=", FailureClass.PYTHON_VERSION_UNSUPPORTED, ()),
    # These two read the script's own result lines, which are printed only on
    # the path they name. They must stay distinct from anything the Dockerfile
    # echoes; see docker/resolve_manifest.sh.
    # Ours, not theirs. The recipe builds Python, and a TypeScript agent with a
    # package.json has an installable manifest; it is simply not one we read.
    # Filing continue and opencode under no_installable_manifest would put two
    # of the most widely run coding agents in the dataset as defective when the
    # defect is the recipe's coverage.
    ("crucible-result: unsupported project language",
     FailureClass.UNSUPPORTED_LANGUAGE, ()),
    ("crucible-result: ambiguous installable manifest",
     FailureClass.AMBIGUOUS_MANIFEST, ()),
    ("crucible-result: no installable manifest",
     FailureClass.NO_INSTALLABLE_MANIFEST, ()),
    ("failed to read dockerfile", FailureClass.NO_BUILD_RECIPE, ()),
    ("cannot locate specified dockerfile", FailureClass.NO_BUILD_RECIPE, ()),
    # Generic build failure last. "failed to solve" is BuildKit's wrapper around
    # every failing step whatever the cause, so it is only the answer when
    # nothing more specific matched.
    ("failed to solve", FailureClass.BUILD_FAILED, ()),
    ("did not complete successfully", FailureClass.BUILD_FAILED, ()),
    ("returned a non-zero code", FailureClass.BUILD_FAILED, ()),
)


def classify_build_log(log: str, exit_code: int) -> FailureClass:
    if exit_code == 0:
        return FailureClass.NONE
    lowered = log.lower()
    for needle, cls, guard in _BUILD_PATTERNS:
        if needle not in lowered:
            continue
        if guard and not any(g in lowered for g in guard):
            continue
        return cls
    return FailureClass.UNKNOWN
