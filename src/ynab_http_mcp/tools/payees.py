# All transaction actions.
from ynab_http_mcp.ynab_service import YnabService
from typing import Annotated, Literal
from ynab_http_mcp.schemas.payees import PayeesResponse, PayeeResponse
from ynab_http_mcp.schemas.transactions import TransactionsResponse
import json


def register(mcp, ynab_service: YnabService):

    @mcp.resource(uri="data://payees", mime_type="application/json")
    async def get_payees() -> str:
        """
        Get a list of all payees.
        """
        # Get raw YNAB response
        raw_response = ynab_service.get_payees()

        validated_response = PayeesResponse.from_ynab_response(raw_response)
        # Return as JSON string for MCP resource compatibility
        return validated_response.model_dump_json()

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
        # Parse filter parameters from the path

        # Get raw YNAB response
        raw_response = ynab_service.get_payee(id)

        validated_response = PayeeResponse.from_ynab_response(raw_response)

        # Return as JSON string for MCP resource compatibility
        return validated_response.model_dump_json()

    @mcp.resource(
        uri="data://payees/{payee_id}/transactions{?since_date,until_date,type}",
        mime_type="application/json",
    )
    async def get_transactions_by_payee(
        payee_id: Annotated[
            str,
            "Payee ID to filter transactions by specific payee.",
        ],
        since_date: Annotated[
            str | None,
            "ISO-format date (YYYY-MM-DD) to filter transactions starting from this date. Leave blank for no start date filter.",
        ] = None,
        until_date: Annotated[
            str | None,
            "ISO-format date (YYYY-MM-DD) to filter transactions up to this date. Leave blank for no end date filter.",
        ] = None,
        type: Annotated[
            Literal["all", "uncleared", "cleared", "reconciled"] | None,
            "Transaction type filter. Must be one of: 'all', 'uncleared', 'cleared', 'reconciled'.",
        ] = "all",
    ) -> str:
        """
        Get transactions related a specific payee.

        Filtering is specified via filter_params in the format:
        since_date=YYYY-MM-DD&until_date=YYYY-MM-DD&type=cleared

        Examples:
        - data://payees/2211a810-42bf-435d-974b-35fc8cdfdf8a/transactions/since_date=2024-01-01&until_date=2024-01-31
        """
        # Parse filter parameters from the path

        # Get raw YNAB response - validation is now handled by the service method
        try:
            raw_response = ynab_service.get_transactions(
                since_date=since_date,
                until_date=until_date,
                type=type if type else "all",
                payee_id=payee_id,
            )
        except ValueError as e:
            error_response = {"error": f"Invalid parameter format: {str(e)}"}
            return json.dumps(error_response)

        validated_response = TransactionsResponse.from_ynab_response(raw_response)
        # Return as JSON string for MCP resource compatibility
        return validated_response.model_dump_json()
