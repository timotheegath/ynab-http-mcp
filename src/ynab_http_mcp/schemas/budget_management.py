"""
Request and response schemas for budget management tools.

This module defines Pydantic models for validating write operation
requests and responses for the budget management tools.
"""

from typing import Optional, List
from pydantic import BaseModel, Field
from enum import Enum


class ReassignMoneyRequest(BaseModel):
    """
    Request schema for reassign_money tool.
    """

    source_category_id: Optional[str] = Field(
        None,
        description="Source category ID. If None, money comes from Ready to Assign",
    )
    destination_category_id: str = Field(..., description="Destination category ID")
    amount: int = Field(
        ..., description="Amount to move in milliunits (must be positive)", gt=0
    )
    month: str = Field(
        ..., description="Month in YYYY-MM format", pattern=r"^\d{4}-\d{2}$"
    )
    memo: Optional[str] = Field(
        None, description="Optional memo for the transaction", max_length=200
    )


class ReassignMoneyResponse(BaseModel):
    """
    Response schema for reassign_money tool.
    """

    success: bool = Field(..., description="Whether the operation was successful")
    source_category_id: Optional[str] = Field(
        None, description="Source category ID (None if from Ready to Assign)"
    )
    destination_category_id: str = Field(..., description="Destination category ID")
    amount: int = Field(..., description="Amount moved in milliunits")
    month: str = Field(..., description="Month in YYYY-MM format")
    transaction_id: Optional[str] = Field(
        None, description="ID of the created transaction"
    )
    source_balance: Optional[int] = Field(
        None, description="Updated source category balance in milliunits"
    )
    destination_balance: int = Field(
        ..., description="Updated destination category balance in milliunits"
    )
    ready_to_assign: Optional[int] = Field(
        None, description="Updated Ready to Assign amount in milliunits"
    )
    error: Optional[str] = Field(None, description="Error message if operation failed")


class BudgetHealthStatus(str, Enum):
    HEALTHY = "healthy"
    OVERASSIGNED = "overassigned"
    HAS_NEGATIVE_CATEGORIES = "has_negative_categories"


class ProblemCategory(BaseModel):
    """
    Schema for categories with problems (negative balances).
    """

    category_id: str = Field(..., description="Category ID")
    category_name: str = Field(..., description="Category name")
    negative_balance: int = Field(
        ..., description="Negative balance amount in milliunits", lt=0
    )


class BudgetHealthResponse(BaseModel):
    """
    Response schema for check_budget_health tool.
    """

    healthy: bool = Field(..., description="Whether the budget is healthy")
    status: BudgetHealthStatus = Field(..., description="Detailed budget health status")
    ready_to_assign: int = Field(
        ..., description="Current Ready to Assign amount in milliunits"
    )
    overassigned_amount: Optional[int] = Field(
        None,
        description="Amount of overassignment in milliunits (negative if overassigned)",
        le=0,
    )
    problem_categories: List[ProblemCategory] = Field(
        default_factory=list, description="List of categories with negative balances"
    )
    error: Optional[str] = Field(None, description="Error message if operation failed")


class SpendingTrend(str, Enum):
    INCREASING = "increasing"
    DECREASING = "decreasing"
    STABLE = "stable"


class CategorySpendingInsightsResponse(BaseModel):
    """
    Response schema for get_category_spending_insights tool.
    """

    category_id: str = Field(..., description="Category ID")
    category_name: str = Field(..., description="Category name")
    month: str = Field(..., description="Month in YYYY-MM format")
    budgeted: int = Field(..., description="Budgeted amount in milliunits")
    spent: int = Field(..., description="Amount spent in milliunits")
    remaining: int = Field(..., description="Remaining budget in milliunits")
    usage_percentage: float = Field(
        ..., description="Budget usage percentage (0-100)", ge=0, le=100
    )
    projected_overspend: int = Field(
        ..., description="Projected overspend amount in milliunits (0 if none)", ge=0
    )
    comparison_month: Optional[str] = Field(
        None, description="Comparison month in YYYY-MM format"
    )
    comparison_spent: Optional[int] = Field(
        None, description="Amount spent in comparison month in milliunits"
    )
    spending_change: Optional[int] = Field(
        None,
        description="Change in spending compared to comparison month in milliunits",
    )
    trend: Optional[SpendingTrend] = Field(None, description="Spending trend")
    error: Optional[str] = Field(None, description="Error message if operation failed")


