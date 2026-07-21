---
name: Ynah HTTP MCP Testing
description: Use this skill when you need to test YNAB HTTP MCP resources and endpoints.
---

# ynab-http-mcp-testing

Use this skill when you need to test YNAB HTTP MCP resources and endpoints.

## Testing Workflow

### 1. Start the Service

```bash
bash scripts/start-ynab-mcp.sh
```

### 2. Verify Service Status

```bash
bash scripts/status-ynab-mcp.sh
```

### 3. Discover Available Resources

```python
# List all available resources
list_mcp_resources()

# List resource templates (parameterized endpoints)
list_mcp_resource_templates()
```

### 4. Test Specific Resources

#### Plan Month Resources

```python
# Get all plan months summary
read_mcp_resource(server="ynab-http-mcp", uri="data://months")

# Get specific month details (YYYY-MM format)
read_mcp_resource(server="ynab-http-mcp", uri="data://months/2024-01")

# Get specific month details (YYYY-MM-DD format)
read_mcp_resource(server="ynab-http-mcp", uri="data://months/2024-01-15")

# Get month category details
read_mcp_resource(server="ynab-http-mcp", uri="data://months/2024-01/categories/{category_id}")
```

#### Account Resources

```python
# Get all accounts
read_mcp_resource(server="ynab-http-mcp", uri="data://accounts")

# Get account transactions
read_mcp_resource(server="ynab-http-mcp", uri="data://accounts/{account_id}/transactions")
```

#### Category Resources

```python
# Get all categories
read_mcp_resource(server="ynab-http-mcp", uri="data://categories")

# Get specific category
read_mcp_resource(server="ynab-http-mcp", uri="data://categories/{category_id}")

# Get category transactions
read_mcp_resource(server="ynab-http-mcp", uri="data://categories/{category_id}/transactions")
```

#### Payee Resources

```python
# Get all payees
read_mcp_resource(server="ynab-http-mcp", uri="data://payees")

# Get specific payee
read_mcp_resource(server="ynab-http-mcp", uri="data://payees/{payee_id}")

# Get payee transactions
read_mcp_resource(server="ynab-http-mcp", uri="data://payees/{payee_id}/transactions")
```

#### Transaction Resources

```python
# Get all transactions
read_mcp_resource(server="ynab-http-mcp", uri="data://transactions")

# Get specific transaction
read_mcp_resource(server="ynab-http-mcp", uri="data://transactions/{transaction_id}")
```

### 5. Debugging Issues

```bash
# Check service logs
tail -50 .ynab_http_mcp.log

# Check for specific errors
grep "Error" .ynab_http_mcp.log

# Check debug output
grep "DEBUG" .ynab_http_mcp.log
```

### 6. Restart After Code Changes

```bash
bash scripts/stop-ynab-mcp.sh && bash scripts/start-ynab-mcp.sh
```

## Common Issues and Fixes

### Date Format Issues

**Symptom**: `ValueError: Invalid date format`

**Fix**: Ensure the service method handles both `YYYY-MM` and `YYYY-MM-DD` formats:

```python
# In ynab_service.py
def get_plan_month(self, date: datetime | str | None = None):
    if date:
        if isinstance(date, str):
            try:
                # Handle both 'YYYY-MM' and 'YYYY-MM-DD' formats
                if len(date) == 7 and date[4] == '-':  # YYYY-MM format
                    date = datetime.fromisoformat(date + '-01')
                else:
                    date = datetime.fromisoformat(date)
            except ValueError as e:
                raise ValueError(f"Invalid date format: {str(e)}") from e
```

### Schema Validation Issues

**Symptom**: `ValidationError: Field required`

**Fix**: Ensure schema methods extract data from nested YNAB API response structure:

```python
# In schemas/planning.py
@staticmethod
def from_ynab_response(ynab_response: ynabPlanMonthResponse):
    data = ynab_response.to_dict()
    
    # Extract from nested structure
    if "data" in data and "month" in data["data"]:
        month_data = data["data"]["month"]
    else:
        month_data = data.get("month", {})
    
    # Process month_data instead of data
```

## Best Practices

1. **Always check service status** before testing
2. **Use MCP resource tools** instead of curl/http requests
3. **Check logs** when errors occur
4. **Restart service** after code changes
5. **Test both date formats** (YYYY-MM and YYYY-MM-DD)
6. **Validate JSON responses** for proper structure
7. **Test edge cases** (invalid dates, missing parameters)

## Example Testing Session

```python
# 1. Start service
bash scripts/start-ynab-mcp.sh

# 2. List available resources
list_mcp_resources()

# 3. Test plan month resources
read_mcp_resource(server="ynab-http-mcp", uri="data://months")
read_mcp_resource(server="ynab-http-mcp", uri="data://months/2024-01")

# 4. Test month category resource
# (replace with actual category ID from previous response)
read_mcp_resource(server="ynab-http-mcp", uri="data://months/2024-01/categories/42c2e872-94ca-4aa4-af62-5394e2574480")

# 5. Check logs if any issues
tail -20 .ynab_http_mcp.log
```
