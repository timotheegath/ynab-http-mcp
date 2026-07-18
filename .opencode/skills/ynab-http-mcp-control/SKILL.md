---
name: ynab-http-mcp-control
description: Manage the ynab_http_mcp Python module with reliable start, stop, and status commands.
---

# ynab-http-mcp-control

Use this skill when you need to run the `ynab_http_mcp` Python module in the background from the repository root and stop it later without guessing process names.

## Behavior rules

- Always start the service with `bash scripts/start-ynab-mcp.sh`
- Always stop the service with `bash scripts/stop-ynab-mcp.sh`
- Check state with `bash scripts/status-ynab-mcp.sh`
- Never kill by process name when `.ynab_http_mcp.pid` exists
- Use `.ynab_http_mcp.log` to inspect startup failures
- If the PID file exists but the process is dead, remove the stale PID file and start again

## Commands

### Start

```bash
bash scripts/start-ynab-mcp.sh
```

### Stop

```bash
bash scripts/stop-ynab-mcp.sh
```

### Status

```bash
bash scripts/status-ynab-mcp.sh
```

### Restart

```bash
bash scripts/stop-ynab-mcp.sh || true
bash scripts/start-ynab-mcp.sh
```

## Notes for OpenCode

When asked to start the YNAB MCP service:

1. Run `bash scripts/status-ynab-mcp.sh`
2. If already running, report that it is already running and include the PID
3. Otherwise run `bash scripts/start-ynab-mcp.sh`
4. If startup fails, inspect `.ynab_http_mcp.log`

When asked to stop the YNAB MCP service:

1. Run `bash scripts/status-ynab-mcp.sh`
2. If running, run `bash scripts/stop-ynab-mcp.sh`
3. If not running, report that it is not running

## Rationale

The command:

```bash
source .venv/bin/activate && python -m ynab_http_mcp &
```

starts a background job, but it does not create a reliable control surface for later stop, status, or restart operations. This skill adds:

- a PID file for precise process control,
- a log file for debugging,
- `nohup` so the process survives terminal disconnects,
- `exec` so the recorded PID belongs to the Python process.
