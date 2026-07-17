"""
Test that all MCP tools can be registered and work with the simplified validation approach.
"""

import os
import sys
sys.path.insert(0, '/home/timo/projects/ynab-http-mcp/src')

from ynab_http_mcp.tools.transactions import register as register_transactions
from ynab_http_mcp.tools.categories import register as register_categories
from ynab_http_mcp.tools.planning import register as register_planning
from ynab_http_mcp.ynab_service import YnabService
from mcp.server.fastmcp import FastMCP


def test_tools_can_be_registered():
    """Test that all tools can be registered without errors."""
    print("Testing tool registration...")
    
    # Set up environment
    os.environ['DEBUG_MODE'] = 'false'
    
    # Create MCP instance
    mcp = FastMCP('test')
    
    # Create service
    service = YnabService()
    
    # Test that all tools can be registered without errors
    try:
        register_transactions(mcp, service)
        print("✓ Transaction tools registered successfully")
        
        register_categories(mcp, service)
        print("✓ Category tools registered successfully")
        
        register_planning(mcp, service)
        print("✓ Planning tools registered successfully")
        
        print("✓ All tools registration test passed")
        return True
        
    except Exception as e:
        print(f"✗ Tool registration failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_tools_use_simplified_validation():
    """Test that tools are using the simplified validation approach."""
    print("Testing that tools use simplified validation...")
    
    # Check that the tools import the simplified validation functions
    try:
        # Check transaction tool imports
        with open('/home/timo/projects/ynab-http-mcp/src/ynab_http_mcp/tools/transactions.py', 'r') as f:
            transaction_content = f.read()
            assert 'clean_ynab_data' in transaction_content, "Transaction tool should use clean_ynab_data"
            assert 'simple_validate' in transaction_content, "Transaction tool should use simple_validate"
            assert 'validate_and_clean_data' not in transaction_content, "Transaction tool should not use old validation"
        
        # Check category tool imports
        with open('/home/timo/projects/ynab-http-mcp/src/ynab_http_mcp/tools/categories.py', 'r') as f:
            category_content = f.read()
            assert 'clean_ynab_data' in category_content, "Category tool should use clean_ynab_data"
            assert 'simple_validate' in category_content, "Category tool should use simple_validate"
            assert 'validate_and_clean_data' not in category_content, "Category tool should not use old validation"
        
        # Check planning tool imports
        with open('/home/timo/projects/ynab-http-mcp/src/ynab_http_mcp/tools/planning.py', 'r') as f:
            planning_content = f.read()
            assert 'simple_validate' in planning_content, "Planning tool should use simple_validate"
            assert 'validate_and_clean_data' not in planning_content, "Planning tool should not use old validation"
        
        print("✓ All tools use simplified validation approach")
        return True
        
    except Exception as e:
        print(f"✗ Validation approach test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_simplified_schemas_exist():
    """Test that simplified schemas exist and are properly registered."""
    print("Testing simplified schemas...")
    
    try:
        from ynab_http_mcp.schemas import registry
        
        # Check that all expected schemas are registered
        registered_schemas = registry.all_schemas()
        
        expected_schemas = [
            'CleanTransaction', 'TransactionsResponse',
            'CleanCategory', 'CategoryGroup', 'CategoriesResponse',
            'MonthCategory', 'PlanMonth', 'PlanMonthResponse',
            'PlanMonthSummary', 'AllPlanMonthsResponse'
        ]
        
        for schema_name in expected_schemas:
            assert schema_name in registered_schemas, f"{schema_name} should be registered"
        
        print(f"✓ All {len(expected_schemas)} simplified schemas are registered")
        return True
        
    except Exception as e:
        print(f"✗ Schema registration test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_clean_ynab_data_functionality():
    """Test that clean_ynab_data function works correctly."""
    print("Testing clean_ynab_data functionality...")
    
    try:
        from ynab_http_mcp.utils.schema_utils import clean_ynab_data
        from datetime import date
        from uuid import UUID
        
        # Test data with complex types
        test_data = {
            'id': UUID('123e4567-e89b-12d3-a456-426614174000'),
            'date': date(2023, 1, 15),
            'amount': -50000,
            'import_id': 'should-be-filtered',
            'name': 'Test Transaction'
        }
        
        # Clean the data
        cleaned = clean_ynab_data(test_data)
        
        # Verify results
        assert cleaned['id'] == '123e4567-e89b-12d3-a456-426614174000', "UUID should be converted to string"
        assert cleaned['date'] == '2023-01-15', "Date should be converted to ISO string"
        assert cleaned['amount'] == -50000, "Primitive types should be preserved"
        assert 'import_id' not in cleaned, "Import fields should be filtered"
        assert cleaned['name'] == 'Test Transaction', "String fields should be preserved"
        
        print("✓ clean_ynab_data functionality test passed")
        return True
        
    except Exception as e:
        print(f"✗ clean_ynab_data test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all tool verification tests."""
    print("Running tool verification tests with simplified validation...")
    print()
    
    tests = [
        test_tools_can_be_registered,
        test_tools_use_simplified_validation,
        test_simplified_schemas_exist,
        test_clean_ynab_data_functionality
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        try:
            if test():
                passed += 1
            print()
        except Exception as e:
            print(f"✗ Test {test.__name__} failed with exception: {e}")
            import traceback
            traceback.print_exc()
            print()
    
    if passed == total:
        print(f"🎉 All {total} tool verification tests passed!")
        print("All MCP tools work correctly with simplified validation approach.")
        return 0
    else:
        print(f"❌ {passed}/{total} tests passed")
        return 1


if __name__ == '__main__':
    sys.exit(main())