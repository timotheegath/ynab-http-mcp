## 1. Infrastructure Setup

- [x] 1.1 Verify Pydantic is available via YNAB SDK dependency
- [x] 1.2 Create schemas module structure: `src/ynab_http_mcp/schemas/`
- [x] 1.3 Create base.py with common utilities and error handling
- [x] 1.4 Create __init__.py for schema registry

## 2. Transaction Schema Implementation

- [x] 2.1 Create schemas/transactions.py with CleanTransaction model
- [x] 2.2 Create schemas/transactions.py with TransactionsResponse model
- [x] 2.3 Update transactions.py tool to use schema validation
- [x] 2.4 Add FastMCP metadata with returnSchema annotation
- [x] 2.5 Test with real YNAB transaction data

## 3. Category Schema Implementation

- [ ] 3.1 Create schemas/categories.py with CleanCategory model
- [ ] 3.2 Create schemas/categories.py with CategoryGroup model
- [ ] 3.3 Create schemas/categories.py with CategoriesResponse model
- [ ] 3.4 Update categories.py tool to use schema validation
- [ ] 3.5 Add FastMCP metadata with returnSchema annotation

## 4. Error Handling Implementation

- [ ] 4.1 Implement graceful validation error handling in base.py
- [ ] 4.2 Integrate debug_exception logging for validation errors
- [ ] 4.3 Add debug_json logging for invalid data in debug mode
- [ ] 4.4 Test error handling with malformed YNAB responses

## 5. FastMCP Metadata Integration

- [ ] 5.1 Verify all tools have proper returnSchema annotations
- [ ] 5.2 Test that schema metadata is accessible to agents
- [ ] 5.3 Verify JSON schema format compatibility

## 6. Testing and Validation

- [ ] 6.1 Run mypy type checking on all schema files
- [ ] 6.2 Run ruff linting and formatting
- [ ] 6.3 Test all MCP tools with real YNAB data
- [ ] 6.4 Verify import fields are filtered from responses
- [ ] 6.5 Test error handling with DEBUG_MODE enabled/disabled

## 7. Documentation

- [ ] 7.1 Add schema documentation to README
- [ ] 7.2 Add examples of schema usage
- [ ] 7.3 Document the schema system architecture