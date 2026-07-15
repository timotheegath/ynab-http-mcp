# OpenCode Agent Instructions for ynab-http-mcp

## Project Overview
- **Type**: Python MCP (Micro Content Provider) server for YNAB (You Need A Budget) HTTP streaming
- **Entry point**: `src/ynab_http_mcp/server.py`
- **Main module**: `ynab_http_mcp`
- **Language**: Python 3.12+

## Key Commands

### Development
```bash
# Run the main entry point
uv run python -m ynab_http_mcp

# Or via installed script
ynab-http-mcp
```

### Testing
```bash
# Run tests (no test files currently exist)
uv run pytest

# Type checking
uv run mypy src/

# Linting
uv run ruff check src/

# Formatting
uv run ruff format src/
```

### Build
```bash
# Build package
uv build
```

## Environment Setup

### Required Environment Variables
- `YNAB_API_KEY`: Your YNAB API key (loaded from `.env`)
- `LOG_LEVEL`: Optional, defaults to "debug" in dev
- `DEBUG_MODE`: Optional, enables debug logging

### .env File
The project uses `python-dotenv` to load environment variables from `.env`. Example:
```
YNAB_API_KEY="your_api_key_here"
LOG_LEVEL="debug"
DEBUG_MODE=True
```

## Project Structure

```
src/
└── ynab_http_mcp/
    ├── __init__.py      # Main entry point
    ├── server.py        # FastMCP server implementation
    └── debug.py         # Debugging utilities
```

## Key Dependencies

### Production
- `dotenv`: Environment variable loading
- `httpx`: HTTP client
- `mcp[cli]`: Micro Content Provider framework
- `ynab`: YNAB API client

### Development
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

- Uses `FastMCP` from `mcp.server.fastmcp`
- Server initialized with `FastMCP("weather")` (note: "weather" appears to be a placeholder)
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
