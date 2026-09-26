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

CMD ["python", "-c", "print('ready')"]
