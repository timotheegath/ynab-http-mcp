# ynab-http-mcp

HTTP Streaming MCP server for YNAB capabilities — enables AI agents to read and write your YNAB budget.

## Overview

This project provides an HTTP-based Model Context Protocol (MCP) server that lets agents interact with a user's [YNAB](https://www.youneedabudget.com/) budget. It supports spending insights, budget planning, bulk transaction operations, and write operations for category budgets and transactions.

## Key Dependencies

- **[ynab-sdk-python](https://github.com/ynab/ynab-sdk-python)**: Official YNAB Python SDK.
- **[FastMCP](https://github.com/jlowin/fastmcp)**: Lightweight MCP server framework.

---

## Running the Server

### Local development (recommended)

```bash
# 1. Copy and fill in your dev credentials
cp .env.dev.example .env
# edit .env — set YNAB_API_KEY to your dev/sandbox key

# 2. Run
uv run ynab-http-mcp
```

On startup the server prints its environment:
- `✅ DEV MODE` — safe to experiment
- `⚠️ PRODUCTION MODE` — real YNAB data, handle with care

### Docker

Two compose overrides control the environment. **Always specify one explicitly.**

```bash
# Development — includes dev dependencies (mypy, pytest, ruff…)
docker compose -f compose.yaml -f compose.dev.yaml up

# Production — lean image, no dev deps, restart policy enabled
docker compose -f compose.yaml -f compose.prod.yaml up
```

Or build the image manually:

```bash
# Production image (default)
docker build -t ynab-http-mcp .

# Development image (includes dev deps)
docker build --build-arg INSTALL_DEV=true -t ynab-http-mcp .
```

View logs / stop:

```bash
docker logs ynab-server
docker stop ynab-server
```

---

## Environment Variables

| Variable | Required | Description |
|---|---|---|
| `YNAB_API_KEY` | ✅ | Your YNAB personal access token |
| `ENVIRONMENT` | recommended | `dev` or `prod` — controls the startup banner |
| `YNAB_PLAN_ID` | optional | Budget ID to use; defaults to most-recently-modified budget |
| `HTTP_PORT` | optional | Port for the MCP server (default: `8000`) |
| `LOG_LEVEL` | optional | Log verbosity (default: `debug`) |
| `DEBUG_MODE` | optional | Enable verbose debug logging (`True`/`False`) |

Templates:

```bash
cp .env.dev.example .env   # for local dev / agent sessions
cp .env.prod.example .env  # for production deploys only
```

> **Never commit `.env` or `.env.prod` to version control.**

---

## Development Workflow

- All development happens on the **`dev` branch**.
- Changes reach **`main`** only via a pull request with human approval.
- Coding agents must follow the rules in [`AGENTS.md`](AGENTS.md) — most importantly: never commit to `main` directly, never use prod credentials.

---

## Key Capabilities

### Read resources (Lean / Full / Aggregate)

Every entity follows a three-layer read convention:

- **Lean** (`data://accounts`, `data://transactions`, …) — minimal fields, fast, LLM-friendly.
- **Full** (`data://accounts/{id}/full`, …) — lean fields + `full_details` dict with every raw SDK field.
- **Aggregate** (`data://transactions/insights`) — pre-computed insights (monthly buckets, top payees/categories, spending trend).

### Write tools

- **`update_month_category`** — modify a category's budgeted amount for a given month.
- **`create_transaction`** — add a new transaction.

### Example agent prompts

```
Triage all transactions from the last few days. If any doubt on categories, ask me.
```

```
I am reaching the end of my Eating Out money. Which money could I reassign confidently?
```

---

## Resource URI Reference

### Lean resources

| URI | Description |
|---|---|
| `data://accounts` | All accounts |
| `data://accounts/{id}` | Single account |
| `data://categories` | All categories |
| `data://categories/{id}` | Single category |
| `data://months` | All plan months summary |
| `data://months/{YYYY-MM}` | Single plan month |
| `data://months/{YYYY-MM}/categories/{id}` | Per-month per-category |
| `data://payees` | All payees |
| `data://payees/{id}` | Single payee |
| `data://transactions` | Transactions (filterable) |
| `data://transactions/{id}` | Single transaction |
| `data://accounts/{id}/transactions` | Per-account transactions |
| `data://categories/{id}/transactions` | Per-category transactions |
| `data://months/{YYYY-MM}/transactions` | Per-month transactions |
| `data://payees/{id}/transactions` | Per-payee transactions |
| `data://budget/check-health/{month}` | Budget health metrics |
| `data://budget/spending-insights/{month}` | Spending analysis |

### Full (drill-in) resources

Append `/full` to any single-entity URI, e.g. `data://transactions/{id}/full`.

### Aggregate

| URI | Description |
|---|---|
| `data://transactions/insights` | Pre-computed insights (last 3 months by default) |

---

## Testing

```bash
# Full test suite
uv run pytest tests/

# MCP Inspector (interactive)
uv run ynab-http-mcp & npx @modelcontextprotocol/inspector --remote http://127.0.0.1:8000/mcp
```

---

## Migration Guide (v1.1.0)

Planning tools were converted from `@mcp.tool()` to `@mcp.resource()`. Update any clients using the old tool endpoints:

| Before | After |
|---|---|
| `POST /mcp/tools/get_plan_month` | `GET /mcp/data://months/{date}` |
| `POST /mcp/tools/get_all_plan_months` | `GET /mcp/data://months` |

All month endpoints accept both `YYYY-MM` and `YYYY-MM-DD` date formats.

---

## To Do

- Harmonize schemas: consistent `MCPResponse`/`MCPRequest`, remove duplicate validation code
- Implement basic authentication (now that write tools exist)
- Update Docker health check for proxy deployments (avoid relying on `curl` and `localhost:8000`)
