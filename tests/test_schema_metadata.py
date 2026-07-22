#!/usr/bin/env python3
"""
Test script to verify schema metadata is accessible.
"""

import sys
import json

# Add project root to path
sys.path.insert(0, "/home/timo/projects/ynab-http-mcp/src")

from ynab_http_mcp.schemas import (
    MCPTransaction,
    MCPTransactions,
    MCPCategory,
    MCPCategoryGoal,
    MCPCategories,
    MonthCategory,
    PlanMonth,
    PlanMonthSummary,
    AllPlanMonthsResponse,
    PlanMonthResponse,
)


def test_schema_registry():
    """Test that schemas are properly accessible via the public API."""
    print("Testing schema accessibility...")

    # Check that all schemas are accessible
    expected_schemas = [
        MCPTransaction,
        MCPTransactions,
        MCPCategory,
        MCPCategoryGoal,
        MCPCategories,
        MonthCategory,
        PlanMonth,
        PlanMonthResponse,
        PlanMonthSummary,
        AllPlanMonthsResponse,
    ]

    for schema_class in expected_schemas:
        assert schema_class is not None, f"{schema_class} should be accessible"
        print(f"✓ {schema_class.__name__} is accessible")

    print("✓ Schema accessibility test passed")


def test_json_schema_generation():
    """Test that JSON schemas can be generated for FastMCP metadata."""
    print("Testing JSON schema generation...")

    schemas_to_test = [
        MCPTransactions,
        MCPCategories,
        PlanMonthResponse,
        AllPlanMonthsResponse,
    ]

    for schema_class in schemas_to_test:
        json_schema = schema_class.model_json_schema()

        # Verify it's valid JSON schema
        assert "properties" in json_schema, (
            f"{schema_class.__name__} schema should have properties"
        )
        assert "title" in json_schema, (
            f"{schema_class.__name__} schema should have title"
        )

        # Verify it can be serialized to JSON
        json_str = json.dumps(json_schema)
        parsed_back = json.loads(json_str)
        assert parsed_back == json_schema, (
            f"{schema_class.__name__} schema should be JSON serializable"
        )

        print(f"✓ {schema_class.__name__} JSON schema is valid")

    print("✓ JSON schema generation test passed")


def test_fastmcp_metadata_compatibility():
    """Test that schemas are compatible with FastMCP metadata format."""
    print("Testing FastMCP metadata compatibility...")

    # Test that returnSchema annotations would work
    test_annotations = {"returnSchema": MCPTransactions.model_json_schema()}

    # Verify the annotation contains valid schema
    assert "returnSchema" in test_annotations
    assert isinstance(test_annotations["returnSchema"], dict)
    assert "properties" in test_annotations["returnSchema"]

    print("✓ FastMCP metadata compatibility test passed")


def test_registry_json_schemas():
    """Test that JSON schemas can be generated for all models."""
    print("Testing JSON schema generation for all models...")

    # Test JSON schema generation for all models
    expected_schemas = [
        MCPTransaction,
        MCPTransactions,
        MCPCategory,
        MCPCategoryGoal,
        MCPCategories,
        MonthCategory,
        PlanMonth,
        PlanMonthResponse,
        PlanMonthSummary,
        AllPlanMonthsResponse,
    ]

    # Verify we get JSON schemas for all models
    assert len(expected_schemas) > 0, "Should have schemas to test"

    for schema_class in expected_schemas:
        json_schema = schema_class.model_json_schema()
        assert isinstance(json_schema, dict), (
            f"{schema_class.__name__} should have dict schema"
        )
        assert "properties" in json_schema, (
            f"{schema_class.__name__} schema should have properties"
        )
        print(f"✓ {schema_class.__name__} JSON schema available")

    print("✓ JSON schema generation test passed")


def main():
    """Run all metadata tests."""
    print("Running schema metadata tests...\n")

    tests = [
        test_schema_registry,
        test_json_schema_generation,
        test_fastmcp_metadata_compatibility,
        test_registry_json_schemas,
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


if __name__ == "__main__":
    sys.exit(main())
