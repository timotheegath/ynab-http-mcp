"""
Data cleaning utilities for YNAB HTTP MCP.

This module provides unified data cleaning functions to simplify
YNAB API response processing and make data agent-friendly.
"""

from typing import Any, Dict, Type, TypeVar, Optional
from datetime import date as datetime_date, datetime as datetime_datetime
from uuid import UUID
import logging
from pydantic import BaseModel, ValidationError
import os
import locale

logger = logging.getLogger(__name__)
T = TypeVar("T", bound=BaseModel)


def clean_ynab_data(data: Any) -> Any:
    """
    Unified data cleaning function for YNAB API responses.

    Performs all necessary data transformations in a single pass:
    - Converts UUID objects to strings
    - Filters out import-related fields
    - Converts date objects to ISO string format
    - Handles nested data structures recursively

    Args:
        data: Raw YNAB API response data (dict, list, or primitive)

    Returns:
        Cleaned data with consistent types suitable for agent consumption
    """
    if isinstance(data, dict):
        return _clean_dict(data)
    elif isinstance(data, list):
        return [_clean_value(item) for item in data]
    else:
        return _clean_value(data)


def _clean_dict(data: Dict[str, Any]) -> Dict[str, Any]:
    """Clean dictionary data by filtering import fields and converting types."""
    cleaned_data = {}

    for key, value in data.items():
        # Filter out import-related fields
        if key in {"import_id", "import_payee_name", "import_payee_name_original"}:
            continue

        # Clean the value recursively
        cleaned_value = _clean_value(value)
        cleaned_data[key] = cleaned_value

    return cleaned_data


def _clean_value(value: Any) -> Any:
    """Clean individual values by converting complex types to simple types."""
    if isinstance(value, UUID):
        # Convert UUID objects to strings
        return str(value)
    elif isinstance(value, datetime_datetime):
        # Convert datetime objects to date string format (YYYY-MM-DD)
        # This ensures compatibility with Pydantic date fields
        return value.date().isoformat()
    elif isinstance(value, datetime_date):
        # Convert date objects to ISO string format (YYYY-MM-DD)
        return value.isoformat()
    elif isinstance(value, dict):
        # Recursively clean nested dictionaries
        return _clean_dict(value)
    elif isinstance(value, list):
        # Recursively clean lists
        return [_clean_value(item) for item in value]
    else:
        # Return primitive types as-is
        return value


def filter_import_fields(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Filter out import-related fields from YNAB data.

    These fields are typically only relevant during import operations
    and should not be exposed through MCP tools.

    Args:
        data: Dictionary containing YNAB data

    Returns:
        Dictionary with import fields removed
    """
    import_fields = {"import_id", "import_payee_name", "import_payee_name_original"}
    return {key: value for key, value in data.items() if key not in import_fields}


def simple_validate(data: Any, model: Type[T]) -> T:
    """
    Simple validation function using basic Pydantic validation.

    Args:
        data: Raw data to validate
        model: Pydantic model class to validate against

    Returns:
        Validated model instance

    Raises:
        ValidationError: If validation fails (using Pydantic's built-in error handling)
    """
    try:
        debug_mode = os.getenv("DEBUG_MODE", "false").lower() in ("true", "1", "yes")
        if debug_mode:
            # logger.debug(f"Validating data against {model.__name__}")
            pass

        return model.model_validate(data)
    except ValidationError as e:
        debug_mode = os.getenv("DEBUG_MODE", "false").lower() in ("true", "1", "yes")
        if debug_mode:
            logger.warning(f"Validation error for {model.__name__}: {str(e)}")
        raise  # Re-raise the Pydantic ValidationError
    except Exception as e:
        debug_mode = os.getenv("DEBUG_MODE", "false").lower() in ("true", "1", "yes")
        if debug_mode:
            logger.error(f"Unexpected error validating {model.__name__}: {str(e)}")
        raise
