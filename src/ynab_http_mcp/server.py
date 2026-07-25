import asyncio
import os
import sys

from dotenv import load_dotenv
from fastmcp import FastMCP
from fastmcp.server.transforms import ResourcesAsTools

import ynab_http_mcp.tools.accounts as account_tools
import ynab_http_mcp.tools.budget_management as budget_tools
import ynab_http_mcp.tools.categories as category_tools
import ynab_http_mcp.tools.payees as payee_tools
import ynab_http_mcp.tools.planning as planning_tools
import ynab_http_mcp.tools.transactions as transaction_tools
from ynab_http_mcp.ynab_service import YnabService

# Load .env
load_dotenv()  # loads .env into environment

# ── Environment banner ────────────────────────────────────────────────────────
_ENV = os.getenv("ENVIRONMENT", "dev")
if _ENV == "prod":
    print(
        "\033[1;31m⚠️  PRODUCTION MODE — real YNAB data. "
        "Do NOT run coding-agent sessions against this instance.\033[0m",
        file=sys.stderr,
    )
else:
    print(
        "\033[1;32m✅  DEV MODE — safe to experiment (ENVIRONMENT=dev).\033[0m",
        file=sys.stderr,
    )
# ─────────────────────────────────────────────────────────────────────────────

# Initialize FastMCP server
HOST = "0.0.0.0"
PORT = int(os.getenv("HTTP_PORT", 8000))
mcp = FastMCP("ynab")
# Create service:
ynab_service = YnabService()
# Register MCP tools:
category_tools.register(mcp, ynab_service)
planning_tools.register(mcp, ynab_service)
transaction_tools.register(mcp, ynab_service)
account_tools.register(mcp, ynab_service)
payee_tools.register(mcp, ynab_service)
budget_tools.register(mcp, ynab_service)
# For compatibility as resources are under-adopted.
mcp.add_transform(ResourcesAsTools(mcp))


async def main():
    # Initialize and run the server
    await mcp.run_http_async(host=HOST, port=PORT)


if __name__ == "__main__":
    asyncio.run(main())
