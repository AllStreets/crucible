#!/bin/sh
# Resolve and install a repository's Node package.
#
# The sibling of resolve_manifest.sh, and it exists for the same reason that
# one does: the sentinels it prints are read by the failure classifier, so they
# must be printed only on the path that they name. BuildKit echoes the whole
# failing RUN command in its error trailer, which is why this is a file the
# Dockerfile calls by path rather than a block written inline. That trap cost
# this project a misclassified build once already; see resolve_manifest.sh.
#
# `set -u` and deliberately not `set -e`, for the same reason as its sibling:
# a step that dies silently leaves a failed build with no evidence of why, and
# a build with no evidence gets filed against the agent.
#
# Why this recipe exists at all. Two of the most widely run coding agents in
# the seed list were recorded as being written in a language this project does
# not build, which is true and is a limit of the harness rather than a fact
# about them. The population of agents people actually run is now mostly
# TypeScript, so a Python-only instrument measures a shrinking corner of the
# field and reports it as if it were the field.

set -u

echo "crucible: resolving a node package in $(pwd)"

if [ ! -f package.json ]; then
    # Say which language it is rather than claiming there is nothing here. A
    # Python project reaching this recipe is our routing mistake, not its
    # defect, and the reverse case is already handled in resolve_manifest.sh.
    for marker in pyproject.toml setup.py go.mod Cargo.toml pom.xml; do
        if [ -f "$marker" ]; then
            echo "crucible: no package.json, but $marker is present at the root"
            echo "crucible-result: unsupported project language"
            exit 1
        fi
    done
    echo "crucible: no package.json at the repository root"
    echo "crucible-result: no installable manifest"
    exit 1
fi

# The package manager is whichever one the repository locked with. Guessing
# wrong is not a small thing here: a workspace locked with pnpm and installed
# with npm resolves a different dependency graph, which would make the row a
# measurement of our guess.
if [ -f pnpm-lock.yaml ]; then
    MANAGER="pnpm"
elif [ -f yarn.lock ]; then
    MANAGER="yarn"
elif [ -f bun.lockb ] || [ -f bun.lock ]; then
    MANAGER="bun"
elif [ -f package-lock.json ]; then
    MANAGER="npm-ci"
else
    MANAGER="npm"
fi
echo "crucible: lockfile says the package manager is $MANAGER"

# A step the kernel kills for running the machine out of memory is a fact
# about the machine, and it has to reach the classifier as one. The first
# version of this script ran a fallback install and then exited 1, which
# replaced the kill signal with its own status: a Node agent whose native
# module was being compiled when the machine ran out of memory was recorded as
# an agent that fails to build. Every install here reports the real status.
died_of_memory() {
    # 137 is the shell's encoding of SIGKILL, which on a build host is almost
    # always the out-of-memory killer. Nothing else in an install path sends it.
    [ "$1" = "137" ] || [ "$1" = "9" ]
}

run_install() {
    "$@"
    status=$?
    if died_of_memory "$status"; then
        echo "crucible: $1 was killed while installing, which on this host means"
        echo "crucible: the machine ran out of memory, commonly while a native"
        echo "crucible: module was being compiled from source"
        echo "crucible-result: build host out of memory"
        exit 3
    fi
    return $status
}

case "$MANAGER" in
    pnpm)
        corepack enable >/dev/null 2>&1
        corepack prepare pnpm@latest --activate >/dev/null 2>&1
        run_install pnpm install --frozen-lockfile || run_install pnpm install || exit 1
        ;;
    yarn)
        corepack enable >/dev/null 2>&1
        run_install yarn install --frozen-lockfile || run_install yarn install || exit 1
        ;;
    bun)
        if ! command -v bun >/dev/null 2>&1; then
            echo "crucible: this repository is locked with bun and the image has no bun"
            echo "crucible-result: unsupported project language"
            exit 1
        fi
        run_install bun install || exit 1
        ;;
    npm-ci)
        # npm ci refuses a lockfile that disagrees with package.json, which is
        # a real disagreement in the repository and worth reporting as one,
        # but it also refuses lockfiles written by much older npm versions.
        run_install npm ci || run_install npm install || exit 1
        ;;
    npm)
        run_install npm install || exit 1
        ;;
