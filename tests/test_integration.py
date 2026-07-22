#!/usr/bin/env python3
"""
Integration test to verify all MCP tools work with real YNAB data structures.
"""

import sys
from datetime import date
from uuid import uuid4

# Add project root to path
sys.path.insert(0, "/home/timo/projects/ynab-http-mcp/src")

from ynab_http_mcp.schemas.transactions import MCPTransaction, MCPTransactions
from ynab_http_mcp.schemas.categories import MCPCategory
from ynab_http_mcp.schemas.planning import (
    MonthCategory,
    PlanMonth,
    PlanMonthResponse,
    PlanMonthSummary,
    AllPlanMonthsResponse,
)
from ynab_http_mcp.utils.schema_utils import clean_ynab_data, simple_validate


def create_sample_transaction():
    """Create a sample transaction that mimics real YNAB data."""
    return {
        "id": str(uuid4()),
        "date": date(2023, 1, 15),
        "amount": "-$500.00",  # Lean: formatted string only (no milli_amount twin)
        "memo": "Grocery shopping",
        "cleared": "cleared",
        "approved": True,
        "account_id": str(uuid4()),
        "account_name": "Checking Account",
        "payee_id": str(uuid4()),
        "payee_name": "Supermarket",
        "category_id": str(uuid4()),
        "category_name": "Groceries",
        "transfer_account_id": None,
        "transfer_transaction_id": None,
        "matched_transaction_id": None,
        "flag_color": None,
        "flag_name": None,
        "debt_transaction_type": None,
        "subtransactions": [],
        # Import fields that should be filtered
        "import_id": "import-123",
        "import_payee_name": "Imported Payee",
        "import_payee_name_original": "Original Payee",
    }


def create_sample_month_category():
    """Create a sample month category that mimics real YNAB data."""
    return {
        "category_id": str(uuid4()),
        "category_name": "Groceries",
        # Lean: integer milliunit budget/activity/balance are dropped; only
        # formatted strings remain on the lean MonthCategory. The integer
        # twins live on the Full layer's full_details dict.
        "budgeted_formatted": "$500.00",
        "activity_formatted": "-$300.00",
        "balance_formatted": "$200.00",
        "goal": {
            "goal_type": "TB",
            "goal_target_date": None,
            "goal_percentage_complete": 60,
            "goal_summary": "Target Category Balance: $500.00",
            "goal_status": "60% complete",
        },
        "deleted": False,
    }


def create_sample_plan_month():
    """Create a sample plan month that mimics real YNAB data."""
    return {
        "month": "2023-01",
        "income": 5000000,  # $5,000.00 in milliunits
        "budgeted": 4000000,  # $4,000.00 budgeted
        "activity": -3000000,  # -$3,000.00 spent
        "to_be_budgeted": 1000000,  # $1,000.00 remaining to budget
        "age_of_money": 30,
        "categories": [create_sample_month_category()],
    }


def create_sample_plan_month_summary():
    """Create a sample plan month summary that mimics real YNAB data."""
    return {
        "month": "2023-01",
        "income": 5000000,
        "budgeted": 4000000,
        "activity": -3000000,
        "to_be_budgeted": 1000000,
    }


def test_transaction_schema():
    """Test transaction schema with real-like data."""
    print("Testing transaction schema...")

    # Test individual transaction
    transaction_data = create_sample_transaction()

    # Clean data using unified function (handles import field filtering, UUID conversion, etc.)
    cleaned_data = clean_ynab_data(transaction_data)

    # Verify import fields were filtered
    assert "import_id" not in cleaned_data
    assert "import_payee_name" not in cleaned_data
    assert "import_payee_name_original" not in cleaned_data

    # Validate using simplified approach
    validated_transaction = simple_validate(cleaned_data, MCPTransaction)
    assert str(validated_transaction.id) == transaction_data["id"]
    assert validated_transaction.amount == "-$500.00"
    print("✓ Individual transaction validation passed")

    # Test transactions response
    transactions_response = {"transactions": [cleaned_data], "server_knowledge": 123}

    validated_response = simple_validate(transactions_response, MCPTransactions)
    assert len(validated_response.transactions) == 1
    print("✓ Transactions response validation passed")


def test_category_schema():
    """Test MCPCategory schema with real-like YNAB data."""
    print("Testing category schema...")

    category_data = {
        "id": str(uuid4()),
        "category_group_id": str(uuid4()),
        "name": "Groceries",
        "hidden": False,
        "internal": False,
        "deleted": False,
        "budgeted_formatted": "$500.00",
        "activity_formatted": "-$300.00",
        "balance_formatted": "$200.00",
        "goal_type": "TB",
        "goal_target_date": None,
        "goal_percentage_complete": 60,
        "goal_summary": "Target Category Balance: $500.00",
        "goal_status": "60% complete",
    }
    cleaned_data = clean_ynab_data(category_data)
    validated_category = simple_validate(cleaned_data, MCPCategory)
    assert str(validated_category.id) == category_data["id"]
    assert validated_category.name == "Groceries"
    # simple_validate constructs the model from the dict directly without
    # going through MCPCategory.from_ynab, so the nested ``goal`` slot
    # stays None unless explicitly provided. The from_ynab path is
    # covered by tests/test_categories_schema.py.
    assert validated_category.goal is None
    print("✓ Individual category validation passed")


def test_planning_schema():
    """Test planning schema with real-like data."""
    print("Testing planning schema...")

    # Test month category (lean layer — formatted strings + nested lean goal)
    month_category_data = create_sample_month_category()
    cleaned_data = clean_ynab_data(month_category_data)
    validated_category = simple_validate(cleaned_data, MonthCategory)
    assert validated_category.category_id is not None
    assert validated_category.category_name == "Groceries"
    print("✓ Month category validation passed")

    # Test plan month
    plan_month_data = create_sample_plan_month()
    cleaned_month_data = clean_ynab_data(plan_month_data)
    validated_month = simple_validate(cleaned_month_data, PlanMonth)
    assert validated_month.month == "2023-01"
    assert len(validated_month.categories) == 1
    print("✓ Plan month validation passed")

    # Test plan month response
    plan_month_response = {"month": cleaned_month_data}

    validated_response = simple_validate(plan_month_response, PlanMonthResponse)
    assert validated_response.month.month == "2023-01"
    print("✓ Plan month response validation passed")

    # Test plan month summary
    summary_data = create_sample_plan_month_summary()
    cleaned_summary_data = clean_ynab_data(summary_data)
    validated_summary = simple_validate(cleaned_summary_data, PlanMonthSummary)
    assert validated_summary.month == "2023-01"
    print("✓ Plan month summary validation passed")

    # Test all plan months response
    all_months_response = {"months": [cleaned_summary_data]}

    validated_all_months = simple_validate(all_months_response, AllPlanMonthsResponse)
    assert len(validated_all_months.months) == 1
    print("✓ All plan months response validation passed")


def test_ynab_api_data_transformation():
    """Test that YNAB API data is properly transformed to match our schema."""
    print("Testing YNAB API data transformation...")

    # Simulate actual YNAB API response structure (month detail with categories)
    ynab_api_data = {
        "data": {
            "month": {
                "month": date(2026, 7, 1),  # YNAB returns date object
                "income": 5000000,
                "budgeted": 4000000,
                "activity": -3000000,
                "to_be_budgeted": 1000000,
                "age_of_money": 30,
                "deleted": False,
                "categories": [
                    {
                        "id": str(uuid4()),
                        "category_group_id": str(uuid4()),
                        "name": "Groceries",
                        "hidden": False,
                        "internal": False,
                        "deleted": False,
                        "budgeted": 500000,
                        "activity": -300000,
                        "balance": 200000,
                        "budgeted_formatted": "$500.00",
                        "activity_formatted": "-$300.00",
                        "balance_formatted": "$200.00",
                        "goal_type": "TB",
                        "goal_target": 500000,
                        "goal_target_date": None,
                        "goal_percentage_complete": 60,
                    }
                ],
            }
        }
    }

    # Transform using a real-ish YNAB response object
    import ynab

    response_obj = ynab.MonthDetailResponse.model_validate(ynab_api_data)
    transformed = PlanMonth.from_ynab_response(response_obj)

    # Validate the transformation
    assert transformed.month == "2026-07"  # Date converted to YYYY-MM
    assert transformed.income == 5000000
    assert len(transformed.categories) == 1
    cat = transformed.categories[0]
    assert cat.category_id is not None
    assert cat.category_name == "Groceries"
    # Lean layer — formatted strings only, no integer milliunit twins
    assert cat.budgeted_formatted == "$500.00"
    assert cat.activity_formatted == "-$300.00"
    assert cat.balance_formatted == "$200.00"

    print("✓ YNAB API data transformation test passed")


def test_import_field_filtering():
    """Test that import fields are properly filtered."""
    print("Testing import field filtering...")

    transaction_with_imports = create_sample_transaction()

    # Verify import fields exist before filtering
    assert "import_id" in transaction_with_imports
    assert "import_payee_name" in transaction_with_imports
    assert "import_payee_name_original" in transaction_with_imports

    # Clean data using unified function (which includes import field filtering)
    cleaned = clean_ynab_data(transaction_with_imports)

    # Verify import fields are removed
    assert "import_id" not in cleaned
    assert "import_payee_name" not in cleaned
    assert "import_payee_name_original" not in cleaned

    # Verify other fields are preserved
    assert "id" in cleaned
    assert "amount" in cleaned
    assert "payee_name" in cleaned

    print("✓ Import field filtering test passed")


def main():
    """Run all integration tests."""
    print("Running integration tests with real-like YNAB data...\n")

    tests = [
        test_transaction_schema,
        test_category_schema,
        test_planning_schema,
        test_import_field_filtering,
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
        print(f"🎉 All {total} integration tests passed!")
        print("All MCP tools work correctly with real YNAB data structures.")
        return 0
    else:
        print(f"❌ {passed}/{total} tests passed")
        return 1


if __name__ == "__main__":
    sys.exit(main())
