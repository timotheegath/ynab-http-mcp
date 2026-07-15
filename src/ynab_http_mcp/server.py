from ynab_http_mcp.debug import is_debug_enabled, debug_ynab_response, debug_exception
from ynab_http_mcp.plans import set_default_plan
from typing import Any
from uuid import UUID

import ynab
from mcp.server.fastmcp import FastMCP
from dotenv import load_dotenv
import os


# Load .env
load_dotenv()  # loads .env into environment

# Initialize FastMCP server
mcp = FastMCP("weather")

# Logging


# Credentials / Config
YNAB_CONFIG = ynab.Configuration(access_token=os.getenv("YNAB_API_KEY"))

# Set plan
PLAN_ID = set_default_plan(YNAB_CONFIG)


with ynab.ApiClient(YNAB_CONFIG) as api_client:
    plans_api = ynab.PlansApi(api_client)
    plans_response = plans_api.get_plans()
    debug_ynab_response("Plans: ", plans_response)
