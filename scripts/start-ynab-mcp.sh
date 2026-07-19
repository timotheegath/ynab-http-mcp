#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PID_FILE="$ROOT_DIR/.ynab_http_mcp.pid"
LOG_FILE="$ROOT_DIR/.ynab_http_mcp.log"

if [[ -f "$PID_FILE" ]] && kill -0 "$(cat "$PID_FILE")" 2>/dev/null; then
  echo "ynab_http_mcp already running with PID $(cat "$PID_FILE")"
  exit 0
fi

cd "$ROOT_DIR"

# Mark logs
  {
    echo
    echo "============================================================"
    echo "RUN START $(date -u +'%Y-%m-%dT%H:%M:%SZ')"
    echo "COMMAND: source .venv/bin/activate && python -m ynab_http_mcp"
    echo "WORKDIR: $ROOT_DIR"
    echo "============================================================"
   } >> "$LOG_FILE"



nohup bash -lc 'source .venv/bin/activate && exec python -m ynab_http_mcp' >> "$LOG_FILE" 2>&1 &
echo $! > "$PID_FILE"
echo "started ynab_http_mcp with PID $(cat "$PID_FILE")"
