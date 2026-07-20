"""
Budget tool schemas for YNAB HTTP MCP.

This module defines Pydantic models for budget management tool
requests and responses.
"""

from typing import Optional, Dict, List, Any
from pydantic import BaseModel, Field


class UpdateMonthCategoryRequest(BaseModel):
    """
    Request schema for updating a month category budget amount.
    """

    budgeted_amount: int = Field(
        ..., description="New budgeted amount in milliunits", ge=0
    )


class CreateTransactionRequest(BaseModel):
    """
    Request schema for creating a new transaction.
    """

    account_id: str = Field(..., description="YNAB account ID")
    date: str = Field(..., description="Transaction date in YYYY-MM-DD format")
    amount: int = Field(..., description="Transaction amount in milliunits")
    payee_id: Optional[str] = Field(None, description="YNAB payee ID")
    payee_name: Optional[str] = Field(None, description="Payee name")
    category_id: Optional[str] = Field(None, description="YNAB category ID")
    memo: Optional[str] = Field(None, description="Transaction memo")
    cleared: str = Field("cleared", description="Transaction cleared status")
    approved: bool = Field(True, description="Whether transaction is approved")
    flag_color: Optional[str] = Field(None, description="Transaction flag color")


class BudgetHealthResponse(BaseModel):
    """
    Response schema for budget health check.
    """

    month: str = Field(..., description="Month in YYYY-MM format")
    total_budgeted: int = Field(..., description="Total budgeted in milliunits")
    total_activity: int = Field(..., description="Total activity in milliunits")
    to_be_budgeted: int = Field(..., description="To be budgeted in milliunits")
    category_health: Dict[str, Dict[str, Any]] = Field(
        ..., description="Category-level health metrics"
    )
    health_percentage: float = Field(
        ..., description="Percentage of healthy categories"
    )
    is_healthy: bool = Field(..., description="Whether budget is healthy overall")


class SpendingInsightCategory(BaseModel):
    """
    Category spending insight.
    """

    category_id: str = Field(..., description="Category ID")
    category_name: str = Field(..., description="Category name")
    total: int = Field(..., description="Total spending in milliunits")
    count: int = Field(..., description="Number of transactions")


class SpendingInsightsResponse(BaseModel):
    """
    Response schema for spending insights.
    """

    month: str = Field(..., description="Month in YYYY-MM format")
    category_id: Optional[str] = Field(
        None, description="Filtered category ID if applicable"
    )
    total_spending: int = Field(..., description="Total spending in milliunits")
    average_transaction: float = Field(..., description="Average transaction amount")
    transaction_count: int = Field(..., description="Number of transactions")
    category_insights: Dict[str, Dict[str, Any]] = Field(
        ..., description="Category-level spending insights"
    )
