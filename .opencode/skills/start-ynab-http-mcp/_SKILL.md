---
name: Start YNAB-HTTP-MCP Server
description: Starts the YNAB-HTTP-MCP server. Assumes the virtual environment is already activated and runs the server using `uv run ynab_http_mcp`.
---

# Start YNAB-HTTP-MCP Server

## Usage
Use this skill when the user wants to start the YNAB-HTTP-MCP server. This skill ensures the server is launched correctly with the virtual environment already activated.

## Workflow
1. Ensure the virtual environment is activated.
2. Run the server using `setsid uv run -m ynab_http_mcp > /tmp/ynab_http_mcp.log 2>&1 < /dev/null &` as a background process. 
3. Do not block on it, wait until the server responds successfully, and move on.

## Example
```bash
setsid uv run -m ynab_http_mcp > /tmp/ynab_http_mcp.log 2>&1 < /dev/null &
```

## Notes
- The virtual environment must be activated before running this skill.
- Ensure the `.env` file is properly configured with the `YNAB_API_KEY`.
