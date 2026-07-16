# All planning actions.
from ynab_http_mcp.ynab_service import YnabService
from typing import Any, Annotated
from datetime import datetime
from ynab_http_mcp.debug import debug_exception, debug_string
from ynab_http_mcp.schemas.planning import PlanMonthResponse, AllPlanMonthsResponse
from ynab_http_mcp.schemas.base import validate_and_clean_data
from ynab_http_mcp.utils.schema_utils import transform_schema
import os


def register(mcp, ynab_service: YnabService):
    @mcp.tool(
        annotations={
            "title": "Get the plan for a specific month.",
            "destructiveHint": False,
            "readOnlyHint": True,
            "idempotentHint": True,
            "returnSchema": transform_schema(PlanMonthResponse.model_json_schema()),
        }
    )
    async def get_plan_month(
        month_date: Annotated[
            str | None,
            "ISO-format date within the month of choice. For instance, '2023-12-11' targets December 2023. Leave blank to select current month",
        ] = None,
    ) -> dict[str, Any]:
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
        
        # Validate and clean with schema
        validated_response = validate_and_clean_data(
            PlanMonthResponse,
            raw_data,
            debug_mode=os.getenv('DEBUG_MODE', 'false').lower() in ('true', '1', 'yes')
        )
        
        return validated_response.model_dump()

    @mcp.tool(
        annotations={
            "title": "Get a summary of the plan across all months.",
            "destructiveHint": False,
            "readOnlyHint": True,
            "idempotentHint": True,
            "returnSchema": transform_schema(AllPlanMonthsResponse.model_json_schema()),
        }
    )
    async def get_all_plan_months() -> dict[str, Any]:
        """Get a summarised list of all months in the plan."""
        # Get raw response and validate with schema
        raw_response = ynab_service.get_all_plan_months()
        raw_data = raw_response.to_dict()
        
        # Validate and clean with schema
        validated_response = validate_and_clean_data(
            AllPlanMonthsResponse,
            raw_data,
            debug_mode=os.getenv('DEBUG_MODE', 'false').lower() in ('true', '1', 'yes')
        )
        
        return validated_response.model_dump()
