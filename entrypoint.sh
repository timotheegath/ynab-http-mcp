#!/bin/bash
set -e

# If YNAB_API_KEY is not set, try to get it from a file (useful for Kubernetes secrets)
if [ -z "${YNAB_API_KEY}" ] && [ -f "/run/secrets/ynab_api_key" ]; then
    export YNAB_API_KEY=$(cat /run/secrets/ynab_api_key)
fi

# Print some debug info if DEBUG_MODE is enabled
if [ "${DEBUG_MODE:-false}" = "true" ]; then
    echo "Starting YNAB HTTP MCP (DEBUG_MODE=true)..."
    echo "LOG_LEVEL: ${LOG_LEVEL:-info}"
    echo "YNAB_PLAN_ID: ${YNAB_PLAN_ID}"
    echo "DEBUG_MODE: ${DEBUG_MODE}"
fi

# Activate virtual environment
. /app/.venv/bin/activate

# When DEBUG_MODE=true, launch under debugpy so VS Code can attach on port 5678.
# Otherwise exec the CMD as-is.
if [ "${DEBUG_MODE:-false}" = "true" ]; then
    exec python -m debugpy --listen 0.0.0.0:5678 -m ynab_http_mcp
else
    exec "$@"
fi
