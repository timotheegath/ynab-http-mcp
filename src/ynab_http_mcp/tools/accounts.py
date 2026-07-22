from ynab_http_mcp.ynab_service import YnabService
from ynab_http_mcp.schemas.accounts import MCPAccounts, MCPAccount, MCPAccountFull
from uuid import UUID


def register(mcp, ynab_service: YnabService):

    @mcp.resource(uri="data://accounts", mime_type="application/json")
    async def get_accounts() -> str:
        """Get a list of all YNAB accounts."""
        # Get raw YNAB response
        raw_response = ynab_service.get_accounts()
        cleaned_response = MCPAccounts.from_ynab(raw_response)

        return cleaned_response.model_dump_json(exclude_none=True)

    @mcp.resource(uri="data://accounts/{account_id}", mime_type="application/json")
    async def get_account(account_id: str) -> str:
        """Get a single YNAB account using its ID"""
        raw_response = ynab_service.get_account(UUID(account_id))
        cleaned_response = MCPAccount.from_ynab(raw_response)
        return cleaned_response.model_dump_json(exclude_none=True)

    @mcp.resource(uri="data://accounts/{account_id}/full", mime_type="application/json")
    async def get_account_full(account_id: str) -> str:
        """Get a single YNAB account using its ID, including the cleaned raw
        YNAB SDK payload under ``full_details``.

        The Lean endpoint (``data://accounts/{account_id}``) returns only the
        LLM-friendly formatted fields. This drill-in endpoint adds a single
        ``full_details`` dict carrying every field the YNAB SDK exposes for
        the account, including fields the Lean layer dropped (``note``,
        integer milliunit balance, ``interest_rate``, ``available_balance``,
        ``debt_escrow_amounts``, etc.). Use this when arithmetic or
        SDK-fidelity access is required.
        """
        raw_response = ynab_service.get_account(UUID(account_id))
        cleaned_response = MCPAccountFull.from_ynab(raw_response)
        return cleaned_response.model_dump_json(exclude_none=True)