esac

# A build step, only when the repository declares one. Most TypeScript agents
# ship sources and compile on install; the ones that do not have no build
# script and must not be given one here.
if node -e "process.exit(require('./package.json').scripts?.build ? 0 : 1)" 2>/dev/null; then
    echo "crucible: package.json declares a build script, running it"
    case "$MANAGER" in
        pnpm) pnpm run build || exit 1 ;;
        yarn) yarn build || exit 1 ;;
        bun)  bun run build || exit 1 ;;
        *)    npm run build || exit 1 ;;
    esac
fi

# Installing is not evidence that anything is runnable, the same way pip
# exiting zero is not evidence that a Python package was installed. A package
# with no bin entry is a library: it will import, and it will never be an agent
# anyone can invoke, and finding that out now is cheaper than finding it out
# when an entrypoint is being written.
#
# The bin is looked for at the root and then in the workspace, because the
# shape of a Node agent is almost always a private workspace root with the
# command in a package below it. The Python recipe learned the same lesson the
# expensive way: searching only the root reported our own shallowness as the
# agent having no installable package.
find_bin() {
    if node -e "process.exit(require('./package.json').bin ? 0 : 1)" 2>/dev/null; then
        echo "."
        return 0
    fi
    for depth in 2 3; do
        found=$(find . -mindepth "$depth" -maxdepth "$depth" -name package.json \
                     -not -path './node_modules/*' -not -path './*/node_modules/*' \
                     -not -path './.*' 2>/dev/null \
                | while read -r m; do
                      d=$(dirname "$m")
                      if node -e "process.exit(require('$PWD/$d/package.json').bin ? 0 : 1)" 2>/dev/null; then
                          echo "$d"
                      fi
                  done)
        [ -n "$found" ] && { printf '%s\n' "$found"; return 0; }
    done
    return 1
}

BINDIRS=$(find_bin)
if [ -z "$BINDIRS" ]; then
    echo "crucible: nothing at the root or in the workspace declares a bin entry"
    echo "crucible-result: node package has no bin"
    exit 2
fi

COUNT=$(printf '%s\n' "$BINDIRS" | grep -c .)
if [ "$COUNT" -gt 1 ]; then
    # One stated rule before refusing, and it is the convention every Node
    # agent in this seed list follows: the command lives in the package
    # directory called cli. When none does, the build stops rather than
    # picking one, because a row labelled with the agent's name that is
    # actually about whichever package sorted first is worse than no row.
    CHOSEN=$(printf '%s\n' "$BINDIRS" | while read -r d; do
        [ "$(basename "$d")" = "cli" ] && echo "$d"
    done | head -1)
    if [ -z "$CHOSEN" ]; then
        echo "crucible: several packages declare a bin and none of them is the cli package:"
        printf '  %s\n' $BINDIRS
        echo "crucible-result: ambiguous installable manifest"
        exit 1
    fi
    echo "crucible: $COUNT packages declare a bin, choosing $CHOSEN by the cli rule"
else
    CHOSEN="$BINDIRS"
fi

# Put the command on PATH under the name the package gives it, so an agent
# written for Node is invoked the same way as one written for Python and the
# entrypoint files do not have to know which recipe built the image.
NAME=$(node -e "const b=require('$PWD/$CHOSEN/package.json').bin; console.log(typeof b === 'string' ? require('$PWD/$CHOSEN/package.json').name.split('/').pop() : Object.keys(b)[0])")
TARGET=$(node -e "const b=require('$PWD/$CHOSEN/package.json').bin; console.log(typeof b === 'string' ? b : b[Object.keys(b)[0]])")
ABS="$PWD/$CHOSEN/$TARGET"
if [ ! -f "$ABS" ]; then
    echo "crucible: $NAME points at $TARGET, which the install did not produce"
    echo "crucible-result: node package has no bin"
    exit 2
fi
chmod +x "$ABS" 2>/dev/null
printf '#!/bin/sh\nexec node "%s" "$@"\n' "$ABS" > "/usr/local/bin/$NAME"
chmod +x "/usr/local/bin/$NAME"

echo "crucible: installed; $NAME is on PATH and runs $ABS"
exit 0
