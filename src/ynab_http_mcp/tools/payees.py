from ynab_http_mcp.ynab_service import YnabService
from typing import Annotated
from ynab_http_mcp.schemas.payees import (
    MCPPayees,
    MCPPayee,
)
from ynab_http_mcp.tools._full import full_resource
from ynab_http_mcp.debug import debug_exception


def register(mcp, ynab_service: YnabService):

    @mcp.resource(uri="data://payees", mime_type="application/json")
    async def get_payees() -> str:
        """Get a list of all payees."""
        raw_response = ynab_service.get_payees()
        validated_response = MCPPayees.from_ynab_response(raw_response)
        return validated_response.model_dump_json(exclude_none=True)

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
