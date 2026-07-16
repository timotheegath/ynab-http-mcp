"""
Planning schemas for YNAB HTTP MCP.

This module defines Pydantic models for validating and cleaning
YNAB planning/month data.
"""

from typing import Optional, List
from pydantic import Field
from .base import CleanBaseModel
from . import registry


class MonthCategory(CleanBaseModel):
    """
    Cleaned month category model.
    """

    category_id: str = Field(..., description="Category ID")
    category_name: str = Field(..., description="Category name")
    budgeted: int = Field(..., description="Budgeted amount in milliunits")
    activity: int = Field(..., description="Activity amount in milliunits")
    balance: int = Field(..., description="Balance in milliunits")
    goal_type: Optional[str] = Field(None, description="Goal type if set")
    goal_creation_month: Optional[str] = Field(None, description="Goal creation month")
    goal_target: Optional[int] = Field(None, description="Goal target amount")
    goal_target_month: Optional[str] = Field(None, description="Goal target month")
    goal_percentage_complete: Optional[int] = Field(
        None, description="Goal percentage complete"
    )
    deleted: bool = Field(..., description="Whether category is deleted")


class PlanMonth(CleanBaseModel):
    """
    Cleaned plan month model.
    """

    month: str = Field(..., description="Month identifier (YYYY-MM)")
    income: int = Field(..., description="Total income for the month")
    budgeted: int = Field(..., description="Total budgeted for the month")
    activity: int = Field(..., description="Total activity for the month")
    to_be_budgeted: int = Field(..., description="Amount to be budgeted")
    age_of_money: Optional[int] = Field(None, description="Age of money in days")
    categories: List[MonthCategory] = Field(
        default_factory=list, description="List of month categories"
    )


class PlanMonthResponse(CleanBaseModel):
    """
    Response structure for get_plan_month tool.
    """

    month: PlanMonth = Field(..., description="Plan month details")


class PlanMonthSummary(CleanBaseModel):
    """
    Summary model for plan months.
    """

    month: str = Field(..., description="Month identifier (YYYY-MM)")
    income: int = Field(..., description="Total income for the month")
    budgeted: int = Field(..., description="Total budgeted for the month")
    activity: int = Field(..., description="Total activity for the month")
    to_be_budgeted: int = Field(..., description="Amount to be budgeted")


class AllPlanMonthsResponse(CleanBaseModel):
    """
    Response structure for get_all_plan_months tool.
    """

    months: List[PlanMonthSummary] = Field(
        ..., description="List of plan month summaries"
    )


# Register schemas with the global registry
registry.register("MonthCategory", MonthCategory)
registry.register("PlanMonth", PlanMonth)
registry.register("PlanMonthResponse", PlanMonthResponse)
registry.register("PlanMonthSummary", PlanMonthSummary)
registry.register("AllPlanMonthsResponse", AllPlanMonthsResponse)
