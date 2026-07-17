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

## Environment Variables

- `YNAB_API_KEY`: Your YNAB API key (loaded from `.env`, and for docker, specified at runtime.)
- `YNAB_PLAN_ID`: Optional. The YNAB plan ID to use. If not set, the server will use the plan that was modified the latest.
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
docker build -t ynab-mcp .
```

#### Run with proper configuration

```bash
docker run -d \
  --name ynab-server \
  -e YNAB_API_KEY="your_api_key" \
  -e YNAB_PLAN_ID="your_plan_id" \
  -p 8000:8000 \
  ynab-mcp
```

```bash
docker run -e YNAB_API_KEY="$YNAB_API_KEY" image-name
```

## Testing

Test using MCP Inspector:

```bash
# Run the server and point MCP Inspector to it
uv run ynab-http-mcp & npx @modelcontextprotocol/inspector --remote http://127.0.0.1:8000/mcp
```

## To do

- Move accounts, categories to resources