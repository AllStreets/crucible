# Generic build recipe. Most agents are a pip-installable Python package; the
# fallbacks cover the common variations. A repository that matches none of them
# is a NO_BUILD_RECIPE observation rather than a bug to work around.
FROM python:3.11-slim

ARG REPO_URL
ARG COMMIT_PIN

RUN apt-get update && apt-get install -y --no-install-recommends \
        git ca-certificates build-essential \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
RUN git clone "$REPO_URL" . && git checkout "$COMMIT_PIN"

RUN if [ -f pyproject.toml ]; then pip install --no-cache-dir -e .; \
    elif [ -f requirements.txt ]; then pip install --no-cache-dir -r requirements.txt; \
    elif [ -f setup.py ]; then pip install --no-cache-dir -e .; \
    else echo "no installable manifest"; exit 1; fi

# The default command is an environment probe, not the agent. It starts the
# interpreter in the built image, prints one line and exits, and that is the
# whole of what the check downstream measures: this image runs in a clean
# sandbox. It deliberately does not invoke the agent. The repositories in the
# seed list share no entrypoint, and with egress denied and no credentials an
# invocation would measure this harness rather than the agent. Nothing in this
# repository may report the result of this probe as a boot, and nothing may
# report it as evidence that an agent ran.
CMD ["python", "-c", "print('crucible environment probe ok')"]
