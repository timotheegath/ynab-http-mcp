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
