"""
Budget management tools for YNAB HTTP MCP.

This module provides tools for budget management operations including
money reassignment, budget health checking, and spending insights.
"""

from typing import Optional, Dict, Any
import json
from ..ynab_service import YnabService
from ..utils.schema_utils import clean_ynab_data
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
        month: str,
        category_id: str,
        request: UpdateMonthCategoryRequest,
    ) -> Dict[str, Any]:
        """
        Update a month category budget amount.

        Args:
            month: Month in YYYY-MM format
            category_id: YNAB category ID
            request: Update request with new budgeted amount

        Returns:
            Dictionary with success status and updated category data
        """
        result = self.ynab_service.update_month_category(
            f"{month}-01", category_id, request.budgeted_amount
        )
        return {
            "success": True,
            "category": clean_ynab_data(result.data.category.to_dict()),
        }

    def assign_money_to_category(
        self, month: str, category_id: str, budget: int
    ) -> str:
        result = self.ynab_service.assign_money(month, category_id, budget)
        return "success"

    def create_transaction(self, request: CreateTransactionRequest) -> Dict[str, Any]:
        """
        Create a new transaction.

        Args:
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
        return {
            "success": True,
            "transaction": clean_ynab_data(result.data.transaction.to_dict()),
        }

    def check_budget_health(self, month: str) -> BudgetHealthResponse:
        """
        Check overall budget health for a specific month.

        Args:
            month: Month in YYYY-MM format

        Returns:
            BudgetHealthResponse with health metrics
        """
        # Get month data
        month_detail = self.ynab_service.get_plan_month(month).data.month

        # Calculate health metrics from month detail
        total_budgeted = month_detail.budgeted
        total_activity = month_detail.activity
        to_be_budgeted = month_detail.to_be_budgeted

        # Calculate category-level health metrics
        category_health = {}
        healthy_categories = 0
        total_categories = 0

        for category in month_detail.categories:
            cat_budgeted = category.budgeted
            cat_activity = category.activity
            cat_balance = category.balance

            # Skip categories with no budgeted amount
            if cat_budgeted == 0:
                continue

            total_categories += 1

            # Calculate category health metrics
            activity_ratio = cat_activity / cat_budgeted if cat_budgeted > 0 else 0
            is_healthy = cat_balance >= 0 and activity_ratio <= 1.0

            if is_healthy:
                healthy_categories += 1

            category_health[str(category.id)] = {
                "category_name": category.name,
                "budgeted": cat_budgeted,
                "activity": cat_activity,
                "balance": cat_balance,
                "activity_ratio": activity_ratio,
                "is_healthy": is_healthy,
            }

        # Calculate overall health percentage
        health_percentage = (
            (healthy_categories / total_categories) if total_categories > 0 else 1.0
        )

        return BudgetHealthResponse(
            month=month,
            total_budgeted=total_budgeted,
            total_activity=total_activity,
            to_be_budgeted=to_be_budgeted,
            category_health=category_health,
            health_percentage=health_percentage,
            is_healthy=health_percentage
            >= 0.8,  # Consider healthy if 80%+ categories are healthy
        )

    def get_spending_insights(
        self, month: str, category_id: Optional[str] = None
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
        from datetime import datetime

        month_datetime = datetime.strptime(f"{month}-01", "%Y-%m-%d")
        transactions_response = self.ynab_service.get_transactions(
            since_date=f"{month}-01",
            until_date=None,
            type="outflow",
            month=month_datetime,
            category_id=category_id,
        )

        # Extract transactions from response
        transactions = transactions_response.data.transactions

        # Calculate metrics
        total_spending = sum(t.amount for t in transactions)
        average_transaction = total_spending / len(transactions) if transactions else 0
        transaction_count = len(transactions)

        # Get category insights
        category_insights: Dict[str, Any] = {}
        for transaction in transactions:
            cat_id = str(transaction.category_id)
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
        month: str,
        category_id: str,
        request: UpdateMonthCategoryRequest,
    ) -> str:
        """Update a month category's targets."""
        result = tools.update_month_category(month, category_id, request)
        return json.dumps(result)

    @mcp.tool(name="assign_budget_to_category")
    def assign_budget_to_category_tool(
        month: str,
        category_id: str,
        budget: int,
    ) -> str:
        """Assign budget to a month category. Pass an integer expressed in the correct currency."""
        result = tools.assign_money_to_category(month, category_id, budget)
        return json.dumps(result)

    @mcp.tool(name="create_transaction")
    def create_transaction_tool(request: CreateTransactionRequest) -> str:
        """Create a new transaction."""
        result = tools.create_transaction(request)
        return json.dumps(result)

    @mcp.resource(
        uri="data://budget/check-health/{month}",
        mime_type="application/json",
    )
    def check_budget_health_resource(month: str) -> str:
        """Check overall budget health for a specific month."""
        result = tools.check_budget_health(month)
        return result.model_dump_json()

    @mcp.resource(
        uri="data://budget/spending-insights/{month}",
        mime_type="application/json",
    )
    def get_spending_insights_resource(
        month: str, category_id: Optional[str] = None
    ) -> str:
        """Get spending insights for a month and optional category."""
        result = tools.get_spending_insights(month, category_id)
        return result.model_dump_json()
