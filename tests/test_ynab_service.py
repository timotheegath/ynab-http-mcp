#!/usr/bin/env python3
"""
Unit tests for the YnabService class.
"""

import pytest
from datetime import datetime, timezone
from unittest.mock import Mock, patch, MagicMock
from uuid import UUID
import ynab
from ynab.models.category_response import CategoryResponse
from ynab.models.category_response_data import CategoryResponseData
from ynab.models.category import Category

# Import the class to test
from ynab_http_mcp.ynab_service import YnabService


def test_get_month_category_success():
    """Test get_month_category with valid parameters."""
    # Create a mock category response
    mock_category = Category(
        id=UUID("12345678-1234-5678-1234-567812345678"),
        name="Test Category",
        category_group_id=UUID("87654321-4321-8765-4321-876543218765"),
        budgeted=100000,  # 1000.00 in milliunits
        activity=50000,   # 50.00 in milliunits
        balance=50000,    # 50.00 in milliunits
        hidden=False,
        internal=False,
        deleted=False
    )
    
    mock_response = CategoryResponse(
        data=CategoryResponseData(category=mock_category)
    )
    
    # Mock the YNAB API client and CategoriesApi
    with patch.object(YnabService, '_call_api') as mock_call_api:
        mock_call_api.return_value = mock_response
        
        # Create service instance
        service = YnabService()
        
        # Call the method
        test_date = datetime(2023, 12, 15, 10, 30, 0, tzinfo=timezone.utc)
        result = service.get_month_category(test_date, "test-category-id")
        
        # Verify the call
        assert result == mock_response
        mock_call_api.assert_called_once()
        
        # Check that the call was made with correct parameters
        call_args = mock_call_api.call_args
        assert call_args[0][0] == ynab.CategoriesApi
        
        # Extract the lambda function and call it with a mock API
        lambda_func = call_args[0][1]
        mock_api = MagicMock()
        lambda_func(mock_api)

        # Verify the API call was made correctly
        # YNAB API expects full date format with day=01
        expected_month_str = "2023-12-01"
        mock_api.get_month_category_by_id.assert_called_with(
            str(service.plan_id), expected_month_str, "test-category-id"
        )


def test_get_month_category_invalid_category_id():
    """Test get_month_category with invalid category_id."""
    service = YnabService()
    
    # Test with empty string
    with pytest.raises(ValueError, match="category_id must be a non-empty string"):
        service.get_month_category(datetime(2023, 12, 15), "")
    
    # Test with non-string type
    with pytest.raises(ValueError, match="category_id must be a non-empty string"):
        service.get_month_category(datetime(2023, 12, 15), 123)


def test_get_month_category_invalid_month_date():
    """Test get_month_category with invalid month_date."""
    service = YnabService()
    
    # Test with invalid string format
    with pytest.raises(ValueError, match="Invalid month_date format"):
        service.get_month_category("invalid-date", "test-category-id")
    
    # Test with integer instead of datetime
    with pytest.raises(ValueError, match="month_date must be a datetime object"):
        service.get_month_category(2023, "test-category-id")


def test_get_month_category_api_error():
    """Test get_month_category when YNAB API call fails."""
    service = YnabService()
    
    # Mock the _call_api to raise an exception
    with patch.object(YnabService, '_call_api') as mock_call_api:
        mock_call_api.side_effect = Exception("API connection failed")
        
        # This should raise a RuntimeError
        with pytest.raises(RuntimeError, match="Failed to retrieve month category data"):
            service.get_month_category(datetime(2023, 12, 15), "test-category-id")


def test_get_month_category_month_formatting():
    """Test that month formatting works correctly with both YYYY-MM and YYYY-MM-DD formats."""
    mock_category = Category(
        id=UUID("12345678-1234-5678-1234-567812345678"),
        name="Test Category",
        category_group_id=UUID("87654321-4321-8765-4321-876543218765"),
        budgeted=100000,
        activity=50000,
        balance=50000,
        hidden=False,
        internal=False,
        deleted=False
    )
    
    mock_response = CategoryResponse(
        data=CategoryResponseData(category=mock_category)
    )
    
    with patch.object(YnabService, '_call_api') as mock_call_api:
        mock_call_api.return_value = mock_response
        
        service = YnabService()
        
        # Test with different date formats - all should result in the same month string
        test_dates = [
            "2023-12-01",    # Full date format
            "2023-12-15",    # Full date format with different day
            "2023-12-31",    # Full date format with end of month
            "2023-12",       # Short month format
        ]
        
        for test_date in test_dates:
            service.get_month_category(test_date, "test-category-id")
            
            # Verify the month is always formatted as YYYY-MM
            call_args = mock_call_api.call_args
            lambda_func = call_args[0][1]
            mock_api = MagicMock()
            lambda_func(mock_api)
            
            # Verify the API call was made with correct month format
            call_kwargs = mock_api.get_month_category_by_id.call_args[0]
            
            # Second argument should be the full date string with day=01
            expected_date = "2023-12-01"
            assert call_kwargs[1] == expected_date, f"Expected '{expected_date}' but got '{call_kwargs[1]}' for input '{test_date}'"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])