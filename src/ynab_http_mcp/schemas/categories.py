"""
Category schemas for YNAB HTTP MCP.

This module defines Pydantic models for validating and cleaning
YNAB category data.
"""

from typing import Optional, List
from pydantic import Field
from .base import CleanBaseModel
from . import registry


class CleanCategory(CleanBaseModel):
    """
    Cleaned category model for YNAB categories.

    Represents a YNAB category with all essential fields.
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

    class Config(CleanBaseModel.Config):
        json_schema_extra = {
            "examples": [
                {
                    "description": "Example cleaned category",
                    "value": {
                        "id": "123e4567-e89b-12d3-a456-426614174000",
                        "category_group_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
                        "name": "Groceries",
                        "hidden": False,
                        "deleted": False,
                        "note": "Monthly grocery budget",
                        "goal_type": "TB",
                        "goal_target": 500000,  # $500.00 in milliunits
                        "goal_percentage_complete": 60,
                    },
                }
            ]
        }


class CategoryGroup(CleanBaseModel):
    """
    Category group model for YNAB category groups.

    Represents a group of related categories.
    """

    id: str = Field(..., description="Unique category group identifier")
    name: str = Field(..., description="Category group name")
    hidden: bool = Field(..., description="Whether category group is hidden")
    deleted: bool = Field(..., description="Whether category group is deleted")
    categories: List[CleanCategory] = Field(
        default_factory=list, description="List of categories in this group"
    )

    class Config(CleanBaseModel.Config):
        json_schema_extra = {
            "examples": [
                {
                    "description": "Example category group",
                    "value": {
                        "id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
                        "name": "Everyday Expenses",
                        "hidden": False,
                        "deleted": False,
                        "categories": [],
                    },
                }
            ]
        }


class CategoriesResponse(CleanBaseModel):
    """
    Complete response structure for categories endpoint.

    Wraps the list of category groups.
    """

    category_groups: List[CategoryGroup] = Field(
        ..., description="List of category groups"
    )

    class Config(CleanBaseModel.Config):
        json_schema_extra = {
            "examples": [
                {
                    "description": "Example categories response",
                    "value": {"category_groups": []},
                }
            ]
        }


# Register schemas with the global registry
registry.register("CleanCategory", CleanCategory)
registry.register("CategoryGroup", CategoryGroup)
registry.register("CategoriesResponse", CategoriesResponse)
