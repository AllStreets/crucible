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
#11 0.221 crucible-result: no installable manifest
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

#8 [5/5] RUN sh /opt/crucible/resolve_manifest.sh
#8 0.289 crucible-result: no installable manifest
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


PYTHON_FLOOR_LOG = """\
#8 0.194 crucible: found a single package definition at ./classic
#8 0.839 Obtaining file:///app/classic
#8 5.870 ERROR: Package 'autogpt-classic' requires a different Python: \
3.11.15 not in '<4.0,>=3.12'
#8 ERROR: process "/bin/sh -c sh /opt/crucible/resolve_manifest.sh" did not \
complete successfully: exit code: 1
------
generic.Dockerfile:25
--------------------
ERROR: failed to solve: process "/bin/sh -c sh /opt/crucible/resolve_manifest.sh" \
did not complete successfully: exit code: 1
"""

AMBIGUOUS_LOG = """\
#8 0.201 crucible: found 3 package definitions and will not guess between them:
#8 0.201   ./agent
#8 0.201   ./evaluation
#8 0.201   ./runtime
#8 0.202 crucible-result: ambiguous installable manifest
#8 ERROR: process "/bin/sh -c sh /opt/crucible/resolve_manifest.sh" did not \
complete successfully: exit code: 1
------
ERROR: failed to solve: process "/bin/sh -c sh /opt/crucible/resolve_manifest.sh" \
did not complete successfully: exit code: 1
"""


def test_a_python_floor_above_the_base_image_is_its_own_class() -> None:
    """Found by running: AutoGPT's only installable subproject requires Python
    >=3.12 and our base image is 3.11.15. That is a fact about the agent and a
    fact about our harness at once, and it is fixable on our side by offering
    more than one base image, so the distribution has to be able to say how much
    of the failure rate is this rather than something about the agent."""
    assert classify_build_log(PYTHON_FLOOR_LOG, 1) is (
        FailureClass.PYTHON_VERSION_UNSUPPORTED
    )
    # It resolved a manifest fine, so it is emphatically not a manifest failure.
    assert classify_build_log(PYTHON_FLOOR_LOG, 1) is not (
        FailureClass.NO_INSTALLABLE_MANIFEST
    )


def test_a_sentinel_must_not_be_matchable_from_the_buildkit_trailer() -> None:
    """BuildKit echoes the entire failing RUN command in its error trailer, so
    a sentinel written inline in the Dockerfile appears in the log of every
    failed build of that recipe whatever went wrong.

    The first version of the manifest logic was inline, and its "ambiguous"
    sentinel matched a build that had found exactly one subproject and failed
    inside pip. The classifier reads these logs, so the leak did not merely look
    untidy, it misclassified the dataset. The logic now lives in a script and
    the trailer carries only its path.
    """
    for log in (PYTHON_FLOOR_LOG, AMBIGUOUS_LOG):
        assert "resolve_manifest.sh" in log, "trailer should name the script"
        assert "ambiguous installable manifest" not in log.split("------")[-1], (
            "no sentinel may appear in the trailer half of the log"
        )
    assert classify_build_log(AMBIGUOUS_LOG, 1) is FailureClass.AMBIGUOUS_MANIFEST


def test_a_build_that_merely_ran_the_script_is_not_an_ambiguous_manifest() -> None:
    """The regression that motivated the split: a log whose only mention of the
    script is the trailer must not be claimed by a manifest class."""
    bare = (
        'ERROR: failed to solve: process "/bin/sh -c sh '
        '/opt/crucible/resolve_manifest.sh" did not complete successfully: '
        "exit code: 1\n"
    )
    result = classify_build_log(bare, 1)
    assert result is not FailureClass.AMBIGUOUS_MANIFEST
    assert result is not FailureClass.NO_INSTALLABLE_MANIFEST
    assert result is FailureClass.BUILD_FAILED


WORKSPACE_ROOT_LOG = """\
#10 0.183 crucible: found a single package definition at ./python
#10 0.756   Installing build dependencies: started
#10 1.462   error: subprocess-exited-with-error
#10 1.462       error: Multiple top-level packages discovered in a flat-layout: \
['samples', 'packages', 'templates'].
#10 ERROR: process "/bin/sh -c sh /opt/crucible/resolve_manifest.sh" did not \
complete successfully: exit code: 1
------
ERROR: failed to solve: process "/bin/sh -c sh /opt/crucible/resolve_manifest.sh" \
did not complete successfully: exit code: 1
"""


