from ynab_http_mcp.ynab_service import YnabService
from typing import Annotated
from ynab_http_mcp.schemas.payees import (
    MCPPayees,
    MCPPayee,
    MCPPayeeFull,
)
from ynab_http_mcp.debug import debug_exception

def register(mcp, ynab_service: YnabService):

    # @mcp.resource(uri="data://payees", mime_type="application/json")
    # async def get_payees() -> str:
    #     """Get a list of all payees."""
    #     raw_response = ynab_service.get_payees()
    #     validated_response = MCPPayees.from_ynab_response(raw_response)
    #     return validated_response.model_dump_json(exclude_none=True)

    @mcp.tool(annotations={"readOnlyHint": True})
    def search_payees(
        query: Annotated[str, "Partial or full payee name to search for (case-insensitive)."],
        limit: Annotated[int, "Max results to return. Defaults to 10."] = 10,
    ) -> str:
        """Search for payees by name. Returns matching payees ranked by closeness
        of match. Use this to resolve a payee name to a UUID before calling
        get_transactions_by_payee. Does not match deleted payees."""
        raw_response = ynab_service.get_payees()
        query_lower = query.lower()
        matches = [
            p for p in raw_response.data.payees
            if not p.deleted and query_lower in p.name.lower()
        ]
        # Rank: exact match first, then startswith, then contains
        matches.sort(key=lambda p: (
            0 if p.name.lower() == query_lower else
            1 if p.name.lower().startswith(query_lower) else 2
        ))
        validated = [MCPPayee.from_ynab(p) for p in matches[:limit]]
        return MCPPayees(payees=validated).model_dump_json(exclude_none=True)

    @mcp.resource(uri="data://payees/{id}", mime_type="application/json")
    async def get_single_payee(
        id: Annotated[
            str,
            "UUID of the payee to retrieve.",
        ],
    ) -> str:
        """Get a single payee by its UUID."""
        raw_response = ynab_service.get_payee(id)
        try:
            cleaned = MCPPayee.from_ynab(raw_response.data.payee)
        except Exception:
            debug_exception(
                f"Failed to validate payee {getattr(raw_response.data.payee, 'id', 'unknown')}"
            )
            cleaned = MCPPayee(id="", name="", deleted=False, transfer_account_id=None)
        return cleaned.model_dump_json(exclude_none=True)
