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
from ynab_http_mcp.utils.simple_validation import simple_validate


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
    ) -> PlanMonthResponse:
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

        # Get raw response and validate with schema
        raw_response = ynab_service.get_plan_month(date=converted_month_date)
        raw_data = raw_response.to_dict()

        # Extract the month data from the YNAB response structure
        # YNAB API returns {'data': {'month': {...}}} but our schema expects {'month': {...}}
        month_data = raw_data.get("data", {}).get("month", {})

        # Transform YNAB data to match our schema
        transformed_data = PlanMonthResponse.from_ynab_data({"month": month_data})

        # Validate using simplified approach
        validated_response = simple_validate(
            transformed_data.model_dump(), PlanMonthResponse
        )

        return validated_response

    @mcp.tool(
        annotations={
            "title": "Get a summary of the plan across all months.",
            "destructiveHint": False,
            "readOnlyHint": True,
            "idempotentHint": True,
        }
    )
    async def get_all_plan_months() -> AllPlanMonthsResponse:
        """Get a summarised list of all months in the plan."""
        # Get raw response and validate with schema
        raw_response = ynab_service.get_all_plan_months()
        raw_data = raw_response.to_dict()

        # Extract the months data from the YNAB response structure
        # YNAB API returns {'data': {'months': [...]}} but our schema expects {'months': [...]}
        months_data = raw_data.get("data", {}).get("months", [])

        # Transform YNAB data to match our schema
        transformed_months = []
        for month_data in months_data:
            transformed_month = PlanMonthSummary.from_ynab_data(month_data)
            transformed_months.append(transformed_month.model_dump())

        # Validate using simplified approach
        validated_response = simple_validate(
            {"months": transformed_months}, AllPlanMonthsResponse
        )

        return validated_response
