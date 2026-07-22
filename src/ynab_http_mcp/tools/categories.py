from ynab_http_mcp.ynab_service import YnabService
from ynab_http_mcp.schemas.categories import CategoriesResponse, CategoryResponse
from ynab_http_mcp.schemas.transactions import MCPTransactions
from typing import Literal, Annotated
import json


def register(mcp, ynab_service: YnabService):
    @mcp.resource(uri="data://categories", mime_type="application/json")
    async def get_categories() -> str:
        """Get a list of category groups and their categories."""
        # Get raw YNAB response
        raw_response = ynab_service.get_categories()

        # Transform and validate with schema
        validated_response = CategoriesResponse.from_ynab_response(raw_response)

        # Return as JSON string for MCP resource compatibility
        return validated_response.model_dump_json()

    @mcp.resource(uri="data://categories/{category_id}", mime_type="application/json")
    async def get_category(category_id: Annotated[str, "ID of the category"]) -> str:
        """Get a specific category"""
        # Get raw YNAB response
        raw_response = ynab_service.get_category(category_id)

        # Transform and validate with schema
        validated_response = CategoryResponse.from_ynab_response(raw_response)

        # Return as JSON string for MCP resource compatibility
        return validated_response.model_dump_json()

  