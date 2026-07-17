"""
Base schema utilities for YNAB HTTP MCP schemas.

This module provides core utilities for schema management and metadata.
"""

from typing import Any, Dict, Type, TypeVar
from pydantic import BaseModel
import logging

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)


def get_json_schema(model: Type[BaseModel]) -> Dict[str, Any]:
    """
    Get JSON schema representation of a Pydantic model.

    This is used for FastMCP metadata integration.
    """
    return model.model_json_schema()


def filter_import_fields(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Filter out import-related fields from YNAB data.

    These fields are typically only relevant during import operations
    and should not be exposed through MCP tools.

    Note: This function is kept for backward compatibility but the
    preferred approach is to use clean_ynab_data() which handles
    import field filtering along with other data cleaning.
    """
    import_fields = {"import_id", "import_payee_name", "import_payee_name_original"}
    return {key: value for key, value in data.items() if key not in import_fields}
