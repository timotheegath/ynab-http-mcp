"""
Simplified planning schemas for YNAB HTTP MCP.

This module defines simplified Pydantic models for validating
YNAB planning/month data using basic data types suitable for agents.
"""

from __future__ import annotations

from datetime import date
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

import ynab
from ynab_http_mcp.utils.schema_utils import clean_ynab_data, simple_validate
from ynab_http_mcp.schemas.categories import MCPCategoryGoal


def _convert_date_to_string(date_value: Any) -> Optional[str]:
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
    Lean month category model.

    Per the Lean / Full / Aggregate convention:

    - Currency fields are exposed as formatted strings only
      (``budgeted_formatted``, ``activity_formatted``, ``balance_formatted``).
      The integer milliunit twins are dropped from the lean layer and live
      only on the Full layer (``data://months/{ym}/full``).
    - The goal is a nested lean ``MCPCategoryGoal`` (3 raw fields + 2
      derived strings). The 11 dropped goal fields and the
      ``goal_technical_details`` string live only on the Full layer.
    """

    category_id: str = Field(..., description="Category ID")
    category_name: str = Field(..., description="Category name")

    # Formatted currency fields from YNAB (Lean layer — no milliunit twins)
    budgeted_formatted: Optional[str] = Field(
        None, description="Budgeted amount with currency formatting"
    )
    activity_formatted: Optional[str] = Field(
        None, description="Activity amount with currency formatting"
    )
    balance_formatted: Optional[str] = Field(
        None, description="Balance with currency formatting"
    )

    # Nested lean goal (3 raw fields + 2 derived strings)
    goal: Optional[MCPCategoryGoal] = Field(
        None, description="Goal attached to this category, if any"
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

    @staticmethod
    def from_ynab_response(ynab_response: ynab.MonthDetailResponse) -> "PlanMonth":
        """Transform YNAB API response to match our simplified schema."""
        data = ynab_response.to_dict()

        # Extract the month data from the nested structure
        if "data" in data and "month" in data["data"]:
            month_data = data["data"]["month"]
        else:
            month_data = data.get("month", {})

        # Convert date object to YYYY-MM string format if needed
        if "month" in month_data and isinstance(month_data["month"], date):
            month_data["month"] = month_data["month"].strftime("%Y-%m")

        # Build lean MonthCategory list with nested lean goals
        if "categories" in month_data:
            transformed_categories = []
            for category in month_data["categories"]:
                raw_category = ynab.Category.model_validate(category)
                transformed_categories.append(
                    MonthCategory(
                        category_id=str(raw_category.id),
                        category_name=raw_category.name,
                        budgeted_formatted=raw_category.budgeted_formatted,
                        activity_formatted=raw_category.activity_formatted,
                        balance_formatted=raw_category.balance_formatted,
                        goal=MCPCategoryGoal.from_ynab(raw_category),
                        deleted=raw_category.deleted,
                    )
                )
            month_data["categories"] = [
                cat.model_dump() for cat in transformed_categories
            ]

        return PlanMonth(**month_data)


class PlanMonthResponse(BaseModel):
    """
    Simplified response structure for get_plan_month tool.
    """

    month: PlanMonth = Field(..., description="Plan month details")

    @staticmethod
    def from_ynab_response(
        ynab_response: ynab.MonthDetailResponse,
    ) -> "PlanMonthResponse":
        """Transform YNAB API response to match our schema."""
        transformed_month = PlanMonth.from_ynab_response(ynab_response)
        final_response = {"month": transformed_month.model_dump()}
        validated_response = simple_validate(final_response, PlanMonthResponse)
        return validated_response


class PlanMonthFull(PlanMonth):
    """Full sibling of ``PlanMonth`` — same lean fields plus ``full_details``.

    ``full_details`` is the cleaned raw ``ynab.MonthDetail`` as a dict and
    contains the integer milliunit ``budgeted``/``activity``/``balance``,
    the full raw goal field set, and every other field the Lean layer
    dropped. Use this when arithmetic or SDK-fidelity access is required.
    """

    full_details: Dict[str, Any] = Field(
        default_factory=dict,
        description=(
            "Cleaned raw ``ynab.MonthDetail`` as a dict. Contains every field "
            "the YNAB SDK exposes for a month detail, including the integer "
            "milliunit budget/activity/balance and the full raw goal field "
            "set. UUIDs are strings, datetimes are ISO dates, and YNAB-specific "
            "import fields are removed."
        ),
    )

    @staticmethod
    def from_ynab_response(ynab_response: ynab.MonthDetailResponse) -> "PlanMonthFull":
        transformed_month = PlanMonth.from_ynab_response(ynab_response)
        # The raw MonthDetail is the inner month; rebuild a ynab object for
        # clean_ynab_data via the same dict the service returned.
        data = ynab_response.to_dict()
        if "data" in data and "month" in data["data"]:
            month_dict = data["data"]["month"]
        else:
            month_dict = data.get("month", {})
        return PlanMonthFull(
            **transformed_month.model_dump(),
            full_details=clean_ynab_data(month_dict),
        )


class PlanMonthFullResponse(BaseModel):
    """Drill-in response shape for a single plan month, including the
    cleaned raw ``ynab.MonthDetail`` under ``full_details``."""

    month: PlanMonthFull = Field(..., description="Plan month details (Full layer)")


class MonthCategoryFull(MonthCategory):
    """Full sibling of ``MonthCategory`` — same lean fields plus ``full_details``."""

    full_details: Dict[str, Any] = Field(
        default_factory=dict,
        description=(
            "Cleaned raw ``ynab.Category`` (per-month) as a dict. Contains "
            "every field the YNAB SDK exposes for the category in this "
            "month, including the integer milliunit budget/activity/balance "
            "and the full raw goal field set. UUIDs are strings, datetimes "
            "are ISO dates, and YNAB-specific import fields are removed."
        ),
    )


class PlanMonthSummary(BaseModel):
    """
    Simplified summary model for plan months using basic data types.
    """

    month: str = Field(..., description="Month identifier (YYYY-MM)")
    income: int = Field(..., description="Total income for the month")
    budgeted: int = Field(..., description="Total budgeted for the month")
    activity: int = Field(..., description="Total activity for the month")
    to_be_budgeted: int = Field(..., description="Amount to be budgeted")

    @staticmethod
    def from_ynab_response(
        ynab_response: ynab.MonthSummary,
    ) -> "PlanMonthSummary":
        """Transform YNAB API response to match our simplified schema."""
        data = ynab_response.to_dict()
        if "month" in data and isinstance(data["month"], date):
            data["month"] = data["month"].strftime("%Y-%m")
        response = PlanMonthSummary(**data)
        validated_response = simple_validate(response.model_dump(), PlanMonthSummary)
        return validated_response


class AllPlanMonthsResponse(BaseModel):
    """
    Simplified response structure for get_all_plan_months tool.
    """

    months: List[PlanMonthSummary] = Field(
        ..., description="List of plan month summaries"
    )

    @staticmethod
    def from_ynab_response(
        ynab_response: ynab.MonthSummariesResponse,
    ) -> "AllPlanMonthsResponse":
        """Transform YNAB API response to match our schema."""
        transformed_months = []
        for month_summary in ynab_response.data.months:
            transformed_month = PlanMonthSummary.from_ynab_response(month_summary)
            transformed_months.append(transformed_month.model_dump())
        final_response = {"months": transformed_months}
        validated_response = simple_validate(final_response, AllPlanMonthsResponse)
        return validated_response
