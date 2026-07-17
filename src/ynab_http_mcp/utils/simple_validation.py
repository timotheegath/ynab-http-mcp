"""
Simple validation utilities for YNAB HTTP MCP.

This module provides simplified validation functions that
use basic Pydantic validation without custom error handling.
"""

from typing import Any, Type, TypeVar
from pydantic import BaseModel, ValidationError
import logging
import os

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)


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
        debug_mode = os.getenv('DEBUG_MODE', 'false').lower() in ('true', '1', 'yes')
        if debug_mode:
            logger.debug(f"Validating data against {model.__name__}")
            
        return model.model_validate(data)
    except ValidationError as e:
        debug_mode = os.getenv('DEBUG_MODE', 'false').lower() in ('true', '1', 'yes')
        if debug_mode:
            logger.warning(f"Validation error for {model.__name__}: {str(e)}")
        raise  # Re-raise the Pydantic ValidationError
    except Exception as e:
        debug_mode = os.getenv('DEBUG_MODE', 'false').lower() in ('true', '1', 'yes')
        if debug_mode:
            logger.error(f"Unexpected error validating {model.__name__}: {str(e)}")
        raise
