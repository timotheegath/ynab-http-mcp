from ynab_http_mcp.debug import is_debug_enabled, debug_ynab_response, debug_exception

from typing import Any

import ynab
from mcp.server.fastmcp import FastMCP
from dotenv import load_dotenv
import os


# Load .env
load_dotenv()  # loads .env into environment

# Initialize FastMCP server
mcp = FastMCP("weather")

# Logging


# Credentials
ynab_configuration = ynab.Configuration(access_token=os.getenv("YNAB_API_KEY"))

with ynab.ApiClient(ynab_configuration) as api_client:
    plans_api = ynab.PlansApi(api_client)
    plans_response = plans_api.get_plans()
    debug_ynab_response("Plans: ", plans_response)
