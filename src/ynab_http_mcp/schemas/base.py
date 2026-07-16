"""
Base schema utilities and error handling for YNAB HTTP MCP schemas.
"""

from typing import Any, Dict, Type, TypeVar, List
from pydantic import BaseModel, ValidationError, Field
from ynab_http_mcp.debug import debug_exception, debug_json
import logging

logger = logging.getLogger(__name__)

T = TypeVar('T', bound=BaseModel)


class MCPValidationError(Exception):
    """Custom validation error for MCP schema validation failures."""
    
    def __init__(self, model_name: str, raw_data: Any, validation_error: ValidationError):
        self.model_name = model_name
        self.raw_data = raw_data
        self.validation_error = validation_error
        
        # Build detailed error message
        error_details = []
        for error in validation_error.errors():
            field_path = " -> ".join(str(part) for part in error['loc'])
            error_details.append(f"{field_path}: {error['msg']} ({error.get('type', 'unknown')})")
        
        super().__init__(f"Validation failed for {model_name}: " + "; ".join(error_details))


def validate_and_clean_data(
    model: Type[T], 
    raw_data: Any,
    debug_mode: bool = False,
    **validation_kwargs
) -> T:
    """
    Validate raw YNAB data against a Pydantic model and return cleaned data.
    
    Args:
        model: Pydantic model class to validate against
        raw_data: Raw data from YNAB API
        debug_mode: Whether to log debug information
        **validation_kwargs: Additional kwargs for Pydantic validation
        
    Returns:
        Validated and cleaned model instance
        
    Raises:
        MCPValidationError: If validation fails
    """
    try:
        if debug_mode:
            debug_json("Validating raw data", raw_data)
        
        # Perform validation
        cleaned_data = model.model_validate(raw_data, **validation_kwargs)
        
        if debug_mode:
            logger.debug(f"Successfully validated {model.__name__}")
            
        return cleaned_data
        
    except ValidationError as e:
        # Log detailed validation error
        if debug_mode:
            debug_exception(f"Validation error for {model.__name__}: {str(e)}")
        
        # Raise custom error with context
        raise MCPValidationError(model.__name__, raw_data, e) from e
    except Exception as e:
        # Handle unexpected errors
        if debug_mode:
            debug_exception(f"Unexpected error validating {model.__name__}: {str(e)}")
        
        raise MCPValidationError(model.__name__, raw_data, 
                               ValidationError([], [])) from e


def filter_import_fields(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Filter out import-related fields from YNAB data.
    
    These fields are typically only relevant during import operations
    and should not be exposed through MCP tools.
    """
    import_fields = {
        'import_id',
        'import_payee_name', 
        'import_payee_name_original'
    }
    
    return {
        key: value 
        for key, value in data.items() 
        if key not in import_fields
    }


def get_json_schema(model: Type[BaseModel]) -> Dict[str, Any]:
    """
    Get JSON schema representation of a Pydantic model.
    
    This is used for FastMCP metadata integration.
    """
    return model.model_json_schema()


class CleanBaseModel(BaseModel):
    """
    Base model for cleaned YNAB data.
    
    All cleaned models should inherit from this to ensure
    consistent behavior and metadata.
    """
    
    class Config:
        # Allow population from attributes (for compatibility)
        populate_by_name = True
        
        # Use alias generators for field name consistency
        alias_generator = None
        
        # Extra behavior configuration
        extra = 'forbid'  # Prevent extra fields by default
        
        # JSON schema extra configuration
        json_schema_extra = {
            'examples': [
                {
                    'description': 'Example cleaned YNAB data',
                    'value': {}
                }
            ]
        }


def create_response_model(
    data_model: Type[BaseModel],
    response_name: str = 'Response'
) -> Type[BaseModel]:
    """
    Dynamically create a response model that wraps a data model.
    
    This is used to create consistent response structures like:
    {
        'data': CleanTransaction[],
        'meta': {...}
    }
    """
    
    class ResponseModel(BaseModel):
        data: List[BaseModel] = Field(..., description=f"List of {data_model.__name__} items")
        meta: Dict[str, Any] = Field(default_factory=dict, description="Response metadata")
        
        class Config:
            json_schema_extra = {
                'examples': [
                    {
                        'description': f'Successful {response_name}',
                        'value': {
                            'data': [],
                            'meta': {}
                        }
                    }
                ]
            }
    
    ResponseModel.__name__ = f"{data_model.__name__}{response_name}"
    return ResponseModel