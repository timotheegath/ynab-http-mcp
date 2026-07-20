# ynab-http-mcp

HTTP Streaming MCP for YNAB capabilities

## Overview

This project provides an HTTP-based Micro Content Provider (MCP) server that enables agents to interact with a user's YNAB (You Need A Budget) budget. The goal is to help users gain insights into their spending habits, optimize their budget planning, and perform bulk operations like cleaning up payee names or categorizing transactions.

## Key Dependencies

- **[ynab-sdk-python](https://github.com/ynab/ynab-sdk-python)**: The official YNAB Python SDK used to interact with the YNAB API.
- **FastMCP**: A lightweight framework for building MCP servers.

## Key Capabilities

### Adding a new transaction

### Getting planning advice based on previous spending trends

### Automatically triage transactions

```plain
Triage all transactions from the last few days. If any doubt on categories, ask me.
```

### Help optimize money assignment

```plain
I am reaching the end of my Eating Out money. Which money could I reassign confidently?
```

### Bulk cleanup operations

- Clean up payee names
- Categorize transactions in bulk
- Identify and merge duplicate payees

### Month Planning Resources

- **Get all months**: `data://months` - Retrieve summary of all plan months
- **Get specific month**: `data://months/{YYYY-MM-DD}` - Get detailed planning data for a specific month
- **Get month category**: `data://months/{YYYY-MM-DD}/categories/{category_id}` - Get category details for a specific month

## Environment Variables

- `YNAB_API_KEY`: Your YNAB API key (loaded from `.env`, and for docker, specified at runtime.)
- `YNAB_PLAN_ID`: Optional. The YNAB plan ID to use. If not set, the server will use the plan that was modified the latest.
- `HTTP_PORT`: Optional. The port where the MCP server will listen. If not set, defaults to 8000.
- `LOG_LEVEL`: Optional, defaults to "debug" in dev
- `DEBUG_MODE`: Optional, enables debug logging

## Running the server

```bash
# Run the server
uv run ynab-http-mcp
```

### Running in Docker

#### Build the image

```bash
docker build -t ynab-http-mcp .
```

#### Run with proper configuration

```bash
docker run -d \
  --name ynab-server \
  -e YNAB_API_KEY="your_api_key" \
  -e YNAB_PLAN_ID="your_plan_id" \
  -p 8000:8000 \
  ynab-http-mcp
```

Or using an env file:

```bash
docker run --env-file .env -d --name ynab-server -p 8000:8000 ynab-http-mcp
```

#### View logs

```bash
docker logs ynab-server
```

#### Stop when done

```bash
docker stop ynab-server
```

## Testing

Test using MCP Inspector:

```bash
# Run the server and point MCP Inspector to it
uv run ynab-http-mcp & npx @modelcontextprotocol/inspector --remote http://127.0.0.1:8000/mcp
```

## Migration Guide (v1.1.0)

### Changes in this Version

- **Planning tools converted to resources**: All planning endpoints have been converted from `@mcp.tool()` to `@mcp.resource()` decorators for consistency.
- **New month-category endpoint**: Added `data://months/{month_date}/categories/{category_id}` for direct access to category details within a specific month.
- **Improved date handling**: All month endpoints now accept both `YYYY-MM` and `YYYY-MM-DD` formats.

### API Changes

#### Old Tool Endpoints (Deprecated)
```
POST /mcp/tools/get_plan_month
POST /mcp/tools/get_all_plan_months
```

#### New Resource Endpoints
```
GET /mcp/data://months
GET /mcp/data://months/{month_date}
GET /mcp/data://months/{month_date}/categories/{category_id}
```

### Migration Steps

1. **Update endpoint URLs**: Replace tool endpoints with resource endpoints
2. **Change HTTP method**: Use GET instead of POST for resource endpoints
3. **Update date formats**: Use ISO format dates (`YYYY-MM-DD` or `YYYY-MM`)
4. **Handle responses**: Resource endpoints return the same JSON structure as before

### Example Migration

**Before (Tool)**:
```json
{
  "tool": "get_plan_month",
  "parameters": {
    "month_date": "2023-12-15"
  }
}
```

**After (Resource)**:
```
GET /mcp/data://months/2023-12-15
```

## To do

- Milliunits conversion into normal currency for the LLM
- Add target-specific tools, and translate complex fields into LLM readable knowledge
- Add transactions as resources with filtering.
- Update Docker health check to work with proxy deployments, don't test localhost:8000