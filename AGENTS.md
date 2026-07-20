# OpenCode Agent Instructions for ynab-http-mcp

## Project Overview

- **Type**: Python MCP (Micro Content Provider) server for YNAB (You Need A Budget) HTTP streaming
- **Entry point**: `src/ynab_http_mcp/server.py`
- **Main module**: `ynab_http_mcp`
- **Language**: Python 3.12+



## Environment Setup

### Required Environment Variables

- `YNAB_API_KEY`: Your YNAB API key (loaded from `.env`)
- `LOG_LEVEL`: Optional, defaults to "debug" in dev
- `DEBUG_MODE`: Optional, enables debug logging

### .env File

The project uses `python-dotenv` to load environment variables from `.env`. Example:

```text
YNAB_API_KEY="your_api_key_here"
LOG_LEVEL="debug"
DEBUG_MODE=True
```

## Project Structure

```text
src/
└── ynab_http_mcp/
    ├── __init__.py      # Main entry point
    ├── server.py        # FastMCP server implementation
    └── debug.py         # Debugging utilities
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
- Server initialized with `FastMCP("")`
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
   read_mcp_resource(server="ynab-http-mcp", uri="data://accounts")
   ```

3. **Debug issues**:
   ```bash
   tail -50 .ynab_http_mcp.log  # Check service logs
   grep "Error" .ynab_http_mcp.log  # Search for errors
   ```

### Common Test Cases

- **Plan Month Resources**:
  - `data://months` - All plan months summary
  - `data://months/2024-01` - Specific month (YYYY-MM format)
  - `data://months/2024-01-15` - Specific month (YYYY-MM-DD format)
  - `data://months/2024-01/categories/{category_id}` - Month category details

- **Account Resources**:
  - `data://accounts` - All accounts
  - `data://accounts/{account_id}/transactions` - Account transactions

- **Category Resources**:
  - `data://categories` - All categories
  - `data://categories/{category_id}` - Specific category
  - `data://categories/{category_id}/transactions` - Category transactions

- **Payee Resources**:
  - `data://payees` - All payees
  - `data://payees/{payee_id}` - Specific payee
  - `data://payees/{payee_id}/transactions` - Payee transactions

- **Transaction Resources**:
  - `data://transactions` - All transactions
  - `data://transactions/{transaction_id}` - Specific transaction

## Gotchas

- The YNAB API key is sensitive - never commit it to version control
- Debug logging can be verbose - disable with `DEBUG_MODE=False`
- The project uses `uv` for package management and building
- No test suite currently exists - tests would need to be added

## Missing Components

- No CI/CD configuration found
- No test files exist
- No comprehensive error handling in server.py
- The "weather" MCP name suggests this might be a template or early-stage project
