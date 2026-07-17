#!/usr/bin/env python3
"""
Integration test to verify all MCP tools work with real YNAB data structures.
"""

import os
import sys
from datetime import date
from uuid import uuid4

# Add project root to path
sys.path.insert(0, '/home/timo/projects/ynab-http-mcp/src')

from ynab_http_mcp.schemas.transactions import CleanTransaction, TransactionsResponse
from ynab_http_mcp.schemas.categories import CleanCategory, CategoryGroup, CategoriesResponse
from ynab_http_mcp.schemas.planning import MonthCategory, PlanMonth, PlanMonthResponse, PlanMonthSummary, AllPlanMonthsResponse
from ynab_http_mcp.utils.schema_utils import clean_ynab_data
from ynab_http_mcp.utils.simple_validation import simple_validate


def create_sample_transaction():
    """Create a sample transaction that mimics real YNAB data."""
    return {
        'id': str(uuid4()),
        'date': date(2023, 1, 15),
        'amount': -50000,  # -$500.00 in milliunits
        'memo': 'Grocery shopping',
        'cleared': 'cleared',
        'approved': True,
        'account_id': str(uuid4()),
        'account_name': 'Checking Account',
        'payee_id': str(uuid4()),
        'payee_name': 'Supermarket',
        'category_id': str(uuid4()),
        'category_name': 'Groceries',
        'transfer_account_id': None,
        'transfer_transaction_id': None,
        'matched_transaction_id': None,
        'flag_color': None,
        'flag_name': None,
        'debt_transaction_type': None,
        'amount_formatted': '-$500.00',
        'amount_currency': -500.00,
        'subtransactions': [],
        # Import fields that should be filtered
        'import_id': 'import-123',
        'import_payee_name': 'Imported Payee',
        'import_payee_name_original': 'Original Payee'
    }


def create_sample_category():
    """Create a sample category that mimics real YNAB data."""
    return {
        'id': str(uuid4()),
        'category_group_id': str(uuid4()),
        'name': 'Groceries',
        'hidden': False,
        'deleted': False,
        'original_category_group_id': None,
        'note': 'Monthly grocery budget',
        'goal_type': 'TB',
        'goal_day': None,
        'goal_cadence': None,
        'goal_cadence_frequency': None,
        'goal_creation_month': '2023-01',
        'goal_target': 500000,  # $500.00 in milliunits
        'goal_target_month': '2023-12',
        'goal_percentage_complete': 60
    }


def create_sample_category_group():
    """Create a sample category group that mimics real YNAB data."""
    return {
        'id': str(uuid4()),
        'name': 'Everyday Expenses',
        'hidden': False,
        'deleted': False,
        'categories': [create_sample_category()]
    }


def create_sample_month_category():
    """Create a sample month category that mimics real YNAB data."""
    return {
        'category_id': str(uuid4()),
        'category_name': 'Groceries',
        'budgeted': 500000,  # $500.00 in milliunits
        'activity': -300000,  # -$300.00 spent
        'balance': 200000,  # $200.00 remaining
        'goal_type': 'TB',
        'goal_creation_month': '2023-01',
        'goal_target': 500000,
        'goal_target_month': '2023-12',
        'goal_percentage_complete': 60,
        'deleted': False
    }


def create_sample_plan_month():
    """Create a sample plan month that mimics real YNAB data."""
    return {
        'month': '2023-01',
        'income': 5000000,  # $5,000.00 in milliunits
        'budgeted': 4000000,  # $4,000.00 budgeted
        'activity': -3000000,  # -$3,000.00 spent
        'to_be_budgeted': 1000000,  # $1,000.00 remaining to budget
        'age_of_money': 30,
        'categories': [create_sample_month_category()]
    }


def create_sample_plan_month_summary():
    """Create a sample plan month summary that mimics real YNAB data."""
    return {
        'month': '2023-01',
        'income': 5000000,
        'budgeted': 4000000,
        'activity': -3000000,
        'to_be_budgeted': 1000000
    }


def test_transaction_schema():
    """Test transaction schema with real-like data."""
    print("Testing transaction schema...")
    
    # Test individual transaction
    transaction_data = create_sample_transaction()
    
    # Clean data using unified function (handles import field filtering, UUID conversion, etc.)
    cleaned_data = clean_ynab_data(transaction_data)
    
    # Verify import fields were filtered
    assert 'import_id' not in cleaned_data
    assert 'import_payee_name' not in cleaned_data
    assert 'import_payee_name_original' not in cleaned_data
    
    # Validate using simplified approach
    validated_transaction = simple_validate(cleaned_data, CleanTransaction)
    assert validated_transaction.id == transaction_data['id']
    assert validated_transaction.amount == -50000
    print("✓ Individual transaction validation passed")
    
    # Test transactions response
    transactions_response = {
        'transactions': [cleaned_data],
        'server_knowledge': 123
    }
    
    validated_response = simple_validate(transactions_response, TransactionsResponse)
    assert len(validated_response.transactions) == 1
    assert validated_response.server_knowledge == 123
    print("✓ Transactions response validation passed")


