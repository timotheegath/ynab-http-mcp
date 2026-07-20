# All transaction actions.
from ynab_http_mcp.ynab_service import YnabService
from typing import Annotated
from ynab_http_mcp.schemas.payees import PayeesResponse, PayeeResponse


def register(mcp, ynab_service: YnabService):

    @mcp.resource(uri="data://payees", mime_type="application/json")
    async def get_payees_resource() -> str:
        """
        Get a list of all payees.
        """
        # Get raw YNAB response
        raw_response = ynab_service.get_payees()

        validated_response = PayeesResponse.from_ynab_response(raw_response)
        # Return as JSON string for MCP resource compatibility
        return validated_response.model_dump_json()

    @mcp.resource(uri="data://payees/{id}", mime_type="application/json")
    async def get_single_payee_resource(
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
        # Parse filter parameters from the path

        # Get raw YNAB response
        raw_response = ynab_service.get_payee(id)

        validated_response = PayeeResponse.from_ynab_response(raw_response)

        # Return as JSON string for MCP resource compatibility
        return validated_response.model_dump_json()
