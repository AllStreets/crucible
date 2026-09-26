"""What went wrong, as a closed vocabulary.

The first paper reports a distribution over these, so they are defined once
here rather than as ad hoc strings. UNKNOWN exists and is load-bearing: an
unrecognized failure bucketed into a neighbouring class would silently distort
the published distribution, so anything unmatched is named as unmatched and
shows up in the dataset asking to be looked at.
"""
from __future__ import annotations

from enum import StrEnum


class FailureClass(StrEnum):
    NONE = "none"
    CLONE_FAILED = "clone_failed"
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
_BUILD_PATTERNS: tuple[tuple[str, FailureClass], ...] = (
    # Dependency resolution, as pip, uv and poetry actually word it.
    ("could not find a version that satisfies", FailureClass.DEPENDENCY_CONFLICT),
    ("no matching distribution found", FailureClass.DEPENDENCY_CONFLICT),
    ("conflicting dependencies", FailureClass.DEPENDENCY_CONFLICT),
    ("resolutionimpossible", FailureClass.DEPENDENCY_CONFLICT),
    ("the conflict is caused by", FailureClass.DEPENDENCY_CONFLICT),
    ("no solution found when resolving dependencies", FailureClass.DEPENDENCY_CONFLICT),
    # Clone, as git words it. Our Dockerfile clones inside the build, so these
    # arrive in the build log rather than from a separate clone step.
    ("fatal: repository", FailureClass.CLONE_FAILED),
    ("repository not found", FailureClass.CLONE_FAILED),
    ("could not read from remote repository", FailureClass.CLONE_FAILED),
    ("could not resolve host", FailureClass.CLONE_FAILED),
    ("fatal: reference is not a tree", FailureClass.CLONE_FAILED),
    # No usable build recipe. The first needle is the exact sentinel our own
    # Dockerfile echoes when a repository has no installable manifest; the rest
    # are docker's wording for a Dockerfile that could not be read at all.
    ("no installable manifest", FailureClass.NO_BUILD_RECIPE),
    ("failed to read dockerfile", FailureClass.NO_BUILD_RECIPE),
    ("cannot locate specified dockerfile", FailureClass.NO_BUILD_RECIPE),
    # Generic build failure last. "failed to solve" is BuildKit's wrapper around
    # every failing step whatever the cause, so it is only the answer when
    # nothing more specific matched.
    ("failed to solve", FailureClass.BUILD_FAILED),
    ("did not complete successfully", FailureClass.BUILD_FAILED),
    ("returned a non-zero code", FailureClass.BUILD_FAILED),
)


def classify_build_log(log: str, exit_code: int) -> FailureClass:
    if exit_code == 0:
        return FailureClass.NONE
    lowered = log.lower()
    for needle, cls in _BUILD_PATTERNS:
        if needle in lowered:
            return cls
    return FailureClass.UNKNOWN
