from ynab_http_mcp.ynab_service import YnabService
from typing import Any


def register(mcp, ynab_service: YnabService):
    @mcp.tool(
            annotations={
                "title":"Get all categories and their groups.",
                "destructiveHint":False,
                "readOnlyHint": True,
                "idempotentHint":True
            }
    )
    async def get_categories() -> dict[str, Any]:
        """Get a list of category groups and their categories."""
        return ynab_service.get_categories().to_dict()
