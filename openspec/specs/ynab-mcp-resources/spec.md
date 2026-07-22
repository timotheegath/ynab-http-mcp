# YNAB MCP Resources

## Purpose

Define the FastMCP `@mcp.resource` endpoints that expose YNAB plan data (accounts, categories, transactions, payees, plan months) to MCP clients as read-only JSON resources. Each resource returns a string payload derived from a `MCPResponse`-shaped Pydantic model so the wire format is consistent and LLM-friendly.
## Requirements
### Requirement: Resource-Based Data Access
The system SHALL provide MCP resources for read-only data access following FastMCP resource patterns.

#### Scenario: Resources initialization
- **WHEN** the server module is imported and main() is called
- **THEN** all YNAB data resources are registered with the server
- **AND** resources follow FastMCP resource return type requirements

### Requirement: Categories Resource

The system SHALL provide an MCP resource for accessing category data.

#### Scenario: Categories resource available
- **WHEN** the categories resource is registered
- **THEN** a resource with URI `data://categories` is available
- **AND** the resource returns JSON data with MIME type `application/json`
- **AND** the response contains a `category_groups` array matching the `MCPCategories` grouped shape

#### Scenario: Categories resource data structure
- **WHEN** the categories resource is accessed
- **THEN** it returns data matching the `MCPCategories` schema
- **AND** the top-level `category_groups` array contains one `MCPCategoryGroup` per non-deleted group (filtered via `MCPCategories.HIDE_DELETED`)
- **AND** each group exposes a nested `categories` array of `MCPCategory` objects, each with formatted currency fields (`budgeted_formatted`, `activity_formatted`, `balance_formatted`) and, when a goal exists, a nested `MCPCategoryGoal` with `goal_summary` and `goal_status` plain-English strings

  ```json
  {
    "category_groups": [
      {
        "id": "string",
        "name": "string",
        "hidden": "boolean",
        "internal": "boolean",
        "deleted": "boolean",
        "categories": [
          {
            "id": "string",
            "category_group_id": "string",
            "name": "string",
            "hidden": "boolean",
            "internal": "boolean",
            "deleted": "boolean",
            "budgeted_formatted": "string",
            "activity_formatted": "string",
            "balance_formatted": "string",
            "goal": {
              "goal_type": "string",
              "goal_summary": "string",
              "goal_status": "string"
            }
          }
        ]
      }
    ]
  }
  ```

#### Scenario: Single-category resource returns a bare category
- **WHEN** the resource at URI `data://categories/{category_id}` is accessed
- **THEN** the response JSON contains a top-level `MCPCategory` (no `category_group` envelope, no `category_groups` array)
- **AND** the single-category endpoint is unchanged by the grouped refactor

### Requirement: Transactions Resource
The system SHALL provide an MCP resource for accessing transaction data with filtering capabilities.

#### Scenario: Transactions resource endpoint exists
- **WHEN** MCP client requests `data://transactions`
- **THEN** the system SHALL return a valid resource response

#### Scenario: Transactions resource supports query parameters
- **WHEN** MCP client requests `data://transactions?since_date=2024-01-01&type=cleared`
- **THEN** the system SHALL process the query parameters and return filtered transactions

#### Scenario: Transactions resource requires mandatory filters
- **WHEN** MCP client requests `data://transactions` with no filters
- **THEN** the system SHALL return an error response with message indicating missing mandatory filters

#### Scenario: Transactions resource accepts date parameters
- **WHEN** MCP client provides `since_date=2024-01-15`
- **THEN** the system SHALL convert it to a datetime object and use it for filtering

#### Scenario: Transactions resource handles invalid dates
- **WHEN** MCP client provides `since_date=invalid-date`
- **THEN** the system SHALL return an error response with message indicating invalid date format

#### Scenario: Transactions resource returns JSON with hints
- **WHEN** MCP client requests valid transaction data
- **THEN** the system SHALL return a JSON string containing `transactions` array, `server_knowledge` field, and `_hints` metadata

#### Scenario: Transactions resource provides field explanations
- **WHEN** MCP client requests transaction data
- **THEN** the system SHALL include a `_hints` object explaining complex fields like `transfer_account_id`, `matched_transaction_id`, etc.

#### Scenario: Transactions resource maintains filter priority
- **WHEN** MCP client provides both `account_id` and `month` parameters
- **THEN** the system SHALL use only the `account_id` filter (as per existing logic)

#### Scenario: Transactions resource handles data validation
- **WHEN** YNAB API returns transaction data that fails validation
- **THEN** the system SHALL skip invalid transactions but continue processing valid ones

### Requirement: Resource Error Handling
All MCP resources SHALL handle errors gracefully and return appropriate responses.

#### Scenario: Data validation errors
- **WHEN** a resource encounters data validation issues
- **THEN** it returns a fallback response with available valid data
- **AND** logs validation errors for debugging

#### Scenario: YNAB API errors
- **WHEN** a YNAB API call fails during resource access
- **THEN** the resource returns an appropriate error response
- **AND** logs the error for debugging

