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
    BOOT_TIMEOUT = "boot_timeout"
    BOOT_CRASH = "boot_crash"
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
            FailureClass.BOOT_TIMEOUT: "Container did not become ready in time",
            FailureClass.BOOT_CRASH: "Container exited during startup",
            FailureClass.NEEDS_CREDENTIALS: "Requires credentials we do not supply",
            FailureClass.UNKNOWN: "Unclassified failure",
        }[self]


_BUILD_PATTERNS: tuple[tuple[str, FailureClass], ...] = (
    ("could not find a version that satisfies", FailureClass.DEPENDENCY_CONFLICT),
    ("no matching distribution found", FailureClass.DEPENDENCY_CONFLICT),
    ("conflicting dependencies", FailureClass.DEPENDENCY_CONFLICT),
    ("repository", FailureClass.CLONE_FAILED),
    ("could not resolve host", FailureClass.CLONE_FAILED),
    ("dockerfile", FailureClass.NO_BUILD_RECIPE),
    ("no installable manifest", FailureClass.NO_BUILD_RECIPE),
    ("failed to solve", FailureClass.BUILD_FAILED),
)


def classify_build_log(log: str, exit_code: int) -> FailureClass:
    if exit_code == 0:
        return FailureClass.NONE
    lowered = log.lower()
    for needle, cls in _BUILD_PATTERNS:
        if needle in lowered:
            return cls
    return FailureClass.UNKNOWN
