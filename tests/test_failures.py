from crucible.failures import FailureClass, classify_build_log


# Real BuildKit output. Note the trailer: every failing build names the
# Dockerfile and the line that failed, which is why "dockerfile" cannot be a
# needle for "no build recipe".
DEPENDENCY_LOG = """\
#12 [5/5] RUN if [ -f pyproject.toml ]; then pip install --no-cache-dir -e .;
#12 3.412 ERROR: Could not find a version that satisfies the requirement \
torch==2.0.99 (from myagent) (from versions: 2.0.0, 2.0.1, 2.1.0)
#12 3.412 ERROR: No matching distribution found for torch==2.0.99
#12 ERROR: process "/bin/sh -c if [ -f pyproject.toml ]; then pip install \
--no-cache-dir -e .; fi" did not complete successfully: exit code: 1
------
 > [5/5] RUN if [ -f pyproject.toml ]; then pip install --no-cache-dir -e .;:
3.412 ERROR: No matching distribution found for torch==2.0.99
------
docker/generic.Dockerfile:16
--------------------
  14 |     RUN git clone "$REPO_URL" . && git checkout "$COMMIT_PIN"
  15 |
  16 | >>> RUN if [ -f pyproject.toml ]; then pip install --no-cache-dir -e .; \\
  17 |     elif [ -f requirements.txt ]; then pip install -r requirements.txt; \\
--------------------
ERROR: failed to solve: process "/bin/sh -c ..." did not complete \
successfully: exit code: 1
"""

NO_RECIPE_LOG = """\
#11 [4/5] RUN if [ -f pyproject.toml ]; then pip install --no-cache-dir -e .;
#11 0.221 no installable manifest
#11 ERROR: process "/bin/sh -c ..." did not complete successfully: exit code: 1
------
docker/generic.Dockerfile:16
--------------------
  16 | >>> RUN if [ -f pyproject.toml ]; then pip install --no-cache-dir -e .; \\
--------------------
ERROR: failed to solve: process "/bin/sh -c ..." did not complete \
successfully: exit code: 1
"""

COMPILE_FAILURE_LOG = """\
#12 41.02 gcc -pthread -B /usr/bin -fPIC -c src/fast.c -o build/fast.o
#12 41.31 src/fast.c:9:10: fatal error: Python.h: No such file or directory
#12 41.31 compilation terminated.
#12 41.52 error: command '/usr/bin/gcc' failed with exit code 1
------
docker/generic.Dockerfile:16
--------------------
  16 | >>> RUN if [ -f pyproject.toml ]; then pip install --no-cache-dir -e .; \\
--------------------
ERROR: failed to solve: process "/bin/sh -c ..." did not complete \
successfully: exit code: 1
"""

MISSING_DOCKERFILE_LOG = (
    "ERROR: failed to solve: failed to read dockerfile: open "
    "/var/lib/docker/tmp/buildkit-mount2751/docker/generic.Dockerfile: "
    "no such file or directory\n"
)

CLONE_FAILURE_LOG = """\
#10 [3/5] RUN git clone "$REPO_URL" . && git checkout "$COMMIT_PIN"
#10 0.412 Cloning into '.'...
#10 1.004 remote: Repository not found.
#10 1.004 fatal: repository 'https://github.com/x/y/' not found
------
docker/generic.Dockerfile:14
--------------------
  14 | >>> RUN git clone "$REPO_URL" . && git checkout "$COMMIT_PIN"
--------------------
ERROR: failed to solve: process "/bin/sh -c ..." did not complete \
successfully: exit code: 128
"""


def test_classifies_the_common_real_world_failures() -> None:
    cases = [
        (DEPENDENCY_LOG, 1, FailureClass.DEPENDENCY_CONFLICT),
        (CLONE_FAILURE_LOG, 1, FailureClass.CLONE_FAILED),
        (MISSING_DOCKERFILE_LOG, 1, FailureClass.NO_BUILD_RECIPE),
        (NO_RECIPE_LOG, 1, FailureClass.NO_BUILD_RECIPE),
        (COMPILE_FAILURE_LOG, 1, FailureClass.BUILD_FAILED),
    ]
    for log, code, expected in cases:
        assert classify_build_log(log, code) is expected, log


def test_a_dependency_failure_is_not_filed_as_a_missing_build_recipe() -> None:
    """BuildKit names the Dockerfile and line in the trailer of essentially
    every failed build. Matching the bare word "dockerfile" therefore filed
    genuine dependency failures as "no build recipe", which means the opposite
    of what happened, and would have dominated the first published
    distribution with a class describing the wrong thing."""
    assert "generic.Dockerfile:16" in DEPENDENCY_LOG
    assert classify_build_log(DEPENDENCY_LOG, 1) is FailureClass.DEPENDENCY_CONFLICT


def test_a_missing_recipe_is_still_a_missing_recipe() -> None:
    """Both halves must hold: the sentinel our own Dockerfile echoes, and a
    Dockerfile docker could not read at all. Both logs also contain
    "failed to solve", so this pins the ordering as well as the needles."""
    assert "failed to solve" in NO_RECIPE_LOG
    assert classify_build_log(NO_RECIPE_LOG, 1) is FailureClass.NO_BUILD_RECIPE
    assert classify_build_log(MISSING_DOCKERFILE_LOG, 1) is FailureClass.NO_BUILD_RECIPE


def test_the_word_repository_alone_is_not_a_clone_failure() -> None:
    """pip, apt and echoed READMEs all say "repository" during a healthy build
    step, so the bare word claimed unrelated failures as clone failures."""
    log = ("#9 0.8 Looking in indexes: https://pypi.org/simple\n"
           "#9 0.9 Cloning the upstream repository metadata cache\n"
           "#9 2.1 error: subprocess-exited-with-error\n"
           "ERROR: failed to solve: process did not complete successfully\n")
    assert classify_build_log(log, 1) is FailureClass.BUILD_FAILED


def test_success_is_not_a_failure_class() -> None:
    assert classify_build_log("Successfully built", 0) is FailureClass.NONE


def test_an_unrecognized_failure_is_named_rather_than_guessed() -> None:
    """Silently bucketing an unknown failure into a known class would
    corrupt the distribution the paper reports."""
    assert classify_build_log("something nobody predicted", 7) is FailureClass.UNKNOWN


def test_every_class_has_a_human_readable_label() -> None:
    for fc in FailureClass:
        assert fc.label and not fc.label.endswith(".")
