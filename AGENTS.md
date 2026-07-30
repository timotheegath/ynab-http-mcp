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
    │   └── transaction_aggregate.py # TransactionInsightsResponse (Aggregate)
    ├── tools/                      # FastMCP resource registrations
    │   ├── accounts.py             # data://accounts, data://accounts/{id}/full
    │   ├── categories.py           # data://categories, data://categories/{id}/full
    │   ├── payees.py               # data://payees, data://payees/{id}/full
    │   ├── planning.py             # data://months, data://months/{ym}/full, ...
    │   └── transactions.py         # data://transactions, data://transactions/{id}/full,
    │                               # data://transactions/insights
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

## Read-side Convention: Lean / Full / Aggregate

Every read resource follows a three-layer convention. The LLM's primary
read path is **Lean**; arithmetic / SDK-fidelity fields live in
**Full**; pre-computed insights live in **Aggregate**.

### Lean (default read shape)

- Identity fields (id, name)
- State booleans (hidden, deleted, internal, approved, closed)
- Minimum-viable raw fields needed for **filter / sort / date math**
- Formatted currency strings (e.g. `-$45.00`)
- Derived plain-English strings for opaque nested concepts
  (e.g. `goal_summary`, `goal_status`)

Lean models MUST NOT expose:

- Integer milliunit fields when a formatted string twin exists
- Formatted strings whose value is fully captured in a derived string
- Any field not needed for filter / sort / date math

Example — Lean `MCPTransaction` has only the formatted `amount: str`
(no `milli_amount` twin) and a nested lean `MCPCategoryGoal` (5
fields, not 16).

### Full (drill-in escape hatch)

Every lean model has a `*Full` sibling that inherits the lean fields
and adds exactly one new field, `full_details: dict`. The dict contains
the cleaned raw YNAB SDK object for the same entity — every field the
SDK exposes (including the dropped milliunit twins and every
discarded detail) is reachable by name inside the dict.

Example — `MCPTransactionFull` has the lean `MCPTransaction` fields
plus `full_details: dict` containing the cleaned raw
`ynab.TransactionDetail` (including the integer `amount` in
milliunits and the raw `subtransactions` array with integer amounts).

### Aggregate (pre-computed insights)

Pre-computed insights exposed at dedicated URIs. Currently only
`data://transactions/insights` returns a `TransactionInsightsResponse`
with monthly buckets, top-5 payees / categories, and a directional
`spending_trend`. Aggregates are never embedded in lean resources.

### The drop rule

A field is dropped from the lean layer if:

- A formatted string captures the same value (drop the raw integer
  twin)
- A derived string captures the raw field's value in prose
- The LLM never needs it for filter / sort / date math
- It is YNAB-internal metadata (import pipeline fields)

### Serialization

Lean resources are serialized with `model_dump_json(exclude_none=True)`
so `None` fields are omitted from the JSON output. The Full layer
follows the same convention for its lean fields; `full_details` is
itself never `None`.

## Resource URI Reference

### Lean resources (default read shape)

- `data://accounts` — all accounts
- `data://accounts/{account_id}` — single account
- `data://categories` — all categories
- `data://categories/{category_id}` — single category
- `data://months` — all plan months summary
- `data://months/{month_date}` — single plan month (YYYY-MM or YYYY-MM-DD)
- `data://months/{month_date}/categories/{category_id}` — per-month per-category
- `data://payees` — all payees
- `data://payees/{id}` — single payee
- `data://transactions` — transactions (with optional since_date, until_date, type, limit, account_id, payee_id, category_id, month filters)
- `data://transactions/{id}` — single transaction
- `data://accounts/{account_id}/transactions` — per-account transactions
- `data://categories/{category_id}/transactions` — per-category transactions
- `data://months/{month_date}/transactions` — per-month transactions (optional `type` filter; date filters intentionally unavailable because the URI path already scopes to a month)
- `data://payees/{payee_id}/transactions` — per-payee transactions

