#!/usr/bin/env python3
"""
Test script to verify transaction schema validation works correctly.
"""

import os
import sys
from datetime import date
from uuid import uuid4

# Add project root to path
sys.path.insert(0, '/home/timo/projects/ynab-http-mcp/src')

from ynab_http_mcp.schemas.transactions import CleanTransaction, TransactionsResponse
from ynab_http_mcp.schemas.base import validate_and_clean_data, filter_import_fields


def test_filter_import_fields():
    """Test that import fields are properly filtered."""
    print("Testing filter_import_fields...")
    
    # Sample transaction data with import fields
    raw_data = {
        'id': str(uuid4()),
        'date': '2023-01-15',
        'amount': -50000,
        'memo': 'Test transaction',
        'cleared': 'cleared',
        'approved': True,
        'account_id': str(uuid4()),
        'account_name': 'Checking',
        'import_id': 'import-123',  # Should be filtered
        'import_payee_name': 'Imported Payee',  # Should be filtered
        'import_payee_name_original': 'Original Payee',  # Should be filtered
        'payee_name': 'Grocery Store'
    }
    
    filtered = filter_import_fields(raw_data)
    
    # Verify import fields are removed
    assert 'import_id' not in filtered, "import_id should be filtered"
    assert 'import_payee_name' not in filtered, "import_payee_name should be filtered"
    assert 'import_payee_name_original' not in filtered, "import_payee_name_original should be filtered"
    
    # Verify other fields are preserved
    assert 'id' in filtered, "id should be preserved"
    assert 'payee_name' in filtered, "payee_name should be preserved"
    
    print("✓ filter_import_fields test passed")


def test_clean_transaction_validation():
    """Test CleanTransaction schema validation."""
    print("Testing CleanTransaction validation...")
    
    # Valid transaction data
    valid_data = {
        'id': str(uuid4()),
        'date': '2023-01-15',
        'amount': -50000,
        'memo': 'Grocery shopping',
        'cleared': 'cleared',
        'approved': True,
        'account_id': str(uuid4()),
        'account_name': 'Checking Account',
        'payee_name': 'Supermarket',
        'category_name': 'Groceries'
    }
    
    # Convert date string to date object
    from datetime import datetime
    valid_data['date'] = datetime.strptime(valid_data['date'], '%Y-%m-%d').date()
    valid_data['account_id'] = uuid4()
    
    # Validate and clean
    try:
        cleaned = validate_and_clean_data(CleanTransaction, valid_data, debug_mode=True)
        print(f"✓ Successfully validated transaction: {cleaned.id}")
        
        # Verify the cleaned data has expected fields
        assert hasattr(cleaned, 'id'), "Cleaned transaction should have id"
        assert hasattr(cleaned, 'amount'), "Cleaned transaction should have amount"
        assert cleaned.amount == -50000, "Amount should be preserved"
        
    except Exception as e:
        print(f"✗ Validation failed: {e}")
        raise


def test_transactions_response_validation():
    """Test TransactionsResponse schema validation."""
    print("Testing TransactionsResponse validation...")
    
    # Create a valid response structure
    response_data = {
        'transactions': [],
        'server_knowledge': 123
    }
    
    try:
        validated = validate_and_clean_data(TransactionsResponse, response_data, debug_mode=True)
        print(f"✓ Successfully validated response with server_knowledge: {validated.server_knowledge}")
        
    except Exception as e:
        print(f"✗ Response validation failed: {e}")
        raise


def test_schema_json_generation():
    """Test that JSON schemas can be generated for FastMCP metadata."""
    print("Testing JSON schema generation...")
    
    try:
        transaction_schema = CleanTransaction.model_json_schema()
        response_schema = TransactionsResponse.model_json_schema()
        
        assert 'properties' in transaction_schema, "Transaction schema should have properties"
        assert 'properties' in response_schema, "Response schema should have properties"
        
        # Verify import fields are not in the schema
        transaction_props = transaction_schema['properties']
        assert 'import_id' not in transaction_props, "import_id should not be in schema"
        assert 'import_payee_name' not in transaction_props, "import_payee_name should not be in schema"
        
        print("✓ JSON schema generation test passed")
        
    except Exception as e:
        print(f"✗ Schema generation failed: {e}")
        raise


def main():
    """Run all tests."""
    print("Running transaction schema tests...\n")
    
    try:
        test_filter_import_fields()
        test_clean_transaction_validation()
        test_transactions_response_validation()
        test_schema_json_generation()
        
        print("\n🎉 All tests passed! Transaction schema system is working correctly.")
        return 0
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())