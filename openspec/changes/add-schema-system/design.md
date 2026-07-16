## Context

The current MCP system directly returns YNAB API responses without any intermediate processing or validation. The YNAB Python SDK already uses Pydantic models internally, but we're not leveraging this for our MCP tools. This creates a missed opportunity for type safety, response cleaning, and documentation.

Current data flow:
```
YNAB API → YNAB SDK (Pydantic models) → MCP Tool → Agent (raw response)
```

Desired data flow:
```
YNAB API → YNAB SDK (Pydantic models) → Schema Validation & Cleaning → MCP Tool → Agent (clean, typed response)
```

## Goals / Non-Goals

**Goals:**
- Create a comprehensive schema system for all MCP tools
- Filter out import-related fields from responses (import_id, import_payee_name, import_payee_name_original)
- Provide type safety with mypy and runtime validation
- Generate FastMCP metadata from schemas automatically
- Handle validation errors gracefully with debug logging
- Establish a scalable pattern for future tools

**Non-Goals:**
- Modify the YNAB SDK or its models
- Create a generic schema system for non-YNAB tools
- Implement complex data transformation beyond field filtering
- Add database persistence for schemas

## Decisions

### 1. Use Pydantic for Schema Models
**Decision**: Use Pydantic BaseModel for all schema definitions
**Rationale**: 
- YNAB SDK already uses Pydantic, so we get compatibility
- Built-in validation and serialization
- Type hints work with mypy
- JSON schema generation for FastMCP metadata
- Industry standard for Python data models

**Alternatives considered**:
- TypedDict: Less validation, no serialization helpers
- Dataclasses: No built-in validation
- Custom validation: Reinventing the wheel

### 2. Field Filtering Strategy
**Decision**: Create clean schema models that exclude import fields, rather than filtering at runtime
**Rationale**:
- More explicit and maintainable
- Type safety ensures import fields can't accidentally be included
- Better performance (no runtime filtering)
- Self-documenting schemas

**Implementation**: Define CleanTransaction model without import_* fields

### 3. Error Handling Strategy
**Decision**: Graceful degradation with debug logging
**Rationale**:
- MCP tools should be resilient
- Debug logs help with troubleshooting
- Agents shouldn't see raw validation errors

**Implementation**:
```python
try:
    return CleanTransaction(**raw_data)
except ValidationError as e:
    debug_exception(f"Validation failed for transaction: {e}")
    # Return partial data or fallback response
```

### 4. FastMCP Metadata Integration
**Decision**: Generate metadata from Pydantic models using model_json_schema()
**Rationale**:
- Single source of truth
- Always in sync with actual schemas
- No manual metadata maintenance

**Implementation**:
```python
@mcp.tool(
    annotations={
        "returnSchema": CleanTransaction.model_json_schema(),
        # ... other annotations
    }
)
```

### 5. Schema Organization
**Decision**: Organize schemas by domain in a dedicated schemas module
**Rationale**:
- Clear separation of concerns
- Easy to find and maintain
- Scalable for future tools
- Avoids circular imports

**Structure**:
```
src/ynab_http_mcp/
├── schemas/
│   ├── __init__.py          # Schema registry
│   ├── base.py             # Base models and utilities
│   ├── transactions.py    # Transaction schemas
│   ├── categories.py      # Category schemas
│   └── planning.py        # Planning schemas
```

### 6. Validation Layer Location
**Decision**: Validate in the tool wrapper, not in YnabService
**Rationale**:
- YnabService should remain a thin adapter
- Validation is an MCP concern, not a YNAB SDK concern
- Keeps service layer reusable
- Tool-specific transformations belong in tools

## Risks / Trade-offs

### Performance Impact
**Risk**: Pydantic validation adds overhead to every tool call
**Mitigation**: 
- Pydantic is optimized for performance
- Validation overhead is minimal compared to API calls
- Can be benchmarked and optimized if needed
- Debug mode can be disabled in production

### Schema Maintenance
**Risk**: Schemas need to be updated when YNAB API changes
**Mitigation**:
- Schemas act as translation layer (per requirement #5)
- YNAB API changes are infrequent
- Type mismatches will be caught by validation
- Can add automated tests for schema compatibility

### Breaking Changes
**Risk**: Clean responses might break existing agent expectations
**Mitigation**:
- Import fields are likely unused by agents
- Can document this as a breaking change in changelog
- Agents should be more robust with clean data
- Can add migration guide if needed

### Dependency Bloat
**Risk**: Adding Pydantic increases dependency size
**Mitigation**:
- Pydantic is already a dependency of YNAB SDK
- Minimal size impact
- Industry standard with good maintenance

## Migration Plan

### Phase 1: Infrastructure Setup
1. Add Pydantic to dependencies (already present via YNAB SDK)
2. Create schemas module structure
3. Implement base validation utilities
4. Add debug logging integration

### Phase 2: Transaction Schema Implementation
1. Create CleanTransaction model
2. Update transactions.py tool with validation
3. Add FastMCP metadata
4. Test with real YNAB data

### Phase 3: Rollout to Other Tools
1. Apply same pattern to categories.py
2. Apply to planning.py
3. Create schema for any future tools

### Phase 4: Documentation
1. Add schema documentation for developers
2. Update README with schema information
3. Add examples of schema usage

### Rollback Strategy
- Schema validation is additive, not destructive
- Can disable validation with feature flag if needed
- Original YNAB SDK responses still available
- Can revert to direct .to_dict() calls

## Open Questions

1. **Schema Versioning**: Should we include schema versions in responses for agents?
2. **Partial Validation**: Should we allow partial responses when validation fails, or fail fast?
3. **Performance Monitoring**: Should we add metrics to monitor validation overhead?
4. **Schema Testing**: Should we add automated tests to verify schema compatibility with YNAB API?