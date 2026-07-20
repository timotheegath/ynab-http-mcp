from ynab_http_mcp.ynab_service import YnabService
from ynab_http_mcp.schemas.categories import (
    CategoriesResponse,
    CategoryGroup,
    CleanCategory,
)
from ynab_http_mcp.schemas.transactions import TransactionsResponse
from ynab_http_mcp.utils.schema_utils import clean_ynab_data
from ynab_http_mcp.utils.simple_validation import simple_validate
from typing import Literal, Annotated
import json
from datetime import datetime


def register(mcp, ynab_service: YnabService):
    @mcp.resource(uri="data://categories", mime_type="application/json")
    async def get_categories() -> str:
        """Get a list of category groups and their categories."""
        # Get raw YNAB response
        raw_response = ynab_service.get_categories()

        # Convert to dict
        raw_data = raw_response.to_dict()

        # Clean and validate category groups and categories using simplified approach
        cleaned_category_groups = []

        for group_data in raw_data.get("data", {}).get("category_groups", []):
            # Clean categories within the group using unified cleaning
            cleaned_categories = []
            for category_data in group_data.get("categories", []):
                try:
                    # Clean data using unified function
                    cleaned_data = clean_ynab_data(category_data)

                    # Validate using simplified approach
                    validated_category = simple_validate(cleaned_data, CleanCategory)
                    cleaned_categories.append(validated_category.model_dump())
                except Exception:
                    from ynab_http_mcp.debug import debug_exception

                    debug_exception(
                        f"Failed to validate category {category_data.get('id', 'unknown')}"
                    )
                    continue

            # Clean group data using unified cleaning
            cleaned_group_data = clean_ynab_data(group_data)
            cleaned_group_data["categories"] = cleaned_categories

            try:
                cleaned_group = simple_validate(cleaned_group_data, CategoryGroup)
                cleaned_category_groups.append(cleaned_group.model_dump())
            except Exception:
                from ynab_http_mcp.debug import debug_exception

                debug_exception(
                    f"Failed to validate category group {group_data.get('id', 'unknown')}"
                )
                continue

        # Create final response
        final_response = {"category_groups": cleaned_category_groups}

        # Validate complete response structure using simplified approach
        try:
            validated_response = simple_validate(final_response, CategoriesResponse)
            # Return as JSON string for MCP resource compatibility
            return json.dumps(validated_response.model_dump())
        except Exception:
            from ynab_http_mcp.debug import debug_exception

            debug_exception("Failed to validate final categories response")
            # Return a fallback response if validation fails
            # Convert dicts back to CategoryGroup objects for type safety
            fallback_groups = []
            for group_dict in cleaned_category_groups:
                try:
                    # Convert categories back to CleanCategory objects
                    categories = []
                    for cat_dict in group_dict.get("categories", []):
                        categories.append(CleanCategory(**cat_dict))

                    # Create CategoryGroup object
                    group_obj = CategoryGroup(
                        id=group_dict["id"],
                        name=group_dict["name"],
                        hidden=group_dict.get("hidden", False),
                        deleted=group_dict.get("deleted", False),
                        categories=categories,
                    )
                    fallback_groups.append(group_obj)
                except Exception:
                    # If conversion fails, skip this group
                    continue

            fallback_response = CategoriesResponse(category_groups=fallback_groups)
            return json.dumps(fallback_response.model_dump())

    @mcp.resource(
        uri="data://categories/{category_id}/transactions{?since_date,until_date,type}",
        mime_type="application/json",
    )
    async def get_transactions_by_account_resource(
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

        # Implement mandatory filter validation
        if not any([since_date, until_date, type and type != "all"]):
            error_response = {
                "error": "At least one of 'since_date', 'until_date', or 'type' (non-'all') filters must be provided"
            }

        # Convert string parameters to appropriate types with error handling
        try:
            converted_since_date = (
                datetime.fromisoformat(since_date) if since_date else None
            )
            converted_until_date = (
                datetime.fromisoformat(until_date) if until_date else None
            )
        except ValueError as e:
            error_response = {"error": f"Invalid parameter format: {str(e)}"}
            return json.dumps(error_response)

        # Get raw YNAB response
        raw_response = ynab_service.get_transactions(
            since_date=converted_since_date,
            until_date=converted_until_date,
            type=type if type else "all",
            category_id=category_id,
        )

        validated_response = TransactionsResponse.from_ynab_response(raw_response)
        # Return as JSON string for MCP resource compatibility
        return validated_response.model_dump_json()
