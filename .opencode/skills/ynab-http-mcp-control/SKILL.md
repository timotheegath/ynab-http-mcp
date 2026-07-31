---
name: ynab-http-mcp-control
description: Manage the ynab_http_mcp dev container with the project's docker compose dev override.
---

# ynab-http-mcp-control

Use this skill when you need to run the `ynab_http_mcp` dev container from the repository root and tear it down again.

The dev container is defined by `compose.yaml` + `compose.dev.yaml`. It mounts the workspace at `/app`, exposes the MCP HTTP endpoint on `:3000` and the debugpy listener on `:5678`, and loads `.env.dev`. These are the same commands the VS Code task `compose: up dev` runs (see `.vscode/tasks.json`) — keep the skill and the VS Code task in sync.

## Behavior rules

- Always start with `docker compose -f compose.yaml -f compose.dev.yaml up -d --build`
- Always stop with `docker compose -f compose.yaml -f compose.dev.yaml down`
- Always check state with `docker compose -f compose.yaml -f compose.dev.yaml ps`
- Tail logs with `docker compose -f compose.yaml -f compose.dev.yaml logs -f ynabhttpmcp`
- Never run `compose.prod.yaml` from an agent session — agent runs are dev-only
- Before any start/restart, confirm `ENVIRONMENT=dev` appears in the active `.env`

## Commands

### Start

```bash
docker compose -f compose.yaml -f compose.dev.yaml up -d --build
```

### Stop

```bash
docker compose -f compose.yaml -f compose.dev.yaml down
```

### Status

```bash
docker compose -f compose.yaml -f compose.dev.yaml ps
```

### Logs

```bash
docker compose -f compose.yaml -f compose.dev.yaml logs -f ynabhttpmcp
```

### Rebuild after code changes

```bash
docker compose -f compose.yaml -f compose.dev.yaml up -d --build
```

## Notes for OpenCode

When asked to start the YNAB MCP dev container:

1. Run `docker compose -f compose.yaml -f compose.dev.yaml ps`
2. If already running, report that and list the container name/state
3. Otherwise run `docker compose -f compose.yaml -f compose.dev.yaml up -d --build`
4. If startup fails, inspect logs with `docker compose -f compose.yaml -f compose.dev.yaml logs ynabhttpmcp`

When asked to stop the YNAB MCP dev container:

1. Run `docker compose -f compose.yaml -f compose.dev.yaml ps`
2. If running, run `docker compose -f compose.yaml -f compose.dev.yaml down`
3. If not running, report that it is not running

## Rationale

Running the service as a container matches how VS Code launches it for debugging (`.vscode/tasks.json` → `compose: up dev`) and gives us:

- a single source of truth for dev dependencies (`INSTALL_DEV=true` in `compose.dev.yaml`)
- a reproducible environment across machines
- `debugpy` on `:5678` ready for attach
- no PID files, no `nohup`, no log files left in the repo
