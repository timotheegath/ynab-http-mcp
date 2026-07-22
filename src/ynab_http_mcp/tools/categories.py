from ynab_http_mcp.ynab_service import YnabService
from ynab_http_mcp.schemas.categories import MCPCategories, MCPCategory
from uuid import UUID


def register(mcp, ynab_service: YnabService):

    @mcp.resource(uri="data://categories", mime_type="application/json")
    async def get_categories() -> str:
        """Get a flat list of all YNAB categories."""
        raw_response = ynab_service.get_categories()
        cleaned_response = MCPCategories.from_ynab(raw_response)

        return cleaned_response.model_dump_json()

    @mcp.resource(uri="data://categories/{category_id}", mime_type="application/json")
    async def get_category(category_id: str) -> str:
        """Get a single YNAB category using its ID"""
        raw_response = ynab_service.get_category(UUID(category_id))
        cleaned_response = MCPCategory.from_ynab(raw_response)
        return cleaned_response.model_dump_json()
