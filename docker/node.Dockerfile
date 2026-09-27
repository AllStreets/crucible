# Build recipe for agents written for Node. The sibling of
# generic.Dockerfile, and subject to the same rule: it is an experimental
# variable, every build row pins a sha256 of these bytes, and rows produced
# under two recipes are two measurements that must not be pooled.
#
# It exists because the instrument had a language-shaped hole in it. Two of the
# most widely run coding agents in the seed list were recorded as written in a
# language this project does not build, which was true and was a fact about the
# harness rather than about them. Most agents people run today are TypeScript,
# so a Python-only instrument was measuring a shrinking corner of the field and
# publishing the distribution as though it were the field.
# The base is a declared variable here for the same reason it is in the Python
# recipe: a row that does not say which base produced it is only comparable
# with rows from before the variable existed.
ARG BASE=node:22-slim
FROM ${BASE}

ARG REPO_URL
ARG COMMIT_PIN
# Versions to force after the agent's own resolution, declared by the seed and
# recorded on the build row. Same contract as the Python recipe.
ARG PINS=""

# git to clone; python3, make and a compiler because a surprising number of
# Node agents pull a native module that builds from source on install, and a
# missing compiler reports itself as the agent failing to install.
RUN apt-get update && apt-get install -y --no-install-recommends \
        git ca-certificates python3 make g++ \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
RUN git clone "$REPO_URL" . && git checkout "$COMMIT_PIN"

# The logic lives in a script rather than inline because BuildKit echoes the
# whole failing RUN command in its error trailer, so a sentinel written inline
# appears in the log of every failed build of this recipe whatever actually
# went wrong, and the failure classifier reads those logs. See
# docker/resolve_node.sh and the longer note in docker/resolve_manifest.sh.
COPY docker/resolve_node.sh /opt/crucible/resolve_node.sh
RUN sh /opt/crucible/resolve_node.sh

RUN if [ -n "$PINS" ]; then \
        echo "crucible: forcing declared pins: $PINS"; \
        npm install --no-save $PINS; \
    fi

# The default command is an environment probe, not the agent. It starts the
# runtime, prints one line and exits, and that is the whole of what the check
# downstream measures. It deliberately does not invoke the agent: with egress
# denied and no credentials an invocation would measure this harness rather
# than the agent. Nothing may report the result of this probe as a boot, and
# nothing may report it as evidence that an agent ran.
CMD ["node", "-e", "console.log('crucible environment probe ok')"]
