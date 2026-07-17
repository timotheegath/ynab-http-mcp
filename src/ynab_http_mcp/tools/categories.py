from ynab_http_mcp.ynab_service import YnabService
from ynab_http_mcp.schemas.categories import (
    CategoriesResponse,
    CategoryGroup,
    CleanCategory,
)
from ynab_http_mcp.utils.schema_utils import clean_ynab_data
from ynab_http_mcp.utils.simple_validation import simple_validate

import json


def register(mcp, ynab_service: YnabService):
    @mcp.resource(uri="data://categories", mime_type="application/json")
    async def get_categories() -> str:
        """Get a list of category groups and their categories."""
        # Get raw YNAB response
        raw_response = ynab_service.get_categories()

        # Convert to dict
        raw_data = raw_response.to_dict()

        # Clean and validate category groups and categories using simplified approach
        cleaned_category_groups = []

        for group_data in raw_data.get("data", {}).get("category_groups", []):
            # Clean categories within the group using unified cleaning
            cleaned_categories = []
            for category_data in group_data.get("categories", []):
                try:
                    # Clean data using unified function
                    cleaned_data = clean_ynab_data(category_data)

                    # Validate using simplified approach
                    validated_category = simple_validate(cleaned_data, CleanCategory)
                    cleaned_categories.append(validated_category.model_dump())
                except Exception:
                    from ynab_http_mcp.debug import debug_exception

                    debug_exception(
                        f"Failed to validate category {category_data.get('id', 'unknown')}"
                    )
                    continue

            # Clean group data using unified cleaning
            cleaned_group_data = clean_ynab_data(group_data)
            cleaned_group_data["categories"] = cleaned_categories

            try:
                cleaned_group = simple_validate(cleaned_group_data, CategoryGroup)
                cleaned_category_groups.append(cleaned_group.model_dump())
            except Exception:
                from ynab_http_mcp.debug import debug_exception

                debug_exception(
                    f"Failed to validate category group {group_data.get('id', 'unknown')}"
                )
                continue

        # Create final response
        final_response = {"category_groups": cleaned_category_groups}

        # Validate complete response structure using simplified approach
        try:
            validated_response = simple_validate(final_response, CategoriesResponse)
            # Return as JSON string for MCP resource compatibility
            return json.dumps(validated_response.model_dump())
        except Exception:
            from ynab_http_mcp.debug import debug_exception

            debug_exception("Failed to validate final categories response")
            # Return a fallback response if validation fails
            # Convert dicts back to CategoryGroup objects for type safety
            fallback_groups = []
            for group_dict in cleaned_category_groups:
                try:
                    # Convert categories back to CleanCategory objects
                    categories = []
                    for cat_dict in group_dict.get("categories", []):
                        categories.append(CleanCategory(**cat_dict))

                    # Create CategoryGroup object
                    group_obj = CategoryGroup(
                        id=group_dict["id"],
                        name=group_dict["name"],
                        hidden=group_dict.get("hidden", False),
                        deleted=group_dict.get("deleted", False),
                        categories=categories,
                    )
                    fallback_groups.append(group_obj)
                except Exception:
                    # If conversion fails, skip this group
                    continue

            fallback_response = CategoriesResponse(category_groups=fallback_groups)
            return json.dumps(fallback_response.model_dump())
