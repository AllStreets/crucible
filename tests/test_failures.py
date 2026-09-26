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

# Verbatim from the first run against a live Docker daemon, 2026-09-26:
# Significant-Gravitas/AutoGPT at 5e84f064d3. Trimmed to the decisive lines.
MONOREPO_ROOT_LOG = """\
#7 200.5 HEAD is now at 5e84f064d3 fix(frontend/marketplace): make public expert \
profiles readable by search engines (SECRT-2749) (#14902)
#7 DONE 200.8s

#8 [5/5] RUN if [ -f pyproject.toml ]; then pip install --no-cache-dir -e .; \
elif [ -f requirements.txt ]; then pip install --no-cache-dir -r requirements.txt; \
elif [ -f setup.py ]; then pip install --no-cache-dir -e .; \
else echo "no installable manifest"; exit 1; fi
#8 0.289 no installable manifest
#8 ERROR: process "/bin/sh -c ..." did not complete successfully: exit code: 1
------
generic.Dockerfile:16
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
        (NO_RECIPE_LOG, 1, FailureClass.NO_INSTALLABLE_MANIFEST),
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
    """Both halves must hold, and they are now different classes. Both logs
    also contain "failed to solve", so this pins the ordering as well as the
    needles."""
    assert "failed to solve" in NO_RECIPE_LOG
    assert classify_build_log(NO_RECIPE_LOG, 1) is FailureClass.NO_INSTALLABLE_MANIFEST
    assert classify_build_log(MISSING_DOCKERFILE_LOG, 1) is FailureClass.NO_BUILD_RECIPE


def test_a_monorepo_root_is_not_reported_as_having_no_build_recipe() -> None:
    """Verbatim from the first live run: AutoGPT and OpenHands both cloned
    cleanly, ran four of five build steps, and failed only because neither
    keeps an installable manifest at the repository root. Reporting that as
    "no usable build recipe" tells a reader we have no way to build these
    agents. The truthful statement is that our recipe looked only at the root
    and their package sits one directory down, which is our gap and not the
    agent's. The two imply different work, so the distribution must not merge
    them."""
    assert classify_build_log(MONOREPO_ROOT_LOG, 1) is (
        FailureClass.NO_INSTALLABLE_MANIFEST
    )
    assert classify_build_log(MONOREPO_ROOT_LOG, 1) is not FailureClass.NO_BUILD_RECIPE
    # The clone reached a real commit, so this is demonstrably not a clone or
    # recipe problem: four of five steps ran.
    assert "HEAD is now at 5e84f064d3" in MONOREPO_ROOT_LOG


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


# git's wording when the clone itself cannot reach the remote.
CLONE_DNS_LOG = """\
#10 [3/5] RUN git clone "$REPO_URL" . && git checkout "$COMMIT_PIN"
#10 0.301 Cloning into '.'...
#10 5.112 fatal: unable to access 'https://github.com/x/y/': \
Could not resolve host: github.com
------
docker/generic.Dockerfile:14
--------------------
  14 | >>> RUN git clone "$REPO_URL" . && git checkout "$COMMIT_PIN"
--------------------
ERROR: failed to solve: process "/bin/sh -c ..." did not complete \
successfully: exit code: 128
"""

# The same words, from apt, three steps after the clone succeeded.
INSTALL_DNS_LOG = """\
#9 [3/5] RUN git clone "$REPO_URL" . && git checkout "$COMMIT_PIN"
#9 0.412 Cloning into '.'...
#9 3.884 DONE
#12 [5/5] RUN pip install --no-cache-dir -e .
#12 1.004 WARNING: Retrying after connection broken by NewConnectionError
#12 8.221 Could not resolve host: files.pythonhosted.org
#12 8.500 ERROR: Could not install packages due to an OSError
------
docker/generic.Dockerfile:16
--------------------
  16 | >>> RUN if [ -f pyproject.toml ]; then pip install --no-cache-dir -e .; \\
--------------------
ERROR: failed to solve: process "/bin/sh -c ..." did not complete \
successfully: exit code: 1
"""


def test_a_clone_that_cannot_resolve_the_host_is_a_clone_failure() -> None:
    assert classify_build_log(CLONE_DNS_LOG, 1) is FailureClass.CLONE_FAILED


def test_an_outage_during_the_install_step_is_not_blamed_on_the_clone() -> None:
    """apt, curl and pip print "could not resolve host" too, and the clone step's
    output sits in the same log because it ran and succeeded. Unguarded, a
    network outage mid-install published as a clone failure."""
    assert "could not resolve host" in INSTALL_DNS_LOG.lower()
    assert "Cloning into" in INSTALL_DNS_LOG
    assert classify_build_log(INSTALL_DNS_LOG, 1) is not FailureClass.CLONE_FAILED
    assert classify_build_log(INSTALL_DNS_LOG, 1) is FailureClass.BUILD_FAILED
