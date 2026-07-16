#!/usr/bin/env python3
"""
Test script to verify error handling works correctly.
"""

import os
import sys
from datetime import date
from uuid import uuid4

# Add project root to path
sys.path.insert(0, '/home/timo/projects/ynab-http-mcp/src')

from ynab_http_mcp.schemas.transactions import CleanTransaction
from ynab_http_mcp.schemas.base import validate_and_clean_data, MCPValidationError


def test_validation_error_handling():
    """Test that validation errors are handled gracefully."""
    print("Testing validation error handling...")
    
    # Invalid transaction data (missing required fields)
    invalid_data = {
        'id': str(uuid4()),
        # Missing required fields: date, amount, cleared, approved, account_id, account_name
        'memo': 'Invalid transaction'
    }
    
    try:
        # This should raise MCPValidationError
        validated = validate_and_clean_data(CleanTransaction, invalid_data, debug_mode=True)
        print("✗ Expected validation error but none was raised")
        return False
        
    except MCPValidationError as e:
        print(f"✓ Caught expected MCPValidationError: {str(e)[:100]}...")
        
        # Verify error contains useful information
        assert e.model_name == 'CleanTransaction', "Error should mention model name"
        assert e.raw_data == invalid_data, "Error should contain raw data"
        assert str(e.validation_error) != '', "Error should contain validation details"
        
        print("✓ Validation error handling test passed")
        return True
        
    except Exception as e:
        print(f"✗ Unexpected error type: {type(e).__name__}: {e}")
        return False


def test_unexpected_error_handling():
    """Test that unexpected errors are handled gracefully."""
    print("Testing unexpected error handling...")
    
    # Data that will cause an unexpected error (not a validation error)
    problematic_data = {
        'id': str(uuid4()),
        'date': 'invalid-date-string',  # This will cause a parsing error
        'amount': -50000,
        'cleared': 'cleared',
        'approved': True,
        'account_id': str(uuid4()),
        'account_name': 'Checking'
    }
    
    try:
        # This should raise MCPValidationError due to date parsing failure
        validated = validate_and_clean_data(CleanTransaction, problematic_data, debug_mode=True)
        print("✗ Expected validation error but none was raised")
        return False
        
    except MCPValidationError as e:
        print(f"✓ Caught expected MCPValidationError for unexpected error: {str(e)[:100]}...")
        
        # Verify error contains useful information
        assert e.model_name == 'CleanTransaction', "Error should mention model name"
        assert e.raw_data == problematic_data, "Error should contain raw data"
        
        print("✓ Unexpected error handling test passed")
        return True
        
    except Exception as e:
        print(f"✗ Unexpected error type: {type(e).__name__}: {e}")
        return False


def test_successful_validation_with_debug():
    """Test that successful validation works with debug mode."""
    print("Testing successful validation with debug mode...")
    
    # Valid transaction data
    valid_data = {
        'id': str(uuid4()),
        'date': date(2023, 1, 15),
        'amount': -50000,
        'memo': 'Test transaction',
        'cleared': 'cleared',
        'approved': True,
        'account_id': str(uuid4()),
        'account_name': 'Checking'
    }
    
    try:
        # This should succeed
        validated = validate_and_clean_data(CleanTransaction, valid_data, debug_mode=True)
        print(f"✓ Successfully validated transaction with debug mode: {validated.id}")
        return True
        
    except Exception as e:
        print(f"✗ Unexpected error during successful validation: {e}")
        return False


def main():
    """Run all error handling tests."""
    print("Running error handling tests...\n")
    
    tests = [
        test_validation_error_handling,
        test_unexpected_error_handling,
        test_successful_validation_with_debug
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
        print(f"🎉 All {total} error handling tests passed!")
        return 0
    else:
        print(f"❌ {passed}/{total} tests passed")
        return 1


if __name__ == '__main__':
    sys.exit(main())