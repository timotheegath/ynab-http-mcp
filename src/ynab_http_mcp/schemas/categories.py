"""
Simplified category schemas for YNAB HTTP MCP.

This module defines simplified Pydantic models for validating
YNAB category data using basic data types suitable for agents.
"""

from typing import Optional, List
from pydantic import BaseModel, Field
from ynab import (
    CategoriesResponse as ynabCategoriesResponse,
    CategoryResponse as ynabCategoryResponse,
)
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

    # Budget fields (using formatted currency from YNAB)
    budgeted_formatted: Optional[str] = Field(
        None, description="Budgeted amount with currency formatting"
    )
    activity_formatted: Optional[str] = Field(
        None, description="Activity amount with currency formatting"
    )
    balance_formatted: Optional[str] = Field(
        None, description="Balance with currency formatting"
    )

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

    # Goal summary fields (human-readable)
    goal_summary: Optional[str] = Field(None, description="Human-readable goal summary")
    goal_status: Optional[str] = Field(None, description="Human-readable goal status")
    goal_technical_details: Optional[str] = Field(
        None, description="Technical goal details for advanced use"
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
    def from_ynab_response(
        ynab_response: ynabCategoriesResponse,
    ) -> "CategoriesResponse":
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


class CategoryResponse(BaseModel):
    """
    Simplified response structure for single category endpoint.

    Wraps a single category with its group information.
    """

    category: CleanCategory = Field(..., description="Single category details")
    category_group: CategoryGroup = Field(..., description="Parent category group")

    @staticmethod
    def from_ynab_response(ynab_response: ynabCategoryResponse) -> "CategoryResponse":
        """Transform YNAB API response to match our simplified schema."""
        # Convert to dict
        raw_data = ynab_response.to_dict()

        # Extract category and group data from YNAB response structure
        category_data = raw_data.get("data", {}).get("category", {})
        group_data = raw_data.get("data", {}).get("category_group", {})

        try:
            # Clean and validate category data
            cleaned_category_data = clean_ynab_data(category_data)
            validated_category = simple_validate(cleaned_category_data, CleanCategory)

            # Clean and validate group data
            cleaned_group_data = clean_ynab_data(group_data)
            # Add the cleaned category to the group
            cleaned_group_data["categories"] = [validated_category.model_dump()]
            validated_group = simple_validate(cleaned_group_data, CategoryGroup)

            # Create final response
            final_response = {
                "category": validated_category.model_dump(),
                "category_group": validated_group.model_dump(),
            }

            # Validate complete response structure
            validated_response = simple_validate(final_response, CategoryResponse)
            return validated_response

        except Exception:
            from ynab_http_mcp.debug import debug_exception

            debug_exception(
                f"Failed to validate category response for category {category_data.get('id', 'unknown')}"
            )

            # Return a fallback response if validation fails
            try:
                # Try to create basic objects even if validation failed
                basic_category = CleanCategory(**clean_ynab_data(category_data))
                basic_group = CategoryGroup(
                    id=group_data.get("id", ""),
                    name=group_data.get("name", ""),
                    hidden=group_data.get("hidden", False),
                    deleted=group_data.get("deleted", False),
                    categories=[basic_category],
                )
                fallback_response = CategoryResponse(
                    category=basic_category, category_group=basic_group
                )
                return fallback_response
            except Exception:
                # If all else fails, raise the original exception
                raise