### Full (drill-in) resources — `*Full` shape with `full_details`

- `data://accounts/{account_id}/full`
- `data://categories/{category_id}/full`
- `data://months/{month_date}/full`
- `data://months/{month_date}/categories/{category_id}/full`
- `data://payees/{id}/full`
- `data://transactions/{id}/full`

### Aggregate resources

- `data://transactions/insights` — pre-computed insights
  (optional `since_date`, `until_date`, `account_id` parameters;
  default window is the last 3 calendar months)

## Breaking Changes

This server has applied the Lean / Full / Aggregate convention.
**BREAKING** changes for any client that reads the dropped fields
directly on a lean model:

- `MCPCategoryGoal` shrinks from 16 raw fields to **5 fields**
  (`goal_type`, `goal_target_date`, `goal_percentage_complete`,
  `goal_summary`, `goal_status`). All 11 dropped raw fields and the
  4 `*_formatted` companions are reachable via the drill-in path:
  `data://categories/{id}/full` → `full_details` (the same field
  names are preserved in the dict).
- `MCPTransaction.milli_amount` (integer milliunit twin of
  `amount`) is **dropped** from the lean layer. The integer value is
  recoverable via `data://transactions/{id}/full` →
  `full_details.amount`. The same rule applies to
  `MCPSubTransaction.milli_amount`, which is reachable via
  `full_details.subtransactions[i].amount`.
- `MonthCategory` (planning schema) drops its milliunit
  `budgeted` / `activity` / `balance` integer fields and the
  `goal_technical_details` string. Integer milliunits and the full
  raw goal field set are reachable via
  `data://months/{ym}/categories/{id}/full`.

The migration path is uniform: read the lean endpoint first, and
drill into the `/{id}/full` endpoint only when arithmetic or
SDK-fidelity access is required.

## Cadence Semantics for MF Goals

YNAB's `goal_cadence` integer encodes a base period; the
`goal_cadence_frequency` integer is a multiplier. The lean
`MCPCategoryGoal.goal_summary` prose reflects this directly:

- `cadence 0` → one-time (no repetition)
- `cadence 1` (Monthly) + `frequency 1` → "every 1 month" / "monthly"
- `cadence 1` + `frequency 2` → "every 2 months"
- `cadence 2` (Weekly) + `frequency 1` → "every 1 week" / "weekly"
- `cadence 2` + `frequency 2` → "every 2 weeks" (biweekly)
- `cadence 3-12` → "every (N-1) months" (frequency ignored)
- `cadence 13` (Yearly) + `frequency 1` → "every 1 year" / "yearly"
- `cadence 13` + `frequency 2` → "every 2 years"
- `cadence 14` → "every 2 years" (frequency ignored)

## Testing Procedures

Use the `ynab-http-mcp-testing` skill for comprehensive testing:

### MCP Resource Testing

1. **Discover resources**:
   ```python
   list_mcp_resources()  # List all available resources
   list_mcp_resource_templates()  # List parameterized endpoints
   ```

2. **Test specific resources**:
   ```python
   read_mcp_resource(server="ynab-http-mcp", uri="data://months")
   read_mcp_resource(server="ynab-http-mcp", uri="data://months/2024-01")
   read_mcp_resource(server="ynab-http-mcp", uri="data://categories/00000000-0000-0000-0000-000000000000/full")
   read_mcp_resource(server="ynab-http-mcp", uri="data://transactions/insights")
   ```

3. **Debug issues**:
   ```bash
   tail -50 .ynab_http_mcp.log  # Check service logs
   grep "Error" .ynab_http_mcp.log  # Search for errors
   ```

### Unit Tests

```bash
uv run pytest tests/                      # Run the full suite
uv run pytest tests/test_categories_schema.py  # Lean goal / cadence math
uv run pytest tests/test_transaction_aggregate.py  # Aggregate computation
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
