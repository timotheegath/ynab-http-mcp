# All planning actions.
import logging
from fastmcp.exceptions import ResourceError
from ynab_http_mcp.ynab_service import YnabService, PlanMonthNotFoundError
from typing import Annotated
from ynab_http_mcp.schemas.planning import (
    PlanMonthResponse,
    AllPlanMonthsResponse,
)
from ynab_http_mcp.schemas.categories import MCPCategory


def _no_plan_error(month: str) -> ResourceError:
    """Build the client-facing error for a month that has no plan yet.

    Logged at INFO, not ERROR: querying beyond the plan's horizon is an
    expected condition, not a server fault.
    """
    return ResourceError(
        f"No plan exists for month {month} — it is beyond the plan's horizon.",
        log_level=logging.INFO,
    )


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
            "ISO date YYYY-MM-DD or YYYY-MM. Day is ignored.",
        ],
    ) -> str:
        """Get the plan for a specific month with formatted budget/activity/balance per category."""
        try:
            raw_response = ynab_service.get_plan_month(date=month_date)
        except PlanMonthNotFoundError as e:
            raise _no_plan_error(e.month) from e
        validated_response = PlanMonthResponse.from_ynab_response(raw_response)
        return validated_response.model_dump_json(exclude_none=True)

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
        raw_response = ynab_service.get_all_plan_months()
        validated_response = AllPlanMonthsResponse.from_ynab_response(raw_response)
        return validated_response.model_dump_json(exclude_none=True)

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
            "ISO date YYYY-MM-DD or YYYY-MM. Day is ignored.",
        ],
        category_id: Annotated[
            str,
            "ID of the category to retrieve",
        ],
    ) -> str:
        """Get a specific category's data for a given month."""
        try:
            raw_response = ynab_service.get_month_category(
                month_date=month_date, category_id=category_id
            )
        except PlanMonthNotFoundError as e:
            raise _no_plan_error(e.month) from e
        cleaned_response = MCPCategory.from_ynab(raw_response)
        return cleaned_response.model_dump_json(exclude_none=True)
