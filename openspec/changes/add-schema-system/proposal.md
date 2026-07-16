## Why

The current MCP system returns raw YNAB API responses directly to agents, which includes unnecessary import-related fields and lacks proper schema documentation. This creates several issues:

1. **Noisy responses**: Agents receive import metadata fields (import_id, import_payee_name, etc.) that are irrelevant for most use cases
2. **No type safety**: No runtime validation or mypy type checking for tool responses
3. **Poor documentation**: No centralized schema definitions for developers or agents
4. **No FastMCP integration**: Schema information isn't available in tool metadata
5. **Fragile error handling**: Invalid API responses aren't gracefully handled

This change establishes a comprehensive schema system that serves all tools, providing clean responses, type safety, and proper documentation.

## What Changes

- Add Pydantic-based schema models for all MCP tools
- Create a schema translation layer that filters import fields and validates responses
- Integrate schemas with FastMCP metadata for agent visibility
- Add graceful error handling with debug logging
- Establish a scalable pattern for future tool schemas

## Capabilities

### New Capabilities
- `schema-system`: Core schema infrastructure with base models and validation
- `transaction-schemas`: Clean transaction response models with import field filtering
- `category-schemas`: Schema definitions for category responses
- `fastmcp-metadata`: Automatic FastMCP schema integration
- `error-handling`: Graceful validation and debugging for invalid responses

### Modified Capabilities
- None (this is a new infrastructure layer, not modifying existing requirements)

## Impact

**Affected Code:**
- `src/ynab_http_mcp/tools/transactions.py` - Add schema validation and filtering
- `src/ynab_http_mcp/tools/categories.py` - Add schema validation
- `src/ynab_http_mcp/tools/planning.py` - Add schema validation
- New: `src/ynab_http_mcp/schemas/` - Schema definitions
- New: `src/ynab_http_mcp/utils/validation.py` - Validation helpers

**Dependencies:**
- Pydantic is already available via YNAB SDK dependency

**APIs:**
- All MCP tool responses will be validated and cleaned
- FastMCP metadata will include schema information

**Systems:**
- Type checking with mypy will be enhanced
- Agent responses will be cleaner and more predictable