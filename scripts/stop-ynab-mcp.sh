#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PID_FILE="$ROOT_DIR/.ynab_http_mcp.pid"

if [[ ! -f "$PID_FILE" ]]; then
  echo "pid file not found; ynab_http_mcp may not be running"
  exit 0
fi

PID="$(cat "$PID_FILE")"

if kill -0 "$PID" 2>/dev/null; then
  kill "$PID"
  sleep 1
  if kill -0 "$PID" 2>/dev/null; then
    kill -9 "$PID"
  fi
  echo "stopped ynab_http_mcp (PID $PID)"
else
  echo "process $PID not running"
fi

rm -f "$PID_FILE"
