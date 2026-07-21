# All transaction actions.
from ynab_http_mcp.ynab_service import YnabService
from typing import Annotated, Literal
from ynab_http_mcp.schemas.transactions import (
    TransactionsResponse,
    TransactionResponse,
)
import json


def register(mcp, ynab_service: YnabService):

    @mcp.resource(
        uri="data://transactions{?since_date,until_date,type,limit}",
        mime_type="application/json",
    )
    async def get_transactions_resource(
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
        limit: Annotated[
            int | None,
            "Maximum number of transactions to return. Leave blank for no limit.",
        ] = None
    ) -> str:
        """
        Get transactions with flexible filtering options as a resource.

        Filtering is specified via filter_params in the format:
        since_date=YYYY-MM-DD&until_date=YYYY-MM-DD&type=cleared&account_id=XXX

        Examples:
        - data://transactions/since_date=2024-01-01&until_date=2024-01-31
        - data://transactions/type=cleared&account_id=XYZ
        """
        # Parse filter parameters from the path

        # Get raw YNAB response - validation is now handled by the service method
        try:
            raw_response = ynab_service.get_transactions(
                since_date=since_date,
                until_date=until_date,
                type=type if type else "all"
            )
        except ValueError as e:
            error_response = {"error": f"Invalid parameter format: {str(e)}"}
            return json.dumps(error_response)

        validated_response = TransactionsResponse.from_ynab_response(raw_response)
        # Return as JSON string for MCP resource compatibility
        return validated_response.model_dump_json()

    @mcp.resource(uri="data://transactions/{id}", mime_type="application/json")
    async def get_single_transaction_resource(
        id: Annotated[
            str,
            "UUID of the transaction to retrieve.",
        ],
    ) -> str:
        """
        Get a single transaction by its UUID

        Example:
        - data://transactions/fd6bb67d-b77f-4dee-a2f5-47ef2bd8613c
        """
        # Parse filter parameters from the path

        # Get raw YNAB response
        raw_response = ynab_service.get_transaction(id)

        validated_response = TransactionResponse.from_ynab_response(raw_response)

        # Return as JSON string for MCP resource compatibility
        return validated_response.model_dump_json()
