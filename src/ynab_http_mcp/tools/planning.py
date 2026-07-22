# All planning actions.
from ynab_http_mcp.ynab_service import YnabService
from typing import Annotated
from ynab_http_mcp.schemas.planning import PlanMonthResponse, AllPlanMonthsResponse


def register(mcp, ynab_service: YnabService):
    @mcp.resource(
        uri="data://months/{month_date}",
        mime_type="application/json",
        annotations={
            "title": "Get the plan for a specific month.",
            "destructiveHint": False,
            "readOnlyHint": True,
            "idempotentHint": True,
        },
    )
    async def get_plan_month(
        month_date: Annotated[
            str,
            "ISO-format date within the month of choice. Accepts 'YYYY-MM-DD' or 'YYYY-MM' format. For instance, '2023-12-11' or '2023-12' both target December 2023.",
        ],
    ) -> str:
        """Get the details of a particular plan month, the money assigned to each category in that month.

        Accepts month_date in 'YYYY-MM-DD' or 'YYYY-MM' format. Day is ignored.
        """
        # Get raw YNAB response - validation is now handled by the service method
        raw_response = ynab_service.get_plan_month(date=month_date)

        # Transform and validate with schema
        validated_response = PlanMonthResponse.from_ynab_response(raw_response)

        # Return as JSON string for MCP resource compatibility
        return validated_response.model_dump_json()

    @mcp.resource(
        uri="data://months",
        mime_type="application/json",
        annotations={
            "title": "Get a summary of the plan across all months.",
            "destructiveHint": False,
            "readOnlyHint": True,
            "idempotentHint": True,
        },
    )
    async def get_all_plan_months() -> str:
        """Get a summarised list of all months in the plan."""
        # Get raw YNAB response
        raw_response = ynab_service.get_all_plan_months()

        # Transform and validate with schema
        validated_response = AllPlanMonthsResponse.from_ynab_response(raw_response)

        # Return as JSON string for MCP resource compatibility
        return validated_response.model_dump_json()

    @mcp.resource(
        uri="data://months/{month_date}/categories/{category_id}",
        mime_type="application/json",
        annotations={
            "title": "Get a specific category's data for a given month.",
            "destructiveHint": False,
            "readOnlyHint": True,
            "idempotentHint": True,
        },
    )
    async def get_month_category_by_id(
        month_date: Annotated[
            str,
            "ISO-format date within the month of choice. Accepts 'YYYY-MM-DD' or 'YYYY-MM' format. For instance, '2023-12-11' or '2023-12' both target December 2023.",
        ],
        category_id: Annotated[
            str,
            "ID of the category to retrieve",
        ],
    ) -> str:
        """Get a specific category's data for a given month.

        Accepts month_date in 'YYYY-MM-DD' or 'YYYY-MM' format. Day is ignored.
        """
        # Get raw YNAB response using the new service method
        # Validation is now handled by the service method
        raw_response = ynab_service.get_month_category(
            month_date=month_date, category_id=category_id
        )

        # Transform and validate with schema
        # We'll reuse the existing CategoryResponse schema for now
        from ynab_http_mcp.schemas.categories import CategoryResponse

        validated_response = CategoryResponse.from_ynab_response(raw_response)

        # Return as JSON string for MCP resource compatibility
        return validated_response.model_dump_json()
