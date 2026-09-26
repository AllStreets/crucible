# Generic build recipe. Most agents are a pip-installable Python package; the
# fallbacks cover the common variations. A repository that matches none of them
# is a recorded observation rather than a bug to work around.
#
# This recipe is an experimental variable, and every build row pins a sha256 of
# these bytes. Editing it changes which agents are viable, so rows produced
# under two versions of this file are two measurements and must not be pooled.
FROM python:3.11-slim

ARG REPO_URL
ARG COMMIT_PIN

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

# The default command is an environment probe, not the agent. It starts the
# interpreter in the built image, prints one line and exits, and that is the
# whole of what the check downstream measures: this image runs in a clean
# sandbox. It deliberately does not invoke the agent. The repositories in the
# seed list share no entrypoint, and with egress denied and no credentials an
# invocation would measure this harness rather than the agent. Nothing in this
# repository may report the result of this probe as a boot, and nothing may
# report it as evidence that an agent ran.
CMD ["python", "-c", "print('crucible environment probe ok')"]
