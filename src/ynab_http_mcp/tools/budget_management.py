"""
Budget management tools for YNAB HTTP MCP.
"""

from typing import Optional, Dict, Any, Annotated
from mcp.types import ToolAnnotations
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
from ..schemas.transaction_aggregate import _ynab_format


def register(mcp, ynab_service: YnabService):
    """Register budget management tools with MCP server."""

    @mcp.tool(annotations=ToolAnnotations(destructiveHint=True))
    def assign_budget_to_category(
        request: AssignBudgetCategoryRequest,
    ) -> Dict[str, Any]:
        """Update a month category budget amount."""
        result = ynab_service.update_month_category(
            f"{request.month}-01", request.category_id, request.budgeted_amount
        )
        return {
            "success": True,
            "category": clean_ynab_data(result.data.category.to_dict()),
        }

    @mcp.tool(annotations=ToolAnnotations(destructiveHint=True))
    def update_category_goal_to_recurring(
        request: UpdateCategoryGoalRecurringRequest,
    ) -> Dict[str, Any]:
        """Update a category's goal to a recurring goal."""
        result = ynab_service.update_category(request.to_update_category_request())
        return {
            "success": True,
            "category": clean_ynab_data(result.data.category.to_dict()),
        }

    @mcp.tool(annotations=ToolAnnotations(destructiveHint=True))
    def update_category_goal_to_target_date(
        request: UpdateCategoryTargetDateRequest,
    ) -> Dict[str, Any]:
        """Update a category's goal to set aside until a target date."""
        result = ynab_service.update_category(request.to_update_category_request())
        return {
            "success": True,
            "category": clean_ynab_data(result.data.category.to_dict()),
        }

    @mcp.tool(annotations=ToolAnnotations(destructiveHint=True))
    def update_category_details(
        request: UpdateCategoryDetailsRequest,
    ) -> Dict[str, Any]:
        """Update a category's name, note, or category group assignment."""
        result = ynab_service.update_category(request.to_update_category_request())
        return {
            "success": True,
            "category": clean_ynab_data(result.data.category.to_dict()),
        }

    @mcp.tool(annotations=ToolAnnotations(destructiveHint=True))
    def clear_category_goals(request: ClearCategoryGoalRequest) -> Dict[str, Any]:
        """Clear a category's goal."""
        result = ynab_service.update_category(request.to_update_category_request())
        return {
            "success": True,
            "category": clean_ynab_data(result.data.category.to_dict()),
        }

    @mcp.tool(annotations=ToolAnnotations(readOnlyHint=False))
    def create_transaction(request: CreateTransactionRequest) -> Dict[str, Any]:
        """Create a new transaction."""
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

    @mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
    def check_budget_health(
        month: Annotated[str, "Month YYYY-MM"],
    ) -> BudgetHealthResponse:
        """Check budget health for a month."""
        # Get month data
        month_detail = ynab_service.get_plan_month(month).data.month

        # Calculate health metrics from month detail
        total_budgeted = month_detail.budgeted
        total_activity = month_detail.activity
        to_be_budgeted = month_detail.to_be_budgeted

        # Grab SDK-formatted strings with fallback to _ynab_format
        _template = None
        if month_detail.budgeted_formatted:
            _template = month_detail.budgeted_formatted

        def _fmt(value: int, sdk_fmt: Optional[str]) -> str:
            return sdk_fmt if sdk_fmt else _ynab_format(value, _template)

        total_budgeted_formatted = _fmt(total_budgeted, month_detail.budgeted_formatted)
        total_activity_formatted = _fmt(total_activity, month_detail.activity_formatted)
        to_be_budgeted_formatted = _fmt(
            to_be_budgeted, month_detail.to_be_budgeted_formatted
        )

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
                "budgeted_formatted": _fmt(cat_budgeted, category.budgeted_formatted),
                "activity": cat_activity,
                "activity_formatted": _fmt(cat_activity, category.activity_formatted),
                "balance": cat_balance,
                "balance_formatted": _fmt(cat_balance, category.balance_formatted),
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
            total_budgeted_formatted=total_budgeted_formatted,
            total_activity=total_activity,
            total_activity_formatted=total_activity_formatted,
            to_be_budgeted=to_be_budgeted,
            to_be_budgeted_formatted=to_be_budgeted_formatted,
            category_health=category_health,
            health_percentage=health_percentage,
            is_healthy=health_percentage
            >= 0.8,  # Consider healthy if 80%+ categories are healthy
        )

    @mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
    def get_spending_insights(
        month: Annotated[str, "Month YYYY-MM"],
        category_id: Annotated[Optional[str], "Category UUID"] = None,
    ) -> SpendingInsightsResponse:
        """Get monthly spending insights."""
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

        # Derive format template from the first transaction's amount_formatted
        _template = None
        for txn in transactions:
            if txn.amount_formatted:
                _template = txn.amount_formatted
                break

        # Calculate metrics
        total_spending = sum(t.amount for t in transactions)
        average_transaction = total_spending / len(transactions) if transactions else 0
        transaction_count = len(transactions)

        # Format the average using a deterministic integer milliunit value:
        # round() ties to nearest even, which is deterministic.
        avg_milli = int(round(average_transaction)) if transactions else 0

        total_spending_formatted = (
            _ynab_format(total_spending, _template) if transactions else "$0.00"
        )
        average_transaction_formatted = (
            _ynab_format(avg_milli, _template) if transactions else "$0.00"
        )

        # Get category insights
        category_insights: Dict[str, Any] = {}
        for transaction in transactions:
            cat_id = str(transaction.category_id)
            if cat_id:
                amount = transaction.amount
                if cat_id in category_insights:
                    category_insights[cat_id]["total"] += amount
                    category_insights[cat_id]["count"] += 1
                    category_insights[cat_id]["total_formatted"] = _ynab_format(
                        category_insights[cat_id]["total"], _template
                    )
                else:
                    category_insights[cat_id] = {
                        "total": amount,
                        "total_formatted": _ynab_format(amount, _template),
                        "count": 1,
                        "category_name": transaction.category_name or "Unknown",
                    }

        return SpendingInsightsResponse(
            month=month,
            category_id=category_id,
            total_spending=total_spending,
            total_spending_formatted=total_spending_formatted,
            average_transaction=average_transaction,
            average_transaction_formatted=average_transaction_formatted,
            transaction_count=transaction_count,
            category_insights=category_insights,
        )
