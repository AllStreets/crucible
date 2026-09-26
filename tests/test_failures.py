from crucible.failures import FailureClass, classify_build_log


def test_classifies_the_common_real_world_failures() -> None:
    cases = [
        ("ERROR: Could not find a version that satisfies the requirement foo",
         1, FailureClass.DEPENDENCY_CONFLICT),
        ("fatal: repository 'https://github.com/x/y' not found",
         128, FailureClass.CLONE_FAILED),
        ("Dockerfile: no such file or directory",
         1, FailureClass.NO_BUILD_RECIPE),
        ("no installable manifest", 1, FailureClass.NO_BUILD_RECIPE),
        ("ERROR: failed to solve: process did not complete successfully",
         1, FailureClass.BUILD_FAILED),
    ]
    for log, code, expected in cases:
        assert classify_build_log(log, code) is expected, log


def test_success_is_not_a_failure_class() -> None:
    assert classify_build_log("Successfully built", 0) is FailureClass.NONE


def test_an_unrecognized_failure_is_named_rather_than_guessed() -> None:
    """Silently bucketing an unknown failure into a known class would
    corrupt the distribution the paper reports."""
    assert classify_build_log("something nobody predicted", 7) is FailureClass.UNKNOWN


def test_every_class_has_a_human_readable_label() -> None:
    for fc in FailureClass:
        assert fc.label and not fc.label.endswith(".")
