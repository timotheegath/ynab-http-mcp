from ynab_http_mcp.ynab_service import YnabService
from typing import Annotated
from ynab_http_mcp.schemas.payees import (
    MCPPayees,
    MCPPayee,
    MCPPayeeFull,
)
from ynab_http_mcp.debug import debug_exception


def register(mcp, ynab_service: YnabService):

    @mcp.resource(uri="data://payees", mime_type="application/json")
    async def get_payees() -> str:
        """
        Get a list of all payees.
        """
        # Get raw YNAB response
        raw_response = ynab_service.get_payees()

        validated_response = MCPPayees.from_ynab_response(raw_response)
        # Return as JSON string for MCP resource compatibility
        return validated_response.model_dump_json(exclude_none=True)

    @mcp.resource(uri="data://payees/{id}", mime_type="application/json")
    async def get_single_payee(
        id: Annotated[
            str,
            "UUID of the payee to retrieve.",
        ],
    ) -> str:
        """
        Get a single payee by its UUID

        Example:
        - data://payees/fd6bb67d-b77f-4dee-a2f5-47ef2bd8613c
        """
        raw_response = ynab_service.get_payee(id)
        try:
            cleaned = MCPPayee.from_ynab(raw_response.data.payee)
        except Exception:
            debug_exception(
                f"Failed to validate payee {getattr(raw_response.data.payee, 'id', 'unknown')}"
            )
            cleaned = MCPPayee(id="", name="", deleted=False, transfer_account_id=None)
        return cleaned.model_dump_json(exclude_none=True)

    @mcp.resource(uri="data://payees/{id}/full", mime_type="application/json")
    async def get_single_payee_full(
        id: Annotated[
            str,
            "UUID of the payee to retrieve.",
        ],
    ) -> str:
        """
        Get a single payee by its UUID, including the cleaned raw YNAB SDK
        payload under ``full_details``.

        The Lean endpoint (``data://payees/{id}``) returns the 4 LLM-friendly
        payee fields. This drill-in endpoint adds a single ``full_details``
        dict carrying every field the YNAB SDK exposes for the payee,
        including fields the Lean layer dropped. Use this when SDK-fidelity
        access is required.
        """
        raw_response = ynab_service.get_payee(id)
        try:
            cleaned = MCPPayeeFull.from_ynab(raw_response.data.payee)
        except Exception:
            debug_exception(
                f"Failed to validate payee (full) {getattr(raw_response.data.payee, 'id', 'unknown')}"
            )
            cleaned = MCPPayeeFull(
                id="",
                name="",
                deleted=False,
                transfer_account_id=None,
                full_details={},
            )
        return cleaned.model_dump_json(exclude_none=True)
