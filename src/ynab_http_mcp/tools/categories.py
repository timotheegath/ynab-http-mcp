from ynab_http_mcp.ynab_service import YnabService
from typing import Any
from ynab_http_mcp.schemas.categories import CategoriesResponse, CategoryGroup, CleanCategory
from ynab_http_mcp.schemas.base import validate_and_clean_data

import os


def register(mcp, ynab_service: YnabService):
    @mcp.tool(
        annotations={
            "title": "Get all categories and their groups.",
            "destructiveHint": False,
            "readOnlyHint": True,
            "idempotentHint": True,        }
    )
    async def get_categories() -> CategoriesResponse:
        """Get a list of category groups and their categories."""
        # Get raw YNAB response
        raw_response = ynab_service.get_categories()
        
        # Convert to dict
        raw_data = raw_response.to_dict()
        
        # Clean and validate category groups and categories
        cleaned_category_groups = []
        
        for group_data in raw_data.get('data', {}).get('category_groups', []):
            # Clean categories within the group
            cleaned_categories = []
            for category_data in group_data.get('categories', []):
                try:
                    cleaned_category = validate_and_clean_data(
                        CleanCategory,
                        category_data,
                        debug_mode=os.getenv('DEBUG_MODE', 'false').lower() in ('true', '1', 'yes')
                    )
                    cleaned_categories.append(cleaned_category.model_dump())
                except Exception as e:
                    from ynab_http_mcp.debug import debug_exception
                    debug_exception(f"Failed to validate category {category_data.get('id', 'unknown')}")
                    continue
            
            # Create cleaned category group
            cleaned_group_data = {
                **group_data,
                'categories': cleaned_categories
            }
            
            try:
                cleaned_group = validate_and_clean_data(
                    CategoryGroup,
                    cleaned_group_data,
                    debug_mode=os.getenv('DEBUG_MODE', 'false').lower() in ('true', '1', 'yes')
                )
                cleaned_category_groups.append(cleaned_group.model_dump())
            except Exception as e:
                from ynab_http_mcp.debug import debug_exception
                debug_exception(f"Failed to validate category group {group_data.get('id', 'unknown')}")
                continue
        
        # Create final response
        final_response = {
            'category_groups': cleaned_category_groups
        }
        
        # Validate complete response structure
        validated_response = validate_and_clean_data(
            CategoriesResponse,
            final_response,
            debug_mode=os.getenv('DEBUG_MODE', 'false').lower() in ('true', '1', 'yes')
        )
        
        return validated_response
    