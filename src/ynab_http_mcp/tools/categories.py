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
                    # Convert UUID objects to strings if needed
                    if 'id' in category_data and hasattr(category_data['id'], 'hex'):
                        category_data['id'] = str(category_data['id'])
                    if 'category_group_id' in category_data and hasattr(category_data['category_group_id'], 'hex'):
                        category_data['category_group_id'] = str(category_data['category_group_id'])
                    
                    # Only include fields that are in the CleanCategory model
                    clean_category_data = {
                        'id': category_data.get('id'),
                        'category_group_id': category_data.get('category_group_id'),
                        'name': category_data.get('name'),
                        'hidden': category_data.get('hidden', False),
                        'deleted': category_data.get('deleted', False),
                        'original_category_group_id': category_data.get('original_category_group_id'),
                        'note': category_data.get('note'),
                        'goal_type': category_data.get('goal_type'),
                        'goal_day': category_data.get('goal_day'),
                        'goal_cadence': category_data.get('goal_cadence'),
                        'goal_cadence_frequency': category_data.get('goal_cadence_frequency'),
                        'goal_creation_month': category_data.get('goal_creation_month'),
                        'goal_target': category_data.get('goal_target'),
                        'goal_target_month': category_data.get('goal_target_month'),
                        'goal_percentage_complete': category_data.get('goal_percentage_complete')
                    }
                    
                    cleaned_category = validate_and_clean_data(
                        CleanCategory,
                        clean_category_data,
                        debug_mode=os.getenv('DEBUG_MODE', 'false').lower() in ('true', '1', 'yes')
                    )
                    cleaned_categories.append(cleaned_category.model_dump())
                except Exception as e:
                    from ynab_http_mcp.debug import debug_exception
                    debug_exception(f"Failed to validate category {category_data.get('id', 'unknown')}")
                    continue
            
            # Create cleaned category group with only the fields we need
            cleaned_group_data = {
                'id': group_data.get('id'),
                'name': group_data.get('name'),
                'hidden': group_data.get('hidden', False),
                'deleted': group_data.get('deleted', False),
                'categories': cleaned_categories
            }
            
            # Convert UUID to string if needed
            if 'id' in cleaned_group_data and hasattr(cleaned_group_data['id'], 'hex'):
                cleaned_group_data['id'] = str(cleaned_group_data['id'])
            
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
        try:
            validated_response = validate_and_clean_data(
                CategoriesResponse,
                final_response,
                debug_mode=os.getenv('DEBUG_MODE', 'false').lower() in ('true', '1', 'yes')
            )
            return validated_response
        except Exception as e:
            from ynab_http_mcp.debug import debug_exception
            debug_exception(f"Failed to validate final categories response")
            # Return a fallback response if validation fails
            return CategoriesResponse(category_groups=cleaned_category_groups)
    