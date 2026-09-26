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

if [ -f pyproject.toml ] || [ -f setup.py ]; then
    echo "crucible: found a package definition at the repository root"
    exec pip install --no-cache-dir -e .
fi

if [ -f requirements.txt ]; then
    echo "crucible: found requirements.txt at the repository root"
    exec pip install --no-cache-dir -r requirements.txt
fi

# One level down, and one level only. Deeper searching finds vendored copies,
# test fixtures and example projects, none of which are the agent.
#
# Only pyproject.toml and setup.py count here. requirements.txt is excluded one
# level down because monorepos scatter them through docs, examples and CI
# directories, where they pin dependencies for something that is not the agent.
#
# sed rather than find's -printf, which is a GNU extension and absent on the
# busybox find some slim base images ship.
found=$(find . -mindepth 2 -maxdepth 2 \
             \( -name pyproject.toml -o -name setup.py \) \
             -not -path './.*' 2>/dev/null \
        | sed 's|/[^/]*$||' \
        | sort -u)

if [ -z "$found" ]; then
    echo "crucible: searched the root and one level down and found no package definition"
    echo "crucible-result: no installable manifest"
    exit 1
fi

count=$(printf '%s\n' "$found" | grep -c . 2>/dev/null || echo 0)

if [ "$count" -gt 1 ]; then
    # Refusing to choose is the point. Silently installing the alphabetically
    # first subproject of a monorepo yields a result labelled with the agent's
    # name that is actually about whichever component we happened to land on,
    # and nothing downstream could tell the difference. An ambiguous repository
    # needs a hand-written entrypoint, which is Phase 2 work.
    echo "crucible: found $count package definitions and will not guess between them:"
    printf '  %s\n' $found
    echo "crucible-result: ambiguous installable manifest"
    exit 1
fi

echo "crucible: found a single package definition at $found"
exec pip install --no-cache-dir -e "$found"
