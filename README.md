# ynab-http-mcp

HTTP Streaming MCP for YNAB capabilities

## Environment Variables

- `YNAB_API_KEY`: Your YNAB API key (loaded from `.env`)
- `YNAB_PLAN_ID`: Optional. The YNAB plan ID to use. If not set, the server will use the plan that was modified the latest.
- `LOG_LEVEL`: Optional, defaults to "debug" in dev
- `DEBUG_MODE`: Optional, enables debug logging

## Running the server

```bash
# Run the server
uv run ynab-http-mcp
```

## Testing

Test using MCP Inspector:

```bash
# Run the server and point MCP Inspector to it
uv run ynab-http-mcp & npx @modelcontextprotocol/inspector --remote http://127.0.0.1:8000/mcp
```
