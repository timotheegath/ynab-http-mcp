# For more information, please refer to https://aka.ms/vscode-docker-python
FROM python:3.12-slim

# Keeps Python from generating .pyc files in the container
ENV PYTHONDONTWRITEBYTECODE=1

# Turns off buffering for easier container logging
ENV PYTHONUNBUFFERED=1

# Creates a non-root user with an explicit UID first
# For more info, please refer to https://aka.ms/vscode-docker-python-configure-containers
RUN adduser -u 5678 --disabled-password --gecos "" appuser

# Runtime env vars that are truly build-time constants
ENV YNAB_PLAN_ID="6eb84411-a778-43db-ac70-54099d711d5c"
# LOG_LEVEL and DEBUG_MODE are intentionally NOT set here;
# they are injected at runtime via .env.dev / .env.prod.

WORKDIR /app

COPY pyproject.toml .
COPY README.md ./
COPY src/ ./src/

# Set INSTALL_DEV=true to include dev dependencies (mypy, pytest, ruff, etc.)
# Defaults to false for lean production images.
ARG INSTALL_DEV=false
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=from=ghcr.io/astral-sh/uv,source=/uv,target=/bin/uv \
    if [ "$INSTALL_DEV" = "true" ]; then \
        uv sync; \
    else \
        uv sync --no-dev; \
    fi

USER appuser

EXPOSE 8000

# Health check - simple TCP check on port 8000
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:8000/ || exit 1

# Entry point script for flexibility
COPY --chown=appuser:appuser entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh
ENTRYPOINT ["/entrypoint.sh"]
CMD ["python", "src/ynab_http_mcp/__main__.py"]
