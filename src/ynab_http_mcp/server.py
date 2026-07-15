from ynab_http_mcp.debug import is_debug_enabled, debug_ynab_response, debug_exception
from typing import Any
from uuid import UUID

import ynab
from mcp.server.fastmcp import FastMCP
from dotenv import load_dotenv
from ynab_http_mcp.ynab_service import YnabService
import ynab_http_mcp.tools.categories as category_tools
import os


# Load .env
load_dotenv()  # loads .env into environment

# Initialize FastMCP server
mcp = FastMCP("ynab")
# Create service:
ynab_service = YnabService()
category_tools.register(mcp, ynab_service)

def main():
    # Initialize and run the server
    mcp.run(transport="streamable-http")


if __name__ == "__main__":
    main()