"""
Test budget management tools for YNAB HTTP MCP.

This module tests the budget management tools including update operations,
budget health checking, and spending insights.
"""

import os
import sys
import json
from unittest.mock import Mock, patch
import pytest

sys.path.insert(0, "/home/timo/projects/ynab-http-mcp/src")

from ynab_http_mcp.tools.budget_management import BudgetManagementTools
from ynab_http_mcp.schemas.budget_tools import (
    UpdateMonthCategoryRequest,
    CreateTransactionRequest,
    BudgetHealthResponse,
    SpendingInsightsResponse,
)
from ynab_http_mcp.ynab_service import YnabService


def test_update_month_category_tool():
    """Test the update_month_category tool."""
    print("Testing update_month_category tool...")

    # Create mock service
    mock_service = Mock(spec=YnabService)

    # Create mock response
    mock_category_response = Mock()
    mock_category_data = Mock()
    mock_category_data.category = {
        "id": "test-category-id",
        "name": "Test Category",
        "budgeted": 50000,
    }
    mock_category_response.data = mock_category_data

    mock_service.update_month_category.return_value = mock_category_response

    # Create tools instance
    tools = BudgetManagementTools(mock_service)

    # Create test request
    request = UpdateMonthCategoryRequest(budgeted_amount=50000)

    # Call the method
    result = tools.update_month_category(
        month="2024-01", category_id="test-category", request=request
    )

    # Verify the result
    assert result["success"] is True
    assert result["category"]["id"] == "test-category-id"
    assert result["category"]["budgeted"] == 50000

    # Verify the service was called correctly
    mock_service.update_month_category.assert_called_once_with(
        "2024-01-01", "test-category", 50000
    )

    print("✓ update_month_category tool test passed")


def test_create_transaction_tool():
    """Test the create_transaction tool."""
    print("Testing create_transaction tool...")

    # Create mock service
    mock_service = Mock(spec=YnabService)

    # Create mock response
    mock_transaction_response = Mock()
    mock_transaction_data = Mock()
    mock_transaction_data.transaction = {
        "id": "test-transaction-id",
        "account_id": "test-account-id",
        "date": "2024-01-15",
        "amount": -50000,
        "payee_name": "Test Payee",
        "category_name": "Test Category",
        "memo": "Test transaction",
    }
    mock_transaction_response.data = mock_transaction_data

    mock_service.create_transaction.return_value = mock_transaction_response

    # Create tools instance
    tools = BudgetManagementTools(mock_service)

    # Create test request
    request = CreateTransactionRequest(
        account_id="test-account-id",
        date="2024-01-15",
        amount=-50000,
        payee_id=None,
        payee_name="Test Payee",
        category_id="test-category-id",
        memo="Test transaction",
        cleared="cleared",
        approved=True,
        flag_color=None,
    )

    # Call the method
    result = tools.create_transaction(request=request)

    # Verify the result
    assert result["success"] is True
    assert result["transaction"]["id"] == "test-transaction-id"
    assert result["transaction"]["amount"] == -50000

    # Verify the service was called correctly
    mock_service.create_transaction.assert_called_once()

    print("✓ create_transaction tool test passed")


