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
    AssignBudgetCategoryRequest,
    CreateTransactionRequest,
    UpdateCategoryDetailsRequest,
    UpdateCategoryGoalRecurringRequest,
    UpdateCategoryTargetDateRequest,
    ClearCategoryGoalRequest,
    BudgetHealthResponse,
    SpendingInsightsResponse,
)




    
def register(mcp, ynab_service: YnabService):
    """Register budget management tools with MCP server."""
    def assign_budget_to_category(
         request: AssignBudgetCategoryRequest
    ) -> Dict[str, Any]:
        """
        Update a month category budget amount.

        Args:
            request: Update request with month, category_id, and new budgeted amount

        Returns:
            Dictionary with success status and updated category data
        """
        result = ynab_service.update_month_category(
            f"{request.month}-01", request.category_id, request.budgeted_amount
        )
        return {
            "success": True,
            "category": clean_ynab_data(result.data.category.to_dict()),
        }

    def update_category_goal_to_recurring(
         request: UpdateCategoryGoalRecurringRequest
    ) -> Dict[str, Any]:
        """
        Update a category's goal to a recurring goal in YNAB.

        Args:
            request: Update request with category parameters and goal settings

        Returns:
            Dictionary with success status and updated category data
        """
        result = ynab_service.update_category(
            request.to_update_category_request()
        )
        return {
            "success": True,
            "category": clean_ynab_data(result.data.category.to_dict()),
        }
    def update_category_goal_to_target_date(
         request: UpdateCategoryTargetDateRequest
    ) -> Dict[str, Any]:
        """
        Update a category's goal to set aside until a target date.

        Args:
            request: Update request with category parameters and goal settings

        Returns:
            Dictionary with success status and updated category data
        """
        result = ynab_service.update_category(
            request.to_update_category_request()
        )
        return {
            "success": True,
            "category": clean_ynab_data(result.data.category.to_dict()),
        }
    def update_category_details(
         request: UpdateCategoryDetailsRequest
    ) -> Dict[str, Any]:
        """
        Update a category's details, and assignment to a category group ID.

        Args:
            request: Update request with category parameters and goal settings

        Returns:
            Dictionary with success status and updated category data
        """
        result = ynab_service.update_category(
            request.to_update_category_request()
        )
        return {
            "success": True,
            "category": clean_ynab_data(result.data.category.to_dict()),
        }
    def clear_category_goals(
         request: ClearCategoryGoalRequest
    ) -> Dict[str, Any]:
        """
        Clear a category's goal

        Args:
            request: Update request with category parameters and goal settings

        Returns:
            Dictionary with success status and updated category data
        """
        result = ynab_service.update_category(
            request.to_update_category_request()
        )
        return {
            "success": True,
            "category": clean_ynab_data(result.data.category.to_dict()),
        }
    

    def create_transaction( request: CreateTransactionRequest) -> Dict[str, Any]:
        """
        Create a new transaction.

        Args:
            request: Transaction creation request

        Returns:
            Dictionary with success status and created transaction data
        """
        result = ynab_service.create_transaction(
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

    def check_budget_health( month: str) -> BudgetHealthResponse:
        """
        Check overall budget health for a specific month.

        Args:
            month: Month in YYYY-MM format

        Returns:
            BudgetHealthResponse with health metrics
        """
        # Get month data
        month_detail = ynab_service.get_plan_month(month).data.month

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
         month: str, category_id: Optional[str] = None
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
        transactions_response = ynab_service.get_transactions(
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


