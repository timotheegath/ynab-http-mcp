# Debugging Guide

This document explains the debugging utilities available in `src/ynab_http_mcp/debug.py` and how to use them effectively.

## Debug Functions Overview

The debug module provides several utility functions for logging and debugging:

1. **`debug_json(label, data)`**
   - **When to use**: For logging structured data (dicts, lists, objects)
   - **Behavior**: Pretty-prints JSON only when DEBUG level is enabled
   - **Example**:

     ```python
     debug_json("API Response", {"status": "success", "data": [1, 2, 3]})
     ```

2. **`debug_response(resp, body_limit=4000)`**
   - **When to use**: For debugging HTTP responses (works with requests/httpx)
   - **Behavior**: Logs method, URL, status, headers, and body
   - **Example**:

     ```python
     response = httpx.get("https://api.example.com/data")
     debug_response(response)
     ```

3. **`debug_exception(message)`**
   - **When to use**: Inside except blocks to log exceptions with traceback
   - **Behavior**: Automatically includes full exception traceback
   - **Example**:

     ```python
     try:
         risky_operation()
     except Exception:
         debug_exception("Failed to perform operation")
     ```

## Environment Variables

Debug behavior is controlled by these environment variables:

1. **`DEBUG_MODE`**: Enables debug mode
   - Truthy values: "1", "true", "yes", "on"
   - When enabled: Uses RichHandler, sets log level to DEBUG

2. **`LOG_LEVEL`**: Explicitly sets log level
   - Overrides debug mode setting
   - Values: DEBUG, INFO, WARNING, ERROR

## Best Practices

1. **Use the right tool**:
   - Structured data → `debug_json()`
   - HTTP responses → `debug_response()`
   - Exceptions → `debug_exception()`
   - Custom logging → `get_logger().debug()`

2. **Debug guards**: All debug functions automatically check if debugging is enabled

3. **Performance**: Expensive operations (JSON serialization) only happen when debug is enabled

4. **Environment**: Set `DEBUG_MODE=true` in development, disable in production

## Example Configuration

```bash
# Enable debug mode
export DEBUG_MODE=true

# Or set explicit log level
export LOG_LEVEL=DEBUG

# In .env file
DEBUG_MODE=true
LOG_LEVEL=DEBUG
```
