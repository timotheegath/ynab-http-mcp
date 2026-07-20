"""
Budget management tools for YNAB HTTP MCP.

This module provides tools for budget management operations including
money reassignment, budget health checking, and spending insights.
"""

from typing import Optional, Dict, Any
import json
from ..ynab_service import YnabService
from ..schemas.budget_tools import (
    UpdateMonthCategoryRequest,
    CreateTransactionRequest,
    BudgetHealthResponse,
    SpendingInsightsResponse,
)


class BudgetManagementTools:
    """
    Budget management tools for YNAB operations.

    Provides methods for updating categories, creating transactions,
    checking budget health, and generating spending insights.
    """

    def __init__(self, ynab_service: YnabService):
        """Initialize with YNAB service instance."""
        self.ynab_service = ynab_service

    def update_month_category(
        self,
        budget_id: str,
        month: str,
        category_id: str,
        request: UpdateMonthCategoryRequest,
    ) -> Dict[str, Any]:
        """
        Update a month category budget amount.

        Args:
            budget_id: YNAB budget ID
            month: Month in YYYY-MM format
            category_id: YNAB category ID
            request: Update request with new budgeted amount

        Returns:
            Dictionary with success status and updated category data
        """
        result = self.ynab_service.update_month_category(
            f"{month}-01", category_id, request.budgeted_amount
        )
        return {"success": True, "category": result.data.category}

    def create_transaction(
        self, budget_id: str, request: CreateTransactionRequest
    ) -> Dict[str, Any]:
        """
        Create a new transaction.

        Args:
            budget_id: YNAB budget ID
            request: Transaction creation request

        Returns:
            Dictionary with success status and created transaction data
        """
        result = self.ynab_service.create_transaction(
            request.account_id,
            request.date,
            request.amount,
            request.payee_id,
            request.payee_name,
            request.category_id,
            request.memo,
            request.cleared,
            request.approved,
            request.flag_color,
        )
        return {"success": True, "transaction": result.data.transaction}

    def check_budget_health(self, budget_id: str, month: str) -> BudgetHealthResponse:
        """
        Check overall budget health for a specific month.

        Args:
            budget_id: YNAB budget ID
            month: Month in YYYY-MM format

        Returns:
            BudgetHealthResponse with health metrics
        """
        # Get month data
        month_detail = self.ynab_service.get_plan_month(month)

        # Calculate health metrics from month detail
        total_income = month_detail.income
        total_budgeted = month_detail.budgeted
        total_activity = month_detail.activity
        to_be_budgeted = month_detail.to_be_budgeted

        # Calculate ratios
        budgeted_ratio = total_budgeted / total_income if total_income > 0 else 0
        activity_ratio = total_activity / total_income if total_income > 0 else 0

        return BudgetHealthResponse(
            month=month,
            total_income=total_income,
            total_budgeted=total_budgeted,
            total_activity=total_activity,
            to_be_budgeted=to_be_budgeted,
            budgeted_ratio=budgeted_ratio,
            activity_ratio=activity_ratio,
            is_healthy=budgeted_ratio <= 1.0 and to_be_budgeted >= 0,
        )

    def get_spending_insights(
        self, budget_id: str, month: str, category_id: Optional[str] = None
    ) -> SpendingInsightsResponse:
        """
        Get spending insights for a month and optional category.

        Args:
            budget_id: YNAB budget ID
            month: Month in YYYY-MM format
            category_id: Optional category ID to filter by

        Returns:
            SpendingInsightsResponse with spending metrics
        """
        # Get transactions for the month
        transactions_response = self.ynab_service.get_transactions(
            since_date=f"{month}-01",
            until_date=None,
            type="outflow",
            month=month,
            category_id=category_id,
        )

        # Extract transactions from response
        transactions = transactions_response.data.transactions

        # Calculate metrics
        total_spending = sum(t.amount for t in transactions)
        average_transaction = total_spending / len(transactions) if transactions else 0
        transaction_count = len(transactions)

        # Get category insights
        category_insights = {}
        for transaction in transactions:
            cat_id = transaction.category_id
            if cat_id:
                amount = transaction.amount
                if cat_id in category_insights:
                    category_insights[cat_id]["total"] += amount
                    category_insights[cat_id]["count"] += 1
                else:
                    category_insights[cat_id] = {
                        "total": amount,
                        "count": 1,
                        "category_name": transaction.category_name or "Unknown",
                    }

        return SpendingInsightsResponse(
            month=month,
            category_id=category_id,
            total_spending=total_spending,
            average_transaction=average_transaction,
            transaction_count=transaction_count,
            category_insights=category_insights,
        )


def register(mcp, ynab_service: YnabService):
    """Register budget management tools with MCP server."""
    tools = BudgetManagementTools(ynab_service)

    @mcp.tool(name="update_month_category")
    def update_month_category_tool(
        budget_id: str,
        month: str,
        category_id: str,
        request: UpdateMonthCategoryRequest,
    ) -> str:
        """Update a month category budget amount."""
        result = tools.update_month_category(budget_id, month, category_id, request)
        return json.dumps(result)

    @mcp.tool(name="create_transaction")
    def create_transaction_tool(
        budget_id: str, request: CreateTransactionRequest
    ) -> str:
        """Create a new transaction."""
        result = tools.create_transaction(budget_id, request)
        return json.dumps(result)

    @mcp.resource(uri="data://budget/check-health", mime_type="application/json")
    def check_budget_health_resource(budget_id: str, month: str) -> str:
        """Check overall budget health for a specific month."""
        result = tools.check_budget_health(budget_id, month)
        return result.model_dump_json()

    @mcp.resource(uri="data://budget/spending-insights", mime_type="application/json")
    def get_spending_insights_resource(
        budget_id: str, month: str, category_id: Optional[str] = None
    ) -> str:
        """Get spending insights for a month and optional category."""
        result = tools.get_spending_insights(budget_id, month, category_id)
        return result.model_dump_json()