### Requirement: Resource Performance
Resources SHALL be optimized for performance and client compatibility.

#### Scenario: JSON serialization
- **WHEN** a resource returns structured data
- **THEN** it uses efficient JSON serialization
- **AND** returns string content for FastMCP compatibility

#### Scenario: MIME type specification
- **WHEN** a resource is registered
- **THEN** it specifies the appropriate MIME type
- **AND** uses `application/json` for JSON data resources

### Requirement: Drill-in resources follow the `/{id}/full` URI convention

The system SHALL register a FastMCP resource template at `data://{entity}/{id}/full` for each read entity that has a single-entity endpoint: `data://categories/{category_id}/full`, `data://accounts/{account_id}/full`, `data://payees/{id}/full`, `data://transactions/{id}/full`, and `data://months/{ym}/full`. Each drill-in resource returns the corresponding `*Full` Pydantic model as JSON with MIME type `application/json`. The drill-in payload is the lean payload with one additional field, `full_details: dict`, containing the cleaned raw YNAB SDK object for the entity. The drill-in resource SHALL NOT omit, abbreviate, or rearrange any field present in the corresponding single-entity lean endpoint.

#### Scenario: Drill-in resources are discoverable
- **WHEN** an MCP client calls `list_mcp_resource_templates()`
- **THEN** the response includes templates at `data://categories/{category_id}/full`, `data://accounts/{account_id}/full`, `data://payees/{id}/full`, `data://transactions/{id}/full`, `data://months/{ym}/full`
- **AND** each template's description documents that the response includes the lean fields plus `full_details`

#### Scenario: Drill-in response includes all lean fields
- **WHEN** the LLM reads `data://categories/{category_id}/full` for a category with id, name, formatted budget/activity/balance, and a goal
- **THEN** the response JSON contains the lean `MCPCategory` fields (id, category_group_id, name, hidden, internal, deleted, budgeted_formatted, activity_formatted, balance_formatted)
- **AND** the lean `MCPCategoryGoal` is nested under `goal`
- **AND** the response additionally contains a top-level `full_details` field with the cleaned raw `ynab.Category` as a dict

#### Scenario: Drill-in response is bigger than the lean response
- **WHEN** the same entity is fetched via the lean URI and the full URI
- **THEN** the full URI response's JSON length is strictly greater than the lean URI's
- **AND** the difference is accounted for by the added `full_details` field

### Requirement: Transactions aggregate resource is registered

The system SHALL register a FastMCP resource template at `data://transactions/insights` returning a `TransactionInsightsResponse` JSON payload. The resource template SHALL accept optional query parameters `since_date` (ISO 8601, inclusive), `until_date` (ISO 8601, exclusive), and `account_id` (UUID). When no `since_date` and no `until_date` are provided, the server SHALL use the last 3 calendar months as the default window (current month and the previous two). The full behavioural contract is defined in the `transaction-aggregate-resource` capability spec.

#### Scenario: Aggregate resource is discoverable
- **WHEN** an MCP client calls `list_mcp_resource_templates()`
- **THEN** the response includes a template at `data://transactions/insights`
- **AND** the template's description references the default 3-month window and the supported query parameters

#### Scenario: Aggregate resource accepts time window parameters
- **WHEN** the LLM reads `data://transactions/insights?since_date=2024-01-01&until_date=2024-04-01`
- **THEN** the server fetches transactions in that window via `ynab_service.get_transactions(since_date="2024-01-01", until_date="2024-04-01", type="all")`
- **AND** the response's `monthly_buckets` covers 2024-01, 2024-02, 2024-03

#### Scenario: Aggregate resource default window is last 3 months
- **WHEN** the LLM reads `data://transactions/insights` with no parameters and the current date is 2025-03-15
- **THEN** the server fetches transactions from 2024-12-01 through 2025-04-01
- **AND** the response covers exactly 3 calendar months: the current month and the previous two (e.g. on 2025-03-15 the response covers 2025-01, 2025-02, 2025-03) — the exact boundary convention is defined in the `transaction-aggregate-resource` spec
- **AND** `monthly_buckets` contains exactly 3 entries, one per covered month (including the current month, even if partial)

### Requirement: Lean resources never embed `full_details` or aggregate data

The system SHALL NOT include `full_details` or aggregate data on any lean list resource (`data://categories`, `data://accounts`, `data://payees`, `data://transactions`, `data://months`, `data://months/{ym}`, or any per-entity-collection URI). The three layers (Lean / Full / Aggregate) live at distinct URIs and never co-occur in one response payload.

#### Scenario: Lean list responses are unchanged in shape
- **WHEN** the LLM reads `data://categories`, `data://accounts`, `data://payees`, `data://transactions`, or `data://months`
- **THEN** the response contains no `full_details` field anywhere
- **AND** the response contains no `monthly_buckets`, `top_payees`, `top_categories`, or other aggregate fields
- **AND** the response contains no `insights` or `aggregate` sub-object