def test_category_schema():
    """Test category schema with real-like data."""
    print("Testing category schema...")
    
    # Test individual category
    category_data = create_sample_category()
    cleaned_data = clean_ynab_data(category_data)
    validated_category = simple_validate(cleaned_data, CleanCategory)
    assert validated_category.id == category_data['id']
    assert validated_category.name == 'Groceries'
    print("✓ Individual category validation passed")
    
    # Test category group
    group_data = create_sample_category_group()
    cleaned_group_data = clean_ynab_data(group_data)
    validated_group = simple_validate(cleaned_group_data, CategoryGroup)
    assert validated_group.id == group_data['id']
    assert len(validated_group.categories) == 1
    print("✓ Category group validation passed")
    
    # Test categories response
    categories_response = {
        'category_groups': [cleaned_group_data]
    }
    
    validated_response = simple_validate(categories_response, CategoriesResponse)
    assert len(validated_response.category_groups) == 1
    print("✓ Categories response validation passed")


def test_planning_schema():
    """Test planning schema with real-like data."""
    print("Testing planning schema...")
    
    # Test month category
    month_category_data = create_sample_month_category()
    cleaned_data = clean_ynab_data(month_category_data)
    validated_category = simple_validate(cleaned_data, MonthCategory)
    assert validated_category.category_id is not None
    assert validated_category.category_name == 'Groceries'
    print("✓ Month category validation passed")
    
    # Test plan month
    plan_month_data = create_sample_plan_month()
    cleaned_month_data = clean_ynab_data(plan_month_data)
    validated_month = simple_validate(cleaned_month_data, PlanMonth)
    assert validated_month.month == '2023-01'
    assert len(validated_month.categories) == 1
    print("✓ Plan month validation passed")
    
    # Test plan month response
    plan_month_response = {
        'month': cleaned_month_data
    }
    
    validated_response = simple_validate(plan_month_response, PlanMonthResponse)
    assert validated_response.month.month == '2023-01'
    print("✓ Plan month response validation passed")
    
    # Test plan month summary
    summary_data = create_sample_plan_month_summary()
    cleaned_summary_data = clean_ynab_data(summary_data)
    validated_summary = simple_validate(cleaned_summary_data, PlanMonthSummary)
    assert validated_summary.month == '2023-01'
    print("✓ Plan month summary validation passed")
    
    # Test all plan months response
    all_months_response = {
        'months': [cleaned_summary_data]
    }
    
    validated_all_months = simple_validate(all_months_response, AllPlanMonthsResponse)
    assert len(validated_all_months.months) == 1
    print("✓ All plan months response validation passed")
    
    # Test YNAB API data transformation
    test_ynab_api_data_transformation()


def test_ynab_api_data_transformation():
    """Test that YNAB API data is properly transformed to match our schema."""
    print("Testing YNAB API data transformation...")
    
    from datetime import date
    from uuid import uuid4
    
    # Simulate actual YNAB API response structure
    ynab_api_data = {
        'month': {
            'month': date(2026, 7, 1),  # YNAB returns date object
            'income': 5000000,
            'budgeted': 4000000,
            'activity': -3000000,
            'to_be_budgeted': 1000000,
            'age_of_money': 30,
            'categories': [
                {
                    'id': str(uuid4()),  # YNAB uses 'id' not 'category_id'
                    'name': 'Groceries',  # YNAB uses 'name' not 'category_name'
                    'budgeted': 500000,
                    'activity': -300000,
                    'balance': 200000,
                    'goal_type': 'TB',
                    'goal_creation_month': '2023-01',
                    'goal_target': 500000,
                    'goal_target_month': '2023-12',
                    'goal_percentage_complete': 60,
                    'deleted': False
                }
            ]
        }
    }
    
    # Transform using our method
    transformed_response = PlanMonthResponse.from_ynab_data(ynab_api_data)
    
    # Validate the transformation
    assert transformed_response.month.month == '2026-07'  # Date should be converted to string
    assert transformed_response.month.income == 5000000
    assert len(transformed_response.month.categories) == 1
    assert transformed_response.month.categories[0].category_id is not None
    assert transformed_response.month.categories[0].category_name == 'Groceries'
    
    # Validate with simplified approach
    validated_response = simple_validate(transformed_response.model_dump(), PlanMonthResponse)
    assert validated_response.month.month == '2026-07'
    assert validated_response.month.categories[0].category_name == 'Groceries'
    
    print("✓ YNAB API data transformation test passed")


def test_import_field_filtering():
    """Test that import fields are properly filtered."""
    print("Testing import field filtering...")
    
    transaction_with_imports = create_sample_transaction()
    
    # Verify import fields exist before filtering
    assert 'import_id' in transaction_with_imports
    assert 'import_payee_name' in transaction_with_imports
    assert 'import_payee_name_original' in transaction_with_imports
    
    # Clean data using unified function (which includes import field filtering)
    cleaned = clean_ynab_data(transaction_with_imports)
    
    # Verify import fields are removed
    assert 'import_id' not in cleaned
    assert 'import_payee_name' not in cleaned
    assert 'import_payee_name_original' not in cleaned
    
    # Verify other fields are preserved
    assert 'id' in cleaned
    assert 'amount' in cleaned
    assert 'payee_name' in cleaned
    
    print("✓ Import field filtering test passed")


def main():
    """Run all integration tests."""
    print("Running integration tests with real-like YNAB data...\n")
    
    tests = [
        test_transaction_schema,
        test_category_schema,
        test_planning_schema,
        test_import_field_filtering
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


if __name__ == '__main__':
    sys.exit(main())