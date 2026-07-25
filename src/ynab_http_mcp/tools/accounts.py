from ynab_http_mcp.ynab_service import YnabService
from ynab_http_mcp.schemas.accounts import MCPAccounts, MCPAccount, MCPAccountFull
from uuid import UUID


def register(mcp, ynab_service: YnabService):

    @mcp.resource(uri="data://accounts", mime_type="application/json")
    async def get_accounts() -> str:
        """Get a list of all YNAB accounts."""
        raw_response = ynab_service.get_accounts()
        cleaned_response = MCPAccounts.from_ynab(raw_response)
        return cleaned_response.model_dump_json(exclude_none=True)

    @mcp.resource(uri="data://accounts/{account_id}", mime_type="application/json")
    async def get_account(account_id: str) -> str:
        """Get a single YNAB account using its ID."""
        raw_response = ynab_service.get_account(UUID(account_id))
        cleaned_response = MCPAccount.from_ynab(raw_response)
        return cleaned_response.model_dump_json(exclude_none=True)

    @mcp.resource(uri="data://accounts/{account_id}/full", mime_type="application/json")
    async def get_account_full(account_id: str) -> str:
        """Get an account with full_details for raw SDK fields (note, integer
        milliunit balance, interest_rate). Use when arithmetic or SDK-fidelity
        access is required beyond the lean endpoint."""
        raw_response = ynab_service.get_account(UUID(account_id))
        cleaned_response = MCPAccountFull.from_ynab(raw_response)
        return cleaned_response.model_dump_json(exclude_none=True)
