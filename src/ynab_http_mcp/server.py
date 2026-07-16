from mcp.server.fastmcp import FastMCP
from dotenv import load_dotenv
from ynab_http_mcp.ynab_service import YnabService
import ynab_http_mcp.tools.categories as category_tools
import ynab_http_mcp.tools.planning as planning_tools
import ynab_http_mcp.tools.transactions as transaction_tools


# Initialize FastMCP server
mcp = FastMCP("ynab")

# Load .env
load_dotenv()  # loads .env into environment

# Initialize FastMCP server
mcp = FastMCP("ynab")
# Create service:
ynab_service = YnabService()
# Register MCP tools:
category_tools.register(mcp, ynab_service)
planning_tools.register(mcp, ynab_service)
transaction_tools.register(mcp, ynab_service)


def main():
    # Initialize and run the server
    mcp.run(transport="streamable-http")


if __name__ == "__main__":
    main()