def test_a_workspace_root_is_not_a_generic_build_failure() -> None:
    """Found by running: autogen's python/pyproject.toml is a flat layout
    holding samples, packages and templates, so setuptools refuses to guess
    which is the distribution.

    Pooling this into build_failed loses the one fact that makes it actionable,
    which is that the agent sits one directory below a manifest we did find and
    needs a hand-written entrypoint naming it. A distribution exists to direct
    work, and a class that cannot direct any is a class that failed.
    """
    assert classify_build_log(WORKSPACE_ROOT_LOG, 1) is (
        FailureClass.WORKSPACE_ROOT_NOT_INSTALLABLE
    )
    assert classify_build_log(WORKSPACE_ROOT_LOG, 1) is not FailureClass.BUILD_FAILED
    # It resolved a manifest, so it is emphatically not a manifest failure.
    assert classify_build_log(WORKSPACE_ROOT_LOG, 1) is not (
        FailureClass.NO_INSTALLABLE_MANIFEST
    )


UNSUPPORTED_LANGUAGE_LOG = """\
#10 0.131 crucible: no Python package definition, but package.json is present at the root
#10 0.131 crucible-result: unsupported project language
#10 ERROR: process "/bin/sh -c sh /opt/crucible/resolve_manifest.sh" did not \
complete successfully: exit code: 1
"""


def test_a_typescript_agent_is_our_gap_and_not_its_defect() -> None:
    """continue and opencode are TypeScript and both ship a package.json, so
    they have an installable manifest. It is simply not one this recipe reads.

    Filing them under no_installable_manifest would place two of the most
    widely run coding agents in the dataset as defective, when the defect is
    the recipe's coverage. The same mistake, in three earlier forms, is what
    the first two live runs kept surfacing.
    """
    assert classify_build_log(UNSUPPORTED_LANGUAGE_LOG, 1) is (
        FailureClass.UNSUPPORTED_LANGUAGE
    )
    assert classify_build_log(UNSUPPORTED_LANGUAGE_LOG, 1) is not (
        FailureClass.NO_INSTALLABLE_MANIFEST
    )


FALSE_SUCCESS_LOG = """\
#10 0.132 crucible: found a package definition at the repository root
#10 6.221 Successfully installed UNKNOWN-0.0.0
#10 6.310 crucible: pip exited zero but installed a distribution named UNKNOWN,
#10 6.310 crucible: which means this manifest declares a workspace and not a package
#10 6.311 crucible-result: workspace root installed nothing
#10 ERROR: process "/bin/sh -c sh /opt/crucible/resolve_manifest.sh" did not \
complete successfully: exit code: 2
"""


def test_pip_exiting_zero_is_not_evidence_a_package_was_installed() -> None:
    """crewai's root pyproject declares crewai-workspace, a uv workspace rather
    than a distribution. setuptools installed it as a distribution named
    UNKNOWN, exited zero, and left the agent absent from the image.

    This was recorded as a successful build and passed the environment check,
    because the probe starts the interpreter without importing the agent. A
    false success is worse than a failure: it inflates the published viability
    rate, and nothing downstream can tell it from a real one.
    """
    assert classify_build_log(FALSE_SUCCESS_LOG, 2) is (
        FailureClass.WORKSPACE_ROOT_NOT_INSTALLABLE
    )
    # It must not read as a success or as a missing manifest.
    assert classify_build_log(FALSE_SUCCESS_LOG, 2) is not FailureClass.NONE
    assert classify_build_log(FALSE_SUCCESS_LOG, 2) is not (
        FailureClass.NO_INSTALLABLE_MANIFEST
    )


def test_a_full_disk_is_never_filed_against_the_agent():
    # Found by running. Two agents were recorded as build_failed when the
    # Docker VM's disk filled during apt, which in the published distribution
    # reads as a defect of the repository. It is a fact about the machine, and
    # the generic BuildKit wrapper that follows every failing step must not be
    # allowed to claim it.
    apt = ("#6 2.595 E: You don't have enough free space in /var/cache/apt/archives/.\n"
           "ERROR: failed to solve: process \"/bin/sh -c apt-get update\" "
           "did not complete successfully: exit code: 100")
    assert classify_build_log(apt, 1) is FailureClass.HOST_OUT_OF_DISK

    kernel = "OSError: [Errno 28] No space left on device\nERROR: failed to solve"
    assert classify_build_log(kernel, 1) is FailureClass.HOST_OUT_OF_DISK

    # And it stays specific: a genuine dependency failure is still that.
    dep = "ERROR: Could not find a version that satisfies the requirement lancedb==0.4.0"
    assert classify_build_log(dep, 1) is FailureClass.DEPENDENCY_CONFLICT
