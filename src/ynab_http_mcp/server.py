import asyncio
from fastmcp import FastMCP
import os
from dotenv import load_dotenv
from ynab_http_mcp.ynab_service import YnabService
import ynab_http_mcp.tools.categories as category_tools
import ynab_http_mcp.tools.planning as planning_tools
import ynab_http_mcp.tools.transactions as transaction_tools
import ynab_http_mcp.tools.accounts as account_tools


# Load .env
load_dotenv()  # loads .env into environment
# Initialize FastMCP server

HOST="0.0.0.0"
PORT=int(os.getenv("HTTP_PORT", 8000))
mcp = FastMCP("ynab")
# Create service:
ynab_service = YnabService()
# Register MCP tools:
category_tools.register(mcp, ynab_service)
planning_tools.register(mcp, ynab_service)
transaction_tools.register(mcp, ynab_service)
account_tools.register(mcp, ynab_service)


async def main():
    # Initialize and run the server
    await mcp.run_http_async(host=HOST, port=PORT)


if __name__ == "__main__":
    asyncio.run(main())
