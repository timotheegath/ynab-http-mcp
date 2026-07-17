#!/usr/bin/env python3
"""
Test script to verify schema metadata is accessible.
"""

import os
import sys
import json

# Add project root to path
sys.path.insert(0, '/home/timo/projects/ynab-http-mcp/src')

from ynab_http_mcp.schemas import registry
from ynab_http_mcp.schemas.transactions import TransactionsResponse
from ynab_http_mcp.schemas.categories import CategoriesResponse
from ynab_http_mcp.schemas.planning import PlanMonthResponse, AllPlanMonthsResponse


def test_schema_registry():
    """Test that schemas are properly registered."""
    print("Testing schema registry...")
    
    # Check that all schemas are registered
    registered_schemas = registry.all_schemas()
    
    expected_schemas = [
        'CleanTransaction',
        'TransactionsResponse', 
        'CleanCategory',
        'CategoryGroup',
        'CategoriesResponse',
        'MonthCategory',
        'PlanMonth',
        'PlanMonthResponse',
        'PlanMonthSummary',
        'AllPlanMonthsResponse'
    ]
    
    for schema_name in expected_schemas:
        assert schema_name in registered_schemas, f"{schema_name} should be registered"
        print(f"✓ {schema_name} is registered")
    
    print("✓ Schema registry test passed")


def test_json_schema_generation():
    """Test that JSON schemas can be generated for FastMCP metadata."""
    print("Testing JSON schema generation...")
    
    schemas_to_test = [
        TransactionsResponse,
        CategoriesResponse,
        PlanMonthResponse,
        AllPlanMonthsResponse
    ]
    
    for schema_class in schemas_to_test:
        json_schema = schema_class.model_json_schema()
        
        # Verify it's valid JSON schema
        assert 'properties' in json_schema, f"{schema_class.__name__} schema should have properties"
        assert 'title' in json_schema, f"{schema_class.__name__} schema should have title"
        
        # Verify it can be serialized to JSON
        json_str = json.dumps(json_schema)
        parsed_back = json.loads(json_str)
        assert parsed_back == json_schema, f"{schema_class.__name__} schema should be JSON serializable"
        
        print(f"✓ {schema_class.__name__} JSON schema is valid")
    
    print("✓ JSON schema generation test passed")


def test_fastmcp_metadata_compatibility():
    """Test that schemas are compatible with FastMCP metadata format."""
    print("Testing FastMCP metadata compatibility...")
    
    # Test that returnSchema annotations would work
    test_annotations = {
        "returnSchema": TransactionsResponse.model_json_schema()
    }
    
    # Verify the annotation contains valid schema
    assert 'returnSchema' in test_annotations
    assert isinstance(test_annotations['returnSchema'], dict)
    assert 'properties' in test_annotations['returnSchema']
    
    print("✓ FastMCP metadata compatibility test passed")


def test_registry_json_schemas():
    """Test that registry can provide JSON schemas for all registered models."""
    print("Testing registry JSON schema generation...")
    
    json_schemas = registry.get_json_schemas()
    
    # Verify we get JSON schemas for all registered models
    assert len(json_schemas) > 0, "Registry should provide JSON schemas"
    
    for schema_name, json_schema in json_schemas.items():
        assert isinstance(json_schema, dict), f"{schema_name} should have dict schema"
        assert 'properties' in json_schema, f"{schema_name} schema should have properties"
        print(f"✓ {schema_name} JSON schema available from registry")
    
    print("✓ Registry JSON schema test passed")


def main():
    """Run all metadata tests."""
    print("Running schema metadata tests...\n")
    
    tests = [
        test_schema_registry,
        test_json_schema_generation,
        test_fastmcp_metadata_compatibility,
        test_registry_json_schemas
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
        print(f"🎉 All {total} schema metadata tests passed!")
        print("Schema metadata is accessible to agents via FastMCP annotations.")
        return 0
    else:
        print(f"❌ {passed}/{total} tests passed")
        return 1


if __name__ == '__main__':
    sys.exit(main())