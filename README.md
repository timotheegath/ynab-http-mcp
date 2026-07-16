# ynab-http-mcp

HTTP Streaming MCP for YNAB capabilities

## Overview

This project provides an HTTP-based Micro Content Provider (MCP) server that enables agents to interact with a user's YNAB (You Need A Budget) budget. The goal is to help users gain insights into their spending habits, optimize their budget planning, and perform bulk operations like cleaning up payee names or categorizing transactions.

## Key Dependencies

- **[ynab-sdk-python](https://github.com/ynab/ynab-sdk-python)**: The official YNAB Python SDK used to interact with the YNAB API.
- **FastMCP**: A lightweight framework for building MCP servers.

## Key Capabilities

### Adding a new transaction

### Getting planning advice based on previous spending trends

### Automatically triage transactions

```plain
Triage all transactions from the last few days. If any doubt on categories, ask me.
```

### Help optimize money assignment

```plain
I am reaching the end of my Eating Out money. Which money could I reassign confidently?
```

### Bulk cleanup operations

- Clean up payee names
- Categorize transactions in bulk
- Identify and merge duplicate payees

## Schema System

The YNAB HTTP MCP includes a comprehensive schema system that provides:

### Type Safety
- All responses are validated against Pydantic models
- Type checking with mypy ensures code reliability
- Runtime validation catches data inconsistencies

### Clean Data
- Import-related fields (`import_id`, `import_payee_name`, `import_payee_name_original`) are automatically filtered
- Consistent response structures across all endpoints
- Graceful error handling for malformed data

### FastMCP Metadata Integration
- Each tool includes `returnSchema` annotations with JSON schema
- Agents can discover response structures programmatically
- Automatic documentation generation

### Available Schemas

#### Transaction Schemas
- `CleanTransaction`: Individual transaction with filtered import fields
- `TransactionsResponse`: Complete transactions response with server knowledge

#### Category Schemas
- `CleanCategory`: Individual category details
- `CategoryGroup`: Group of related categories
- `CategoriesResponse`: Complete categories response

#### Planning Schemas
- `MonthCategory`: Category budget details for a specific month
- `PlanMonth`: Complete month budget details
- `PlanMonthResponse`: Response for get_plan_month tool
- `PlanMonthSummary`: Summary of a plan month
- `AllPlanMonthsResponse`: Response for get_all_plan_months tool

### Error Handling
- Custom `MCPValidationError` for validation failures
- Detailed error messages with field-level information
- Debug logging with `DEBUG_MODE=True`
- Graceful fallbacks for partial data

## Schema System Architecture

```
┌───────────────────────────────────────────────────────────────────────────────┐
│                    YNAB HTTP MCP Schema System Architecture                   │
├───────────────────────────────────────────────────────────────────────────────┤
│                                                                               │
│  ┌─────────────┐       ┌─────────────────┐       ┌─────────────────────────┐  │
│  │  YNAB API    │──────▶│   Pydantic     │──────▶│   MCP Tool Wrappers    │  │
│  │  (Raw Data)  │       │   Schema       │       │   (Validation + Cleaning)│  │
│  └─────────────┘       │   Models        │       └─────────────────────────┘  │
│                       └────────┬────────┘                                   │
│                                │                                            │
│                                ▼                                            │
│                       ┌─────────────────┐                                   │
│                       │  FastMCP        │                                   │
│                       │  Metadata       │                                   │
│                       │  (Auto-generated│                                   │
│                       │   from schemas) │                                   │
│                       └─────────────────┘                                   │
│                                                                               │
│  Key Components:                                                               │
│  • CleanBaseModel: Base class for all cleaned schemas                        │
│  • SchemaRegistry: Central registry for all available schemas                 │
│  • validate_and_clean_data(): Main validation function                        │
│  • filter_import_fields(): Filters out import-related fields                 │
│  • MCPValidationError: Custom error for validation failures                   │
│                                                                               │
│  Benefits:                                                                   │
│  ✅ Clean responses (no import_* fields)                                  │
│  ✅ Type safety with mypy                                                   │
│  ✅ Runtime validation                                                       │
│  ✅ Automatic FastMCP metadata                                              │
│  ✅ Graceful error handling                                                 │
│  ✅ Scalable to all tools                                                   │
│                                                                               │
└───────────────────────────────────────────────────────────────────────────────┘
```

## Schema Usage Examples

### Basic Validation

```python
from ynab_http_mcp.schemas.transactions import CleanTransaction
from ynab_http_mcp.schemas.base import validate_and_clean_data

# Sample transaction data from YNAB API
transaction_data = {
    'id': '123e4567-e89b-12d3-a456-426614174000',
    'date': '2023-01-15',
    'amount': -50000,  # -$500.00 in milliunits
    'memo': 'Grocery shopping',
    'cleared': 'cleared',
    'approved': True,
    'account_id': 'a1b2c3d4-e5f6-7890-abcd-ef1234567890',
    'account_name': 'Checking Account',
    'payee_name': 'Supermarket',
    'category_name': 'Groceries',
    # Import fields that will be automatically filtered
    'import_id': 'import-123',
    'import_payee_name': 'Imported Payee',
    'import_payee_name_original': 'Original Payee'
}

# Validate and clean the transaction
cleaned_transaction = validate_and_clean_data(
    CleanTransaction,
    transaction_data,
    debug_mode=True  # Enable debug logging
)

# Access cleaned data
print(f"Transaction: {cleaned_transaction.payee_name} - {cleaned_transaction.amount_formatted}")
```

### Schema Registry Usage

```python
from ynab_http_mcp.schemas import registry

# Get all registered schemas
all_schemas = registry.all_schemas()

# Get JSON schemas for FastMCP metadata
json_schemas = registry.get_json_schemas()

# Get specific schema by name
transaction_schema = registry.get('CleanTransaction')
```

### Error Handling

```python
from ynab_http_mcp.schemas.base import MCPValidationError

try:
    # This will raise MCPValidationError for invalid data
    cleaned_transaction = validate_and_clean_data(
        CleanTransaction,
        {'id': 'invalid'},  # Missing required fields
        debug_mode=True
    )
except MCPValidationError as e:
    print(f"Validation failed: {e}")
    # Error contains: e.model_name, e.raw_data, e.validation_error
    # Access detailed validation errors
    for error in e.validation_error.errors():
        print(f"Field {error['loc']}: {error['msg']}")
```

### FastMCP Metadata Integration

```python
from ynab_http_mcp.schemas.transactions import TransactionsResponse

# Get JSON schema for FastMCP tool annotations
json_schema = TransactionsResponse.model_json_schema()

# Use in tool registration
@mcp.tool(
    annotations={
        "returnSchema": json_schema,  # Agents can discover this structure
        "title": "Get transactions with flexible filtering.",
        # ... other annotations
    }
)
async def get_transactions(...):
    # ... implementation
    return validated_response.model_dump()
```

## Environment Variables

- `YNAB_API_KEY`: Your YNAB API key (loaded from `.env`)
- `YNAB_PLAN_ID`: Optional. The YNAB plan ID to use. If not set, the server will use the plan that was modified the latest.
- `LOG_LEVEL`: Optional, defaults to "debug" in dev
- `DEBUG_MODE`: Optional, enables debug logging

## Running the server

```bash
# Run the server
uv run ynab-http-mcp
```

## Testing

Test using MCP Inspector:

```bash
# Run the server and point MCP Inspector to it
uv run ynab-http-mcp & npx @modelcontextprotocol/inspector --remote http://127.0.0.1:8000/mcp
```
