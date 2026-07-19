# YNAB MCP Resources

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
- **AND** the response contains an array of category groups
- **AND** each category group contains its categories

#### Scenario: Categories resource data structure
- **WHEN** the categories resource is accessed
- **THEN** it returns data matching the CategoriesResponse schema:
  ```json
  {
    "category_groups": [
      {
        "id": "string",
        "name": "string",
        "hidden": "boolean",
        "deleted": "boolean",
        "categories": [
          {
            "id": "string",
            "category_group_id": "string",
            "name": "string",
            "hidden": "boolean",
            "deleted": "boolean"
            // ... additional category fields
          }
        ]
      }
    ]
  }
  ```

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