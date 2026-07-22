from ynab_http_mcp.ynab_service import YnabService
from ynab_http_mcp.schemas.accounts import MCPAccounts, MCPAccount
from ynab_http_mcp.schemas.transactions import TransactionsResponse
from ynab_http_mcp.utils.schema_utils import clean_ynab_data
from ynab_http_mcp.utils.schema_utils import simple_validate
from uuid import UUID
from typing import Annotated, Literal
import json


def register(mcp, ynab_service: YnabService):

    @mcp.resource(uri="data://accounts", mime_type="application/json")
    async def get_accounts() -> str:
        """Get a list of all YNAB accounts."""
        # Get raw YNAB response
        raw_response = ynab_service.get_accounts()
        cleaned_response = MCPAccounts.from_ynab(raw_response)

        return cleaned_response.model_dump_json()

    @mcp.resource(uri="data://accounts/{account_id}", mime_type="application/json")
    async def get_account(account_id: str) -> str:
        """Get a single YNAB account using its ID"""
        raw_response = ynab_service.get_account(UUID(account_id))
        cleaned_response = MCPAccount.from_ynab(raw_response)
        return cleaned_response.model_dump_json()
    
    
