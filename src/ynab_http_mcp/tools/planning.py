# All transaction, planning actions.
from ynab_http_mcp.ynab_service import YnabService
from typing import Any, Annotated
from datetime import datetime
from ynab_http_mcp.debug import debug_exception, debug_string


def register(mcp, ynab_service: YnabService):
    @mcp.tool()
    async def get_plan_month(
        month_date: Annotated[
            str | None,
            "ISO-format date within the month of choice. For instance, '2023-12-11' targets December 2023. Leave blank to select current month",
        ] = None,
    ) -> dict[str, Any]:
        """Get a list of category groups and their categories."""
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

        return ynab_service.get_plan_month(date=converted_month_date).to_dict()