class GoalAchievementStatus(str, Enum):
    ON_TRACK = "on_track"
    BEHIND = "behind"
    AHEAD = "ahead"
    ACHIEVED = "achieved"


class MonthlyBudgetData(BaseModel):
    """
    Schema for monthly budget data in budget insights.
    """

    month: str = Field(..., description="Month in YYYY-MM format")
    budgeted: int = Field(..., description="Budgeted amount in milliunits")
    spent: int = Field(..., description="Amount spent in milliunits")
    balance: int = Field(..., description="Ending balance in milliunits")


class BudgetInsightsResponse(BaseModel):
    """
    Response schema for get_budget_insights tool.
    """

    category_id: str = Field(..., description="Category ID")
    category_name: str = Field(..., description="Category name")
    historical_data: List[MonthlyBudgetData] = Field(
        ..., description="12 months of historical budget data", min_length=1
    )
    average_monthly_spending: float = Field(
        ..., description="Average monthly spending over the period"
    )
    spending_trend: SpendingTrend = Field(..., description="Overall spending trend")
    current_month_budgeted: int = Field(
        ..., description="Current month's budgeted amount in milliunits"
    )
    current_month_spent: int = Field(
        ..., description="Current month's spending in milliunits"
    )
    current_month_remaining: int = Field(
        ..., description="Current month's remaining budget in milliunits"
    )
    has_goal: bool = Field(..., description="Whether the category has a goal")
    goal_target: Optional[int] = Field(
        None, description="Goal target amount in milliunits"
    )
    goal_funded: Optional[int] = Field(
        None, description="Amount funded toward goal in milliunits"
    )
    goal_remaining: Optional[int] = Field(
        None, description="Amount remaining to reach goal in milliunits"
    )
    goal_completion_percentage: Optional[float] = Field(
        None, description="Goal completion percentage (0-100)", ge=0, le=100
    )
    goal_status: Optional[GoalAchievementStatus] = Field(
        None, description="Goal achievement status"
    )
    seasonal_pattern_detected: bool = Field(
        ..., description="Whether seasonal spending patterns were detected"
    )
    error: Optional[str] = Field(None, description="Error message if operation failed")


class UpdateCategoryRequest(BaseModel):
    """
    Request schema for update_category service method.
    """

    month: str = Field(
        ..., description="Month in YYYY-MM format", pattern=r"^\d{4}-\d{2}$"
    )
    category_id: str = Field(..., description="Category ID")
    budgeted_amount: Optional[int] = Field(
        None, description="New budgeted amount in milliunits"
    )
    balance_adjustment: Optional[int] = Field(
        None, description="Amount to adjust balance by in milliunits"
    )


class CreateTransactionRequest(BaseModel):
    """
    Request schema for create_transaction service method.
    """

    account_id: str = Field(..., description="Account ID")
    date: str = Field(
        ...,
        description="Transaction date in YYYY-MM-DD format",
        pattern=r"^\d{4}-\d{2}-\d{2}$",
    )
    amount: int = Field(..., description="Transaction amount in milliunits")
    payee_id: Optional[str] = Field(
        None, description="Payee ID (required if payee_name not provided)"
    )
    payee_name: Optional[str] = Field(
        None, description="Payee name (required if payee_id not provided)"
    )
    category_id: Optional[str] = Field(None, description="Category ID")
    memo: Optional[str] = Field(None, description="Transaction memo", max_length=200)
    cleared: str = Field(
        "cleared",
        description="Cleared status",
        pattern=r"^(cleared|uncleared|reconciled)$",
    )
    approved: bool = Field(True, description="Whether transaction is approved")
    flag_color: Optional[str] = Field(
        None,
        description="Flag color",
        pattern=r"^(red|orange|yellow|green|blue|purple)$",
    )
