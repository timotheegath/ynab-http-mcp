# All planning actions.
from ynab_http_mcp.ynab_service import YnabService
from typing import Annotated
from datetime import datetime
from ynab_http_mcp.debug import debug_exception
from ynab_http_mcp.schemas.planning import (
    PlanMonthResponse,
    AllPlanMonthsResponse,
    PlanMonthSummary,
)
from ynab_http_mcp.utils.schema_utils import simple_validate


def register(mcp, ynab_service: YnabService):
    @mcp.tool(
        annotations={
            "title": "Get the plan for a specific month.",
            "destructiveHint": False,
            "readOnlyHint": True,
            "idempotentHint": True,
        }
    )
    async def get_plan_month(
        month_date: Annotated[
            str | None,
            "ISO-format date within the month of choice. For instance, '2023-12-11' targets December 2023. Leave blank to select current month",
        ] = None,
    ) -> str:
        """Get the details of a particular plan month, the money assigned to each category in that month."""
        if month_date:
            try:
                converted_month_date = datetime.fromisoformat(month_date)
            except Exception as e:
                debug_exception(str(e))
                raise RuntimeError(
                    f"Failed to convert input date to datetime: {e}"
                ) from e
        else:
            converted_month_date = None

        # Get raw YNAB response
        raw_response = ynab_service.get_plan_month(date=converted_month_date)

        # Transform and validate with schema
        validated_response = PlanMonthResponse.from_ynab_response(raw_response)

        # Return as JSON string for MCP resource compatibility
        return validated_response.model_dump_json()

    @mcp.tool(
        annotations={
            "title": "Get a summary of the plan across all months.",
            "destructiveHint": False,
            "readOnlyHint": True,
            "idempotentHint": True,
        }
    )
    async def get_all_plan_months() -> str:
        """Get a summarised list of all months in the plan."""
        # Get raw YNAB response
        raw_response = ynab_service.get_all_plan_months()

        # Transform and validate with schema
        validated_response = AllPlanMonthsResponse.from_ynab_response(raw_response)

        # Return as JSON string for MCP resource compatibility
        return validated_response.model_dump_json()
