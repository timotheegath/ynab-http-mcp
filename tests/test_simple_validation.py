"""
Tests for the simplified validation approach.
"""

import pytest
from datetime import date
from uuid import UUID
from ynab_http_mcp.utils.schema_utils import clean_ynab_data, simple_validate
from ynab_http_mcp.schemas.transactions import MCPTransaction


def test_clean_ynab_data_with_uuid_conversion():
    """Test that clean_ynab_data converts UUID objects to strings."""
    data = {
        "id": UUID("123e4567-e89b-12d3-a456-426614174000"),
        "account_id": UUID("a1b2c3d4-e5f6-7890-abcd-ef1234567890"),
        "name": "Test Transaction",
    }

    cleaned = clean_ynab_data(data)

    assert cleaned["id"] == "123e4567-e89b-12d3-a456-426614174000"
    assert cleaned["account_id"] == "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
    assert cleaned["name"] == "Test Transaction"


def test_clean_ynab_data_with_date_conversion():
    """Test that clean_ynab_data converts date objects to ISO strings."""
    data = {"date": date(2023, 1, 15), "name": "Test Transaction"}

    cleaned = clean_ynab_data(data)

    assert cleaned["date"] == "2023-01-15"
    assert cleaned["name"] == "Test Transaction"


def test_clean_ynab_data_with_import_field_filtering():
    """Test that clean_ynab_data filters out import-related fields."""
    data = {
        "id": "test-id",
        "name": "Test Transaction",
        "import_id": "import-123",
        "import_payee_name": "Import Payee",
        "import_payee_name_original": "Original Payee",
    }

    cleaned = clean_ynab_data(data)

    assert "id" in cleaned
    assert "name" in cleaned
    assert "import_id" not in cleaned
    assert "import_payee_name" not in cleaned
    assert "import_payee_name_original" not in cleaned


def test_clean_ynab_data_with_nested_structures():
    """Test that clean_ynab_data handles nested data structures."""
    data = {
        "id": UUID("123e4567-e89b-12d3-a456-426614174000"),
        "date": date(2023, 1, 15),
        "subtransactions": [
            {
                "id": UUID("123e4567-e89b-12d3-a456-426614174001"),
                "amount": 1000,
                "import_id": "should-be-filtered",
            }
        ],
    }

    cleaned = clean_ynab_data(data)

    assert cleaned["id"] == "123e4567-e89b-12d3-a456-426614174000"
    assert cleaned["date"] == "2023-01-15"
    assert len(cleaned["subtransactions"]) == 1
    assert cleaned["subtransactions"][0]["id"] == "123e4567-e89b-12d3-a456-426614174001"
    assert cleaned["subtransactions"][0]["amount"] == 1000
    assert "import_id" not in cleaned["subtransactions"][0]


def test_simple_validate_with_valid_data():
    """Test that simple_validate works with valid data."""
    data = {
        "id": "123e4567-e89b-12d3-a456-426614174000",
        "date": "2023-01-15",
        # Lean: amount is a formatted string; integer milliunit twin is dropped
        # from the lean layer (lives on full_details for the Full layer).
        "amount": "-$50.00",
        "memo": "Grocery shopping",
        "cleared": "cleared",
        "approved": True,
        "account_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
        "account_name": "Checking Account",
        "payee_name": "Supermarket",
        "category_name": "Groceries",
    }

    # This should not raise an exception
    validated = simple_validate(data, MCPTransaction)

    assert str(validated.id) == "123e4567-e89b-12d3-a456-426614174000"
    assert validated.date == date(2023, 1, 15)
    assert validated.amount == "-$50.00"


def test_simple_validate_with_invalid_data():
    """Test that simple_validate raises ValidationError for invalid data."""
    data = {
        "id": "valid-id",
        "date": "2023-01-15",
        "amount": "-$50.00",
        # Missing required fields: memo, cleared, approved, account_id, account_name
    }

    with pytest.raises(Exception):  # Should raise ValidationError
        simple_validate(data, MCPTransaction)


def test_integration_clean_then_validate():
    """Test the full integration: clean YNAB data then validate."""
    # Simulate raw YNAB API data with complex types
    raw_ynab_data = {
        "id": UUID("123e4567-e89b-12d3-a456-426614174000"),
        "date": date(2023, 1, 15),
        # Lean: amount is the formatted string; integer milliunit twin is dropped
        # from the lean layer (lives on full_details for the Full layer).
        "amount": "-$50.00",
        "memo": "Grocery shopping",
        "cleared": "cleared",
        "approved": True,
        "account_id": UUID("a1b2c3d4-e5f6-7890-abcd-ef1234567890"),
        "account_name": "Checking Account",
        "payee_name": "Supermarket",
        "category_name": "Groceries",
        "import_id": "should-be-removed",  # Should be filtered out
        "import_payee_name": "should-also-be-removed",  # Should be filtered out
    }

    # Step 1: Clean the data
    cleaned_data = clean_ynab_data(raw_ynab_data)

    # Verify import fields were removed
    assert "import_id" not in cleaned_data
    assert "import_payee_name" not in cleaned_data

    # Verify types were converted
    assert isinstance(cleaned_data["id"], str)
    assert isinstance(cleaned_data["date"], str)
    assert isinstance(cleaned_data["account_id"], str)

    # Step 2: Validate the cleaned data
    validated = simple_validate(cleaned_data, MCPTransaction)

    # Verify the validation worked
    assert str(validated.id) == "123e4567-e89b-12d3-a456-426614174000"
    assert validated.date == date(2023, 1, 15)
    assert str(validated.account_id) == "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
