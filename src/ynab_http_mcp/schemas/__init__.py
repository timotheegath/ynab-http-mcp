"""
Schema registry and public API for YNAB HTTP MCP schemas.

This module provides:
- Schema registry for all available models
- Public imports for easy access to schemas
- FastMCP metadata integration
"""

from typing import Dict, Type, Optional
from pydantic import BaseModel
from .base import (
    MCPValidationError,
    validate_and_clean_data,
    filter_import_fields,
    get_json_schema,
    CleanBaseModel,
    create_response_model,
)


class SchemaRegistry:
    """
    Central registry for all YNAB HTTP MCP schemas.

    This enables:
    - Discovery of available schemas
    - FastMCP metadata generation
    - Runtime schema validation
    """

    def __init__(self):
        self._schemas: Dict[str, Type[BaseModel]] = {}

    def register(self, name: str, schema: Type[BaseModel]) -> None:
        """Register a schema with the registry."""
        self._schemas[name] = schema

    def get(self, name: str) -> Optional[Type[BaseModel]]:
        """Get a schema by name."""
        return self._schemas.get(name)

    def all_schemas(self) -> Dict[str, Type[BaseModel]]:
        """Get all registered schemas."""
        return dict(self._schemas)

    def get_json_schemas(self) -> Dict[str, Dict]:
        """Get JSON schema representations of all registered schemas."""
        return {name: get_json_schema(schema) for name, schema in self._schemas.items()}


# Global schema registry instance
registry = SchemaRegistry()


# Public API
__all__ = [
    "MCPValidationError",
    "validate_and_clean_data",
    "filter_import_fields",
    "get_json_schema",
    "CleanBaseModel",
    "create_response_model",
    "SchemaRegistry",
    "registry",
]
