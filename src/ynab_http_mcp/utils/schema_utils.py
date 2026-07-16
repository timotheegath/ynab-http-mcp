from typing import Dict, Any
import copy


def transform_schema(schema: Dict[str, Any]) -> Dict[str, Any]:
    """
    Transform Pydantic schema to FastMCP-compatible format.
    Inlines all $ref references and removes $defs section.
    """
    # Make a deep copy to avoid modifying the original
    schema = copy.deepcopy(schema)
    
    # Store defs for reference resolution
    defs = schema.pop("$defs", {})
    
    def inline_refs(obj: Any) -> Any:
        """Recursively inline $ref references in schema objects."""
        if isinstance(obj, dict):
            if "$ref" in obj:
                # Replace $ref with the actual definition
                ref_key = obj["$ref"].split("/")[-1]
                if ref_key in defs:
                    return inline_refs(defs[ref_key])
                # If ref not found, keep original object
                return obj
            # Process nested objects
            return {k: inline_refs(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [inline_refs(item) for item in obj]
        return obj
    
    # Apply inlining to the entire schema
    return inline_refs(schema)