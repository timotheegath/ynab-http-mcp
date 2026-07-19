"""
Simplified category schemas for YNAB HTTP MCP.

This module defines simplified Pydantic models for validating
YNAB category data using basic data types suitable for agents.
"""

from typing import Optional, List
from pydantic import BaseModel, Field


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



