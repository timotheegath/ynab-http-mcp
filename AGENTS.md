# OpenCode Agent Instructions for ynab-http-mcp

## ⚠️ Environment Safety Rules (READ FIRST)

> These rules exist to prevent accidental changes to production YNAB data.
> **Read and follow them before taking any action.**

- **ALWAYS work on the `dev` branch.** Never commit directly to `main`.
- **Use `.env.dev` credentials only.** Never read, write, or modify `.env.prod`.
- **Never run `compose.prod.yaml`.** All local runs must use `compose.dev.yaml`.
- **Before any start/restart, confirm `ENVIRONMENT=dev`** appears in the active `.env`.
- **To promote changes to prod:** open a PR from `dev` → `main` and wait for human approval. Do not merge it yourself.
- If in doubt about which environment is active, run `grep ENVIRONMENT .env` and stop if the output is not `ENVIRONMENT=dev`.

---

## Project Overview

- **Type**: Python MCP (Micro Content Provider) server for YNAB (You Need A Budget) HTTP streaming
- **Entry point**: `src/ynab_http_mcp/server.py`
- **Main module**: `ynab_http_mcp`
- **Language**: Python 3.12+


## Environment Setup

### Required Environment Variables

- `ENVIRONMENT`: `dev` or `prod` — controls startup banner and signals which credentials are active
- `YNAB_API_KEY`: Your YNAB API key (loaded from `.env`)
- `LOG_LEVEL`: Optional, defaults to `debug` in dev
- `DEBUG_MODE`: Optional, enables debug logging

### .env Files

The project uses `python-dotenv` to load environment variables from `.env`.
Two example templates are provided — never commit either with real credentials:

```text
.env.dev.example   # dev template  → cp .env.dev.example .env  (for development)
.env.prod.example  # prod template → cp .env.prod.example .env (for production deploy only)
```

Example dev `.env`:

```text
ENVIRONMENT=dev
YNAB_API_KEY="your_dev_api_key_here"
LOG_LEVEL="debug"
DEBUG_MODE=True
```

### Docker Compose

```bash
# Development (always use this in agent sessions)
docker compose -f compose.yaml -f compose.dev.yaml up

# Production (human-only, never from an agent session)
docker compose -f compose.yaml -f compose.prod.yaml up
```

## Project Structure

```text
src/
└── ynab_http_mcp/
    ├── __init__.py                 # Main entry point
    ├── server.py                   # FastMCP server implementation
    ├── debug.py                    # Debugging utilities
    ├── ynab_service.py             # YNAB SDK wrapper
    ├── schemas/                    # Pydantic models (Lean / Full / Aggregate)
    │   ├── base.py                 # Lean / Full / Aggregate convention docs
    │   ├── accounts.py             # MCPAccount, MCPAccountFull
    │   ├── categories.py           # MCPCategory, MCPCategoryGoal, MCPCategoryFull
    │   ├── payees.py               # MCPPayee, MCPPayeeFull
    │   ├── transactions.py         # MCPTransaction, MCPTransactionFull
    │   ├── planning.py             # PlanMonth, PlanMonthFull, MonthCategory
    │   ├── transaction_aggregate.py # TransactionInsightsResponse (Aggregate)
    │   └── money_movement_aggregate.py # MoneyMovementInsightsResponse (Aggregate)
    ├── tools/                      # FastMCP resource registrations
    │   ├── accounts.py             # data://accounts, data://accounts/{id}/full
    │   ├── categories.py           # data://categories, data://categories/{id}/full
    │   ├── payees.py               # data://payees, data://payees/{id}/full
    │   ├── planning.py             # data://months, data://months/{ym}/full, ...
    │   ├── transactions.py         # data://transactions, data://transactions/{id}/full,
    │   │                           # data://transactions/insights
    │   └── money_movements.py      # get_money_movement_insights,
    │                               # get_money_movement_insights_for_month (tools)
    └── utils/                      # helpers (dates, schema_utils)
```

## Key Dependencies

### Production dependencies

- `dotenv`: Environment variable loading
- `FastMCP`: Micro Content Provider framework
- `ynab`: YNAB API client

### Development dependencies

- `mypy`: Type checking
- `pytest`: Testing framework
- `pytest-asyncio`: Async test support
- `rich`: Pretty console output
- `ruff`: Linter and formatter

## Debugging Utilities

The `debug.py` module provides:

- `setup_logging()`: Configures structured logging
- `debug_json()`: Pretty-print JSON in debug mode
- `debug_response()`: Log HTTP responses
- `debug_exception()`: Log exceptions with traceback

Debug mode is enabled via `DEBUG_MODE=True` or `MY_MCP_DEBUG=1` environment variables.

## MCP Framework Notes

- Uses `FastMCP` from `fastmcp`
- Server initialized with `FastMCP("ynab")`
- YNAB API client is configured with access token from environment

## Important Files

- `pyproject.toml`: Project configuration, dependencies, and build settings
- `.env`: Environment variables (not committed to git)
- `uv.lock`: Lock file for reproducible builds

## Workflow Notes

1. **Environment first**: Always ensure `.env` is properly set up before running
2. **Debug mode**: Use `DEBUG_MODE=True` for detailed logging during development
3. **Type safety**: Run `mypy` before committing to catch type issues
4. **Code quality**: Use `ruff check` and `ruff format` for linting and formatting

## Server Control Procedures

Use the `ynab-http-mcp-control` skill for server management:

- **Start service**: `bash scripts/start-ynab-mcp.sh`
- **Stop service**: `bash scripts/stop-ynab-mcp.sh`
- **Check status**: `bash scripts/status-ynab-mcp.sh`
- **Restart service**: `bash scripts/stop-ynab-mcp.sh && bash scripts/start-ynab-mcp.sh`

Always check service status before testing and restart after code changes.


### Unit Tests

```bash
uv run pytest tests/                      # Run the full suite
uv run pytest tests/test_categories_schema.py  # Lean goal / cadence math
uv run pytest tests/test_transaction_aggregate.py  # Aggregate computation
uv run pytest tests/test_money_movement_aggregate.py  # Money-movement aggregate
uv run pytest tests/test_integration.py   # End-to-end lean shape
```

## Gotchas

- The YNAB API key is sensitive - never commit it to version control
- Debug logging can be verbose - disable with `DEBUG_MODE=False`
- The project uses `uv` for package management and building
- Lean resources are serialized with `exclude_none=True`; no
  `"key": null` noise in the wire format
- `full_details` is a `dict`, not a Pydantic model — the YNAB SDK
  already has the typed model; we ship a cleaned dict for LLM
  navigation

## Missing Components

- No CI/CD configuration found
- No comprehensive error handling in server.py
