#!/bin/sh
# Resolve and install a repository's Python package.
#
# This lives in its own file rather than inline in the Dockerfile, and that is
# load-bearing rather than tidiness. BuildKit prints the entire failing RUN
# command in its error trailer, so any sentinel string written inline appears in
# the log of every failed build of this recipe whatever actually went wrong. The
# first version of this logic was inline, and its "ambiguous" sentinel matched
# builds that were not ambiguous at all: one had found exactly one subproject
# and failed inside pip. The failure classifier reads these logs, so a sentinel
# that leaks into the trailer does not merely look untidy, it silently
# misclassifies the dataset. The same trap is already documented in
# failures.py for the bare "dockerfile" needle.
#
# Every sentinel below is prefixed `crucible:` and is printed only on the path
# it names. The Dockerfile runs this script by path, so the trailer carries the
# path and nothing else.
#
# `set -u` but deliberately not `set -e`. The first version used `set -e`, and
# when the directory search returned a non-zero status the script died with no
# output whatever: a failed build carrying no evidence of why, which is
# unattributable and would have been filed against the agent. Each step here
# checks its own status and says what it found.

set -u

echo "crucible: resolving installable manifest in $(pwd)"

# install_and_verify <path>
#
# pip exiting zero is not evidence that a package was installed. A uv or
# poetry workspace root carries a pyproject.toml that names a workspace rather
# than a distribution, and setuptools installs it as a distribution literally
# named UNKNOWN, exits zero, and leaves the agent absent from the image. That
# is a false success, and a false success is worse than a failure: it inflates
# the viability rate and passes the environment check, because the probe starts
# the interpreter without ever importing the agent.
#
# crewai is the case that exposed this. Its root declares crewai-workspace and
# the real package sits in lib. autogen has the same shape and was caught only
# because setuptools happened to refuse it instead.
install_and_verify() {
    target="$1"
    if [ -n "${CRUCIBLE_EXTRAS:-}" ]; then
        echo "crucible: installing with extras [$CRUCIBLE_EXTRAS]"
        pip install --no-cache-dir -e "$target[$CRUCIBLE_EXTRAS]" || return 1
    else
        pip install --no-cache-dir -e "$target" || return 1
    fi

    # Requirements alongside a package definition are installed too. A
    # setup.py that under-declares its dependencies is common, and the
    # requirements file beside it is what the project's own instructions tell
    # a user to install. babyagi is that case: it installs from setup.py and
    # then cannot import its own database layer.
    if [ -f "$target/requirements.txt" ]; then
        echo "crucible: also installing requirements.txt beside the package"
        pip install --no-cache-dir -r "$target/requirements.txt" || return 1
    fi

    if find "$target" -maxdepth 1 -iname "UNKNOWN.egg-info" 2>/dev/null | grep -q .; then
        echo "crucible: pip exited zero but installed a distribution named UNKNOWN,"
        echo "crucible: which means this manifest declares a workspace and not a package"
        echo "crucible-result: workspace root installed nothing"
        return 2
    fi
    return 0
}

if [ -f pyproject.toml ] || [ -f setup.py ]; then
    echo "crucible: found a package definition at the repository root"
    install_and_verify .
    exit $?
fi

if [ -f requirements.txt ]; then
    echo "crucible: found requirements.txt at the repository root"
    exec pip install --no-cache-dir -r requirements.txt
fi

# Below the root, shallowest first.
#
# One level was not enough, and the first ten-agent run is why. langgraph keeps
# its package at libs/langgraph and autogen keeps its at python/packages, so a
# one-level search found nothing in one and a workspace root in the other, and
# both were recorded as failures of the agent when they were failures of this
# search. Real agent monorepos nest the installable package two directories
# down, which is a finding in its own right.
#
# Depths are tried shallowest first and the first depth that yields anything
# decides. Going deeper after a hit would start finding vendored copies, test
# fixtures and example projects, none of which are the agent.
#
# Only pyproject.toml and setup.py count below the root. requirements.txt is
# excluded because monorepos scatter them through docs, examples and CI
# directories, where they pin dependencies for something that is not the agent.
#
# sed rather than find's -printf, which is a GNU extension and absent on the
# busybox find some slim base images ship.
repo_name=$(basename "${REPO_URL:-}" .git)

found=""
for depth in 2 3; do
    found=$(find . -mindepth "$depth" -maxdepth "$depth" \
                 \( -name pyproject.toml -o -name setup.py \) \
                 -not -path './.*' 2>/dev/null \
            | sed 's|/[^/]*$||' \
            | sort -u)
    if [ -n "$found" ]; then
        echo "crucible: found package definitions at depth $((depth - 1))"
        break
    fi
done

if [ -z "$found" ]; then
    # Before reporting no manifest, check whether this is a project in a
    # language this recipe does not cover. continue and opencode are both
    # TypeScript and both have a package.json, so reporting that they have no
    # installable manifest blames them for a gap that is ours. The recipe is
    # Python only, and saying which language it actually is turns a wrong label
    # into a queued piece of work.
    for marker in package.json go.mod Cargo.toml pom.xml build.gradle; do
        if [ -f "$marker" ]; then
            echo "crucible: no Python package definition, but $marker is present at the root"
            echo "crucible-result: unsupported project language"
            exit 1
        fi
    done
    echo "crucible: searched the root and two levels below it, found no package definition"
    echo "crucible-result: no installable manifest"
    exit 1
fi

count=$(printf '%s\n' "$found" | grep -c . 2>/dev/null || echo 0)

if [ "$count" -gt 1 ]; then
    # One stated rule, applied before refusing: prefer the subproject whose
    # directory name is the repository's own name. In a monorepo that publishes
    # several packages, the one sharing the repository name is the agent and the
    # rest are its libraries, and langgraph is the case that motivated this.
    #
    # The rule is deterministic, is printed when it fires, and does not
    # generalise into a guess. When no directory matches, the build still stops
    # rather than picking the alphabetically first subproject, because a result
    # labelled with the agent's name that is actually about whichever component
    # we landed on is worse than no result. autogen is that case: it publishes
    # several packages and none is named for the repository, so it needs a
    # hand-written entrypoint, which is Phase 2 work.
    match=$(printf '%s\n' "$found" | while read -r d; do
        [ "$(basename "$d")" = "$repo_name" ] && echo "$d"
    done)
    matches=$(printf '%s\n' "$match" | grep -c . 2>/dev/null || echo 0)
    if [ "$matches" -eq 1 ]; then
        echo "crucible: $count candidates, choosing $match because its name is the repository's"
        install_and_verify "$match"
        exit $?
    fi
    echo "crucible: found $count package definitions and will not guess between them:"
    printf '  %s\n' $found
    echo "crucible: none is named for the repository, which is $repo_name"
    echo "crucible-result: ambiguous installable manifest"
    exit 1
fi

echo "crucible: found a single package definition at $found"
install_and_verify "$found"
exit $?
