from ynab_http_mcp.ynab_service import YnabService
from ynab_http_mcp.schemas.categories import CategoriesResponse, CategoryResponse
from ynab_http_mcp.schemas.transactions import TransactionsResponse
from typing import Literal, Annotated
import json


def register(mcp, ynab_service: YnabService):
    @mcp.resource(uri="data://categories", mime_type="application/json")
    async def get_categories() -> str:
        """Get a list of category groups and their categories."""
        # Get raw YNAB response
        raw_response = ynab_service.get_categories()

        # Transform and validate with schema
        validated_response = CategoriesResponse.from_ynab_response(raw_response)

        # Return as JSON string for MCP resource compatibility
        return validated_response.model_dump_json()

    @mcp.resource(uri="data://categories/{category_id}", mime_type="application/json")
    async def get_category(category_id: Annotated[str, "ID of the category"]) -> str:
        """Get a specific category"""
        # Get raw YNAB response
        raw_response = ynab_service.get_category(category_id)

        # Transform and validate with schema
        validated_response = CategoryResponse.from_ynab_response(raw_response)

        # Return as JSON string for MCP resource compatibility
        return validated_response.model_dump_json()

    @mcp.resource(
        uri="data://categories/{category_id}/transactions{?since_date,until_date,type}",
        mime_type="application/json",
    )
    async def get_transactions_by_category(
        category_id: Annotated[
            str,
            "Category ID to filter transactions by specific category.",
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
        Get transactions related a specific category.

        Filtering is specified via filter_params in the format:
        since_date=YYYY-MM-DD&until_date=YYYY-MM-DD&type=cleared

        Examples:
        - data://category/f7ab4ff3-99c3-44db-b060-2c2df8d9384b/transactions/since_date=2024-01-01&until_date=2024-01-31
        """
        # Parse filter parameters from the path

        # Get raw YNAB response - validation is now handled by the service method
        try:
            raw_response = ynab_service.get_transactions(
                since_date=since_date,
                until_date=until_date,
                type=type if type else "all",
                category_id=category_id,
            )
        except ValueError as e:
            error_response = {"error": f"Invalid parameter format: {str(e)}"}
            return json.dumps(error_response)

        validated_response = TransactionsResponse.from_ynab_response(raw_response)
        # Return as JSON string for MCP resource compatibility
        return validated_response.model_dump_json()
