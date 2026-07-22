from ynab_http_mcp.ynab_service import YnabService
from ynab_http_mcp.schemas.categories import MCPCategories, MCPCategory, MCPCategoryFull
from uuid import UUID


def register(mcp, ynab_service: YnabService):

    @mcp.resource(uri="data://categories", mime_type="application/json")
    async def get_categories() -> str:
        """Get a flat list of all YNAB categories."""
        raw_response = ynab_service.get_categories()
        cleaned_response = MCPCategories.from_ynab(raw_response)

        return cleaned_response.model_dump_json(exclude_none=True)

    @mcp.resource(uri="data://categories/{category_id}", mime_type="application/json")
    async def get_category(category_id: str) -> str:
        """Get a single YNAB category using its ID"""
        raw_response = ynab_service.get_category(UUID(category_id))
        cleaned_response = MCPCategory.from_ynab(raw_response)
        return cleaned_response.model_dump_json(exclude_none=True)

    @mcp.resource(
        uri="data://categories/{category_id}/full", mime_type="application/json"
    )
    async def get_category_full(category_id: str) -> str:
        """Get a single YNAB category using its ID, including the cleaned raw
        YNAB SDK payload under ``full_details``.

        The Lean endpoint (``data://categories/{category_id}``) returns only
        the 9 LLM-friendly fields plus a 5-field lean goal. This drill-in
        endpoint adds a single ``full_details`` dict carrying every field the
        YNAB SDK exposes for the category, including fields the Lean layer
        dropped (``note``, integer milliunit budget/activity/balance, the
        full goal raw field set, etc.). Use this when arithmetic or
        SDK-fidelity access is required.
        """
        raw_response = ynab_service.get_category(UUID(category_id))
        cleaned_response = MCPCategoryFull.from_ynab(raw_response)
        return cleaned_response.model_dump_json(exclude_none=True)
