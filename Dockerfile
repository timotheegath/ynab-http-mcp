# For more information, please refer to https://aka.ms/vscode-docker-python
FROM python:3.12-slim

# Keeps Python from generating .pyc files in the container
ENV PYTHONDONTWRITEBYTECODE=1

# Turns off buffering for easier container logging
ENV PYTHONUNBUFFERED=1

# Creates a non-root user with an explicit UID first
# For more info, please refer to https://aka.ms/vscode-docker-python-configure-containers
RUN adduser -u 5678 --disabled-password --gecos "" appuser

# NOTE: curl used to be installed here only for the HEALTHCHECK. The probe now
# uses the stdlib (see HEALTHCHECK below), so the layer was dropped.

# Runtime env vars that are truly build-time constants
ENV YNAB_PLAN_ID="6eb84411-a778-43db-ac70-54099d711d5c"
# LOG_LEVEL, DEBUG_MODE, and HTTP_PORT are intentionally NOT set here;
# they are injected at runtime via .env.dev / .env.prod.

WORKDIR /app

# Set INSTALL_DEV=true to include dev dependencies (mypy, pytest, ruff, debugpy, etc.)
# and bundle the test suite into the image. Defaults to false for lean production images.
ARG INSTALL_DEV=false

# Copy source files owned by appuser so the runtime user can write
# (pytest caches, .pyc, fixtures, etc.). --chown must be on each COPY.
COPY --chown=appuser:appuser pyproject.toml uv.lock ./
COPY --chown=appuser:appuser README.md ./
COPY --chown=appuser:appuser src/ ./src/

# In dev mode, also ship the test suite so `pytest` can run inside the container.
# In prod mode, the staged copy is removed so tests never land in the final image
# (the Dockerfile is the source of truth for what the runtime image contains).
COPY tests/ /tmp/tests-staged/
RUN if [ "$INSTALL_DEV" = "true" ]; then \
        mv /tmp/tests-staged /app/tests; \
    else \
        rm -rf /tmp/tests-staged; \
    fi

RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=from=ghcr.io/astral-sh/uv,source=/uv,target=/bin/uv \
    if [ "$INSTALL_DEV" = "true" ]; then \
        uv sync; \
    else \
        uv sync --no-dev; \
    fi

# uv sync runs as root and creates .venv/ and uv.lock metadata at the root
# level. Reown the whole workdir so appuser can write to .venv (e.g. python -m
# pip install, .pyc writes under .venv/lib/...) and any future test output,
# including the bundled tests/ directory from the dev build.
RUN chown -R appuser:appuser /app

USER appuser

# Documentation only: the server actually binds HTTP_PORT (default 8000, see
# env var table in README / src/ynab_http_mcp/server.py). Deployments set
# HTTP_PORT=3000 via .env.dev / .env.prod, which is what this EXPOSE refers to.
EXPOSE 3000

# Health check - HTTP GET of the liveness endpoint.
#
# Two things were wrong before, both of which made a healthy container report
# unhealthy: the probe hit "/" (which the MCP app answers with 404, and `curl -f`
# fails on any status >= 400), and it hardcoded port 3000 while the server binds
# HTTP_PORT (default 8000 when the env var is absent). The probe now reads the
# same env var the server does, with the same fallback, so the two cannot drift.
# Stdlib only - python:3.12-slim already ships Python, so no curl is needed.
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD python -c "import os, sys, urllib.request; port = os.getenv('HTTP_PORT', '8000'); sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:' + port + '/mcp/health', timeout=3).getcode() == 200 else 1)"

# Entry point script for flexibility
COPY --chown=appuser:appuser entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh
ENTRYPOINT ["/entrypoint.sh"]
CMD ["python", "-m", "ynab_http_mcp"]
