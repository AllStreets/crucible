# Generic build recipe. Most agents are a pip-installable Python package; the
# fallbacks cover the common variations. A repository that matches none of them
# is a recorded observation rather than a bug to work around.
#
# This recipe is an experimental variable, and every build row pins a sha256 of
# these bytes. Editing it changes which agents are viable, so rows produced
# under two versions of this file are two measurements and must not be pooled.
# The base image is a declared variable, defaulting to the Python this recipe
# was written against. It is an argument rather than a constant because three
# agents in the seed list are unbuildable for one reason and one reason only:
# they require a Python newer than 3.11, directly or through a dependency. That
# is a limit of this harness, not a property of those repositories, and the
# honest fix is to let a seed line say which Python it needs and to record on
# the build row which one it got. Two rows built on two bases are two
# measurements, so the base travels with the row that it produced.
ARG BASE=python:3.11-slim
FROM ${BASE}

ARG REPO_URL
ARG COMMIT_PIN
# Optional extras to install with the package, declared per agent in its
# entrypoint file and recorded on the build row. An agent whose model client
# is an optional extra cannot reach a model without it.
ARG EXTRAS=""
ENV CRUCIBLE_EXTRAS=$EXTRAS

RUN apt-get update && apt-get install -y --no-install-recommends \
        git ca-certificates build-essential \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
RUN git clone "$REPO_URL" . && git checkout "$COMMIT_PIN"

# Root first, then exactly one directory down. The logic lives in a script
# rather than inline because BuildKit echoes the whole failing RUN command in
# its error trailer, and a sentinel string written inline therefore appears in
# the log of every failed build of this recipe whatever actually happened. The
# classifier reads those logs. See docker/resolve_manifest.sh.
COPY docker/resolve_manifest.sh /opt/crucible/resolve_manifest.sh
RUN sh /opt/crucible/resolve_manifest.sh

# Versions forced after the agent resolved its own, declared by the seed line
# and recorded on the build row. This exists for one situation and says so in
# the record: a transitive dependency whose current release is broken on the
# machine doing the building, where the agent has done nothing wrong and
# measuring it at all requires overriding what its own resolution chose. Two
# agents install a cryptography wheel that executes an instruction this host
# does not implement, and die on import before reaching any of their own code.
# A pinned build is a different measurement from an unpinned one, which is why
# it is a column and not a quiet fix.
ARG PINS=""
RUN if [ -n "$PINS" ]; then \
        echo "crucible: forcing declared pins: $PINS"; \
        pip install --no-cache-dir $PINS; \
    fi

# The default command is an environment probe, not the agent. It starts the
# interpreter in the built image, prints one line and exits, and that is the
# whole of what the check downstream measures: this image runs in a clean
# sandbox. It deliberately does not invoke the agent. The repositories in the
# seed list share no entrypoint, and with egress denied and no credentials an
# invocation would measure this harness rather than the agent. Nothing in this
# repository may report the result of this probe as a boot, and nothing may
# report it as evidence that an agent ran.
CMD ["python", "-c", "print('crucible environment probe ok')"]
