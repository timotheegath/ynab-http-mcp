# All planning actions.
import ynab
from ynab_http_mcp.ynab_service import YnabService
from typing import Annotated
from ynab_http_mcp.schemas.planning import (
    PlanMonthResponse,
    AllPlanMonthsResponse,
    PlanMonthFull,
    PlanMonthFullResponse,
)
from ynab_http_mcp.schemas.categories import MCPCategory, MCPCategoryFull


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
        raw_response = ynab_service.get_plan_month(date=month_date)
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
        raw_response = ynab_service.get_month_category(
            month_date=month_date, category_id=category_id
        )
        cleaned_response = MCPCategory.from_ynab(raw_response)
        return cleaned_response.model_dump_json(exclude_none=True)

    @mcp.resource(
        uri="data://months/{month_date}/full",
        mime_type="application/json",
        annotations={
            "title": "Get the plan for a specific month, including the cleaned raw YNAB SDK payload under full_details.",
            "destructiveHint": False,
            "readOnlyHint": True,
            "idempotentHint": True,
        },
    )
    async def get_plan_month_full(
        month_date: Annotated[
            str,
            "ISO date YYYY-MM-DD or YYYY-MM.",
        ],
    ) -> str:
        """Get a plan month with full_details for integer milliunit
        budget/activity/balance and the full raw goal field set. Use when
        arithmetic or SDK-fidelity access is required beyond the lean endpoint."""
        raw_response = ynab_service.get_plan_month(date=month_date)
        plan_full = PlanMonthFull.from_ynab_response(raw_response)
        wrapped = PlanMonthFullResponse(month=plan_full)
        return wrapped.model_dump_json(exclude_none=True)

    @mcp.resource(
        uri="data://months/{month_date}/categories/{category_id}/full",
        mime_type="application/json",
        annotations={
            "title": "Get a specific category's data for a given month, including the cleaned raw YNAB SDK payload under full_details.",
            "destructiveHint": False,
            "readOnlyHint": True,
            "idempotentHint": True,
        },
    )
    async def get_month_category_full(
        month_date: Annotated[
            str,
            "ISO date YYYY-MM-DD or YYYY-MM.",
        ],
        category_id: Annotated[
            str,
            "ID of the category to retrieve",
        ],
    ) -> str:
        """Get a month category with full_details for raw SDK fields. Use when
        arithmetic or SDK-fidelity access is required beyond the lean endpoint."""
        raw_response = ynab_service.get_month_category(
            month_date=month_date, category_id=category_id
        )
        raw_cat = (
            raw_response.data.category
            if isinstance(raw_response, ynab.CategoryResponse)
            else raw_response
        )
        full = MCPCategoryFull.from_ynab(raw_cat)
        return full.model_dump_json(exclude_none=True)
