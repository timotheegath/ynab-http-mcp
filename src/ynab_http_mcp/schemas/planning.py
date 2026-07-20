"""
Simplified planning schemas for YNAB HTTP MCP.

This module defines simplified Pydantic models for validating
YNAB planning/month data using basic data types suitable for agents.
"""

from typing import Optional, List
from pydantic import BaseModel, Field
from datetime import date
from ynab_http_mcp.utils.schema_utils import simple_validate


def _convert_date_to_string(date_value):
    """Convert date object to YYYY-MM-DD string format."""
    if date_value is None:
        return None
    if isinstance(date_value, date):
        return date_value.strftime("%Y-%m-%d")
    if isinstance(date_value, str):
        return date_value
    return str(date_value)


class MonthCategory(BaseModel):
    """
    Simplified month category model using basic data types.
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


class PlanMonth(BaseModel):
    """
    Simplified plan month model using basic data types.
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

    @classmethod
    def from_ynab_data(cls, data: dict) -> "PlanMonth":
        """Transform YNAB API data to match our simplified schema."""
        # Convert date object to YYYY-MM string format if needed
        if "month" in data and isinstance(data["month"], date):
            data["month"] = data["month"].strftime("%Y-%m")

        # Transform categories to match our schema
        if "categories" in data:
            transformed_categories = []
            for category in data["categories"]:
                transformed_category = {
                    "category_id": str(category.get("id", "")),
                    "category_name": category.get("name", ""),
                    "budgeted": category.get("budgeted", 0),
                    "activity": category.get("activity", 0),
                    "balance": category.get("balance", 0),
                    "goal_type": category.get("goal_type"),
                    "goal_creation_month": _convert_date_to_string(
                        category.get("goal_creation_month")
                    ),
                    "goal_target": category.get("goal_target"),
                    "goal_target_month": _convert_date_to_string(
                        category.get("goal_target_month")
                    ),
                    "goal_percentage_complete": category.get(
                        "goal_percentage_complete"
                    ),
                    "deleted": category.get("deleted", False),
                }
                transformed_categories.append(transformed_category)
            data["categories"] = transformed_categories

        return cls(**data)


class PlanMonthResponse(BaseModel):
    """
    Simplified response structure for get_plan_month tool.
    """

    month: PlanMonth = Field(..., description="Plan month details")

    @classmethod
    def from_ynab_data(cls, data: dict) -> "PlanMonthResponse":
        """Transform YNAB API data to match our simplified schema."""
        if "month" in data:
            data["month"] = PlanMonth.from_ynab_data(data["month"])
        response = cls(**data)
        validated_response = simple_validate(
            response.model_dump(), PlanMonthResponse
        )
        return validated_response


class PlanMonthSummary(BaseModel):
    """
    Simplified summary model for plan months using basic data types.
    """

    month: str = Field(..., description="Month identifier (YYYY-MM)")
    income: int = Field(..., description="Total income for the month")
    budgeted: int = Field(..., description="Total budgeted for the month")
    activity: int = Field(..., description="Total activity for the month")
    to_be_budgeted: int = Field(..., description="Amount to be budgeted")

    @classmethod
    def from_ynab_data(cls, data: dict) -> "PlanMonthSummary":
        """Transform YNAB API data to match our simplified schema."""
        # Convert date object to YYYY-MM string format if needed
        if "month" in data and isinstance(data["month"], date):
            data["month"] = data["month"].strftime("%Y-%m")
        response = cls(**data)
        validated_response = simple_validate(
            response.model_dump(), PlanMonthSummary
        )
        return validated_response


class AllPlanMonthsResponse(BaseModel):
    """
    Simplified response structure for get_all_plan_months tool.
    """

    months: List[PlanMonthSummary] = Field(
        ..., description="List of plan month summaries"
    )
