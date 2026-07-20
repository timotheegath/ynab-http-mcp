"""
Simplified category schemas for YNAB HTTP MCP.

This module defines simplified Pydantic models for validating
YNAB category data using basic data types suitable for agents.
"""

from typing import Optional, List
from pydantic import BaseModel, Field
from ynab import CategoriesResponse as ynabCategoriesResponse
from ynab_http_mcp.utils.schema_utils import clean_ynab_data, simple_validate


class CleanCategory(BaseModel):
    """
    Simplified category model using basic data types.

    Represents a YNAB category with all essential fields
    using simple types that are easily consumable by AI agents.
    """

    # Required fields
    id: str = Field(..., description="Unique category identifier")
    category_group_id: str = Field(..., description="ID of the parent category group")
    name: str = Field(..., description="Category name")
    hidden: bool = Field(..., description="Whether category is hidden")
    deleted: bool = Field(..., description="Whether category is deleted")

    # Optional fields
    original_category_group_id: Optional[str] = Field(
        None, description="Original category group ID if moved"
    )
    note: Optional[str] = Field(None, description="Category note")
    goal_type: Optional[str] = Field(None, description="Type of goal if set")
    goal_day: Optional[int] = Field(None, description="Day of month for goal")
    goal_cadence: Optional[int] = Field(None, description="Goal cadence")
    goal_cadence_frequency: Optional[int] = Field(
        None, description="Goal cadence frequency"
    )
    goal_creation_month: Optional[str] = Field(
        None, description="Month when goal was created"
    )
    goal_target: Optional[int] = Field(None, description="Goal target amount")
    goal_target_month: Optional[str] = Field(None, description="Target month for goal")
    goal_percentage_complete: Optional[int] = Field(
        None, description="Percentage of goal completed"
    )


class CategoryGroup(BaseModel):
    """
    Simplified category group model using basic data types.

    Represents a group of related categories.
    """

    id: str = Field(..., description="Unique category group identifier")
    name: str = Field(..., description="Category group name")
    hidden: bool = Field(..., description="Whether category group is hidden")
    deleted: bool = Field(..., description="Whether category group is deleted")
    categories: List[CleanCategory] = Field(
        default_factory=list, description="List of categories in this group"
    )


class CategoriesResponse(BaseModel):
    """
    Simplified response structure for categories endpoint.

    Wraps the list of category groups.
    """

    category_groups: List[CategoryGroup] = Field(
        ..., description="List of category groups"
    )

    @staticmethod
    def from_ynab_response(ynab_response: ynabCategoriesResponse) -> "CategoriesResponse":
        """Transform YNAB API response to match our simplified schema."""
        # Convert to dict
        raw_data = ynab_response.to_dict()

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
            return validated_response
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
            return fallback_response