def test_check_budget_health_resource():
    """Test the check_budget_health resource."""
    print("Testing check_budget_health resource...")

    # Create mock service
    mock_service = Mock(spec=YnabService)

    # Create mock month detail response
    mock_month_detail = Mock()
    mock_month_detail.budgeted = 80000
    mock_month_detail.activity = 60000
    mock_month_detail.to_be_budgeted = 20000

    # Create mock categories
    mock_category1 = Mock()
    mock_category1.id = "cat-1"
    mock_category1.name = "Groceries"
    mock_category1.budgeted = 40000
    mock_category1.activity = 30000
    mock_category1.balance = 10000

    mock_category2 = Mock()
    mock_category2.id = "cat-2"
    mock_category2.name = "Dining Out"
    mock_category2.budgeted = 20000
    mock_category2.activity = 15000
    mock_category2.balance = 5000

    mock_category3 = Mock()
    mock_category3.id = "cat-3"
    mock_category3.name = "Entertainment"
    mock_category3.budgeted = 20000
    mock_category3.activity = 15000
    mock_category3.balance = 5000

    # Set up categories as a list that can be iterated
    categories_list = [mock_category1, mock_category2, mock_category3]
    mock_month_detail.categories = categories_list

    mock_service.get_plan_month.return_value = mock_month_detail

    # Create tools instance
    tools = BudgetManagementTools(mock_service)

    # Call the method
    result = tools.check_budget_health(month="2024-01")

    # Verify the result
    assert isinstance(result, BudgetHealthResponse)
    assert result.month == "2024-01"
    assert result.total_budgeted == 80000
    assert result.total_activity == 60000
    assert result.to_be_budgeted == 20000
    assert len(result.category_health) == 3  # Should have 3 categories
    assert result.health_percentage == 1.0  # All categories are healthy
    assert result.is_healthy is True

    # Verify the service was called correctly
    mock_service.get_plan_month.assert_called_once_with("2024-01")

    print("✓ check_budget_health resource test passed")


def test_get_spending_insights_resource():
    """Test the get_spending_insights resource."""
    print("Testing get_spending_insights resource...")

    # Create mock service
    mock_service = Mock(spec=YnabService)

    # Create mock transactions response
    mock_transactions_response = Mock()
    mock_transactions_data = Mock()

    # Create test transactions
    mock_transaction1 = Mock()
    mock_transaction1.amount = -50000
    mock_transaction1.category_id = "category-1"
    mock_transaction1.category_name = "Groceries"

    mock_transaction2 = Mock()
    mock_transaction2.amount = -30000
    mock_transaction2.category_id = "category-1"
    mock_transaction2.category_name = "Groceries"

    mock_transaction3 = Mock()
    mock_transaction3.amount = -20000
    mock_transaction3.category_id = "category-2"
    mock_transaction3.category_name = "Dining Out"

    mock_transactions_data.transactions = [
        mock_transaction1,
        mock_transaction2,
        mock_transaction3,
    ]
    mock_transactions_response.data = mock_transactions_data

    mock_service.get_transactions.return_value = mock_transactions_response

    # Create tools instance
    tools = BudgetManagementTools(mock_service)

    # Call the method
    result = tools.get_spending_insights(month="2024-01")

    # Verify the result
    assert isinstance(result, SpendingInsightsResponse)
    assert result.month == "2024-01"
    assert result.category_id is None
    assert result.total_spending == -100000
    assert result.average_transaction == pytest.approx(-33333.33)
    assert result.transaction_count == 3
    assert len(result.category_insights) == 2
    assert result.category_insights["category-1"]["total"] == -80000
    assert result.category_insights["category-1"]["count"] == 2
    assert result.category_insights["category-2"]["total"] == -20000
    assert result.category_insights["category-2"]["count"] == 1

    print("✓ get_spending_insights resource test passed")


def test_spending_insights_with_category_filter():
    """Test spending insights with category filter."""
    print("Testing get_spending_insights with category filter...")

    # Create mock service
    mock_service = Mock(spec=YnabService)

    # Create mock transactions response
    mock_transactions_response = Mock()
    mock_transactions_data = Mock()

    # Create test transactions - only category-1 since we're filtering
    mock_transaction1 = Mock()
    mock_transaction1.amount = -50000
    mock_transaction1.category_id = "category-1"
    mock_transaction1.category_name = "Groceries"

    mock_transactions_data.transactions = [mock_transaction1]
    mock_transactions_response.data = mock_transactions_data

    mock_service.get_transactions.return_value = mock_transactions_response

    # Create tools instance
    tools = BudgetManagementTools(mock_service)

    # Call the method with category filter
    result = tools.get_spending_insights(month="2024-01", category_id="category-1")

    # Verify the result
    assert isinstance(result, SpendingInsightsResponse)
    assert result.month == "2024-01"
    assert result.category_id == "category-1"
    assert result.total_spending == -50000
    assert result.transaction_count == 1

    print("✓ get_spending_insights with category filter test passed")


def test_budget_health_unhealthy_scenario():
    """Test budget health with unhealthy scenario."""
    print("Testing check_budget_health with unhealthy scenario...")

    # Create mock service
    mock_service = Mock(spec=YnabService)

    # Create mock month detail response with unhealthy metrics
    mock_month_detail = Mock()
    mock_month_detail.budgeted = 120000  # Over-budgeted
    mock_month_detail.activity = 110000
    mock_month_detail.to_be_budgeted = -20000  # Negative

    # Create mock categories - some unhealthy
    mock_category1 = Mock()
    mock_category1.id = "cat-1"
    mock_category1.name = "Groceries"
    mock_category1.budgeted = 40000
    mock_category1.activity = 50000  # Over-spent
    mock_category1.balance = -10000  # Negative balance

    mock_category2 = Mock()
    mock_category2.id = "cat-2"
    mock_category2.name = "Dining Out"
    mock_category2.budgeted = 20000
    mock_category2.activity = 15000  # Healthy
    mock_category2.balance = 5000

    mock_category3 = Mock()
    mock_category3.id = "cat-3"
    mock_category3.name = "Entertainment"
    mock_category3.budgeted = 20000
    mock_category3.activity = 25000  # Over-spent
    mock_category3.balance = -5000  # Negative balance

    # Set up categories as a list that can be iterated
    categories_list = [mock_category1, mock_category2, mock_category3]
    mock_month_detail.categories = categories_list

    mock_service.get_plan_month.return_value = mock_month_detail

    # Create tools instance
    tools = BudgetManagementTools(mock_service)

    # Call the method
    result = tools.check_budget_health(month="2024-01")

    # Verify the result shows unhealthy budget
    assert isinstance(result, BudgetHealthResponse)
    assert len(result.category_health) == 3  # Should have 3 categories
    assert result.health_percentage == pytest.approx(
        0.33, abs=0.01
    )  # Only 1 out of 3 categories is healthy
    assert result.is_healthy is False  # Less than 80% healthy

    print("✓ check_budget_health unhealthy scenario test passed")


def test_error_handling():
    """Test error handling in budget management tools."""
    print("Testing error handling...")

    # Create mock service
    mock_service = Mock(spec=YnabService)

    # Test error in update_month_category
    mock_service.update_month_category.side_effect = ValueError("Invalid category ID")

    tools = BudgetManagementTools(mock_service)

    request = UpdateMonthCategoryRequest(budgeted_amount=50000)

    # This should raise the error from the service
    with pytest.raises(ValueError, match="Invalid category ID"):
        tools.update_month_category(
            month="2024-01",
            category_id="invalid-category",
            request=request,
        )

    print("✓ Error handling test passed")


def main():
    """Run all budget management tests."""
    print("Running budget management tool tests...")
    print()

    tests = [
        test_update_month_category_tool,
        test_create_transaction_tool,
        test_check_budget_health_resource,
        test_get_spending_insights_resource,
        test_spending_insights_with_category_filter,
        test_budget_health_unhealthy_scenario,
        test_error_handling,
    ]

    passed = 0
    total = len(tests)

    for test in tests:
        try:
            test()
            passed += 1
            print()
        except Exception as e:
            print(f"✗ Test {test.__name__} failed: {e}")
            import traceback

            traceback.print_exc()
            print()

    if passed == total:
        print(f"🎉 All {total} budget management tests passed!")
        return 0
    else:
        print(f"❌ {passed}/{total} tests passed")
        return 1


if __name__ == "__main__":
    sys.exit(main())
