# accounts Specification

## Purpose
TBD - created by archiving change add-accounts-resource. Update Purpose after archive.
## Requirements
### Requirement: Accounts Resource Endpoint
The system SHALL provide an MCP resource endpoint that returns all YNAB accounts for the current plan.

#### Scenario: Successful accounts retrieval
- **WHEN** an MCP client requests the accounts resource
- **THEN** the system returns a JSON response containing all accounts with their essential fields

#### Scenario: Error handling for missing API key
- **WHEN** the YNAB_API_KEY environment variable is not set
- **THEN** the system returns an appropriate error response

#### Scenario: Error handling for invalid plan
- **WHEN** the specified plan does not exist
- **THEN** the system handles the 404 error gracefully and returns a fallback response

### Requirement: Account Data Structure
The system SHALL return account data in a simplified, validated format suitable for AI consumption.

#### Scenario: Data cleaning and validation
- **WHEN** raw YNAB account data is received
- **THEN** the system cleans and validates the data using the unified cleaning utilities

#### Scenario: Fallback for validation failures
- **WHEN** account data validation fails
- **THEN** the system provides a fallback response with available valid data

### Requirement: MCP Resource Registration
The system SHALL register the accounts resource with the FastMCP server following the same pattern as other resources.

#### Scenario: Resource availability
- **WHEN** the MCP server starts
- **THEN** the accounts resource is available at the expected URI

#### Scenario: Consistent resource pattern
- **WHEN** the accounts resource is accessed
- **THEN** it follows the same response format and behavior as other resources

### Requirement: Account drill-in resource at `data://accounts/{account_id}/full`

The system SHALL register a FastMCP resource template at `data://accounts/{account_id}/full` that returns an `MCPAccountFull` JSON payload. The `MCPAccountFull` model SHALL inherit from the lean `MCPAccount` and SHALL add exactly one field, `full_details: dict`, containing the cleaned raw `ynab.Account` as a dict. The drill-in response SHALL include every field present in the lean `data://accounts/{account_id}` response plus the `full_details` field. The drill-in resource SHALL NOT be the default single-entity endpoint — the LLM is expected to read the lean endpoint first and drill in only when it needs SDK-fidelity data.

#### Scenario: Account drill-in resource is discoverable
- **WHEN** an MCP client calls `list_mcp_resource_templates()`
- **THEN** the response includes a template at `data://accounts/{account_id}/full`
- **AND** the template's description documents that the response includes lean fields plus `full_details`

#### Scenario: Account drill-in response includes full_details
- **WHEN** the LLM reads `data://accounts/{account_id}/full` for an account that has a `note`, a `direct_import_last_error`, an integer `balance` in milliunits, and a YNAB-side `cleared_balance` / `uncleared_balance` field
- **THEN** the response JSON contains the lean `MCPAccount` fields (id, name, type, on_budget, closed, deleted, formatted balance/cleared_balance/uncleared_balance, transfer_payee_id, last_reconciled_at, direct_import_linked, direct_import_in_error)
- **AND** the response additionally contains a top-level `full_details` field
- **AND** `full_details` includes `note`, integer milliunit fields, and any other fields the lean layer dropped (e.g. `interest_rate`, `available_balance`, `debt_escrow_amounts` if present in the raw response)

#### Scenario: Lean account response is unchanged
- **WHEN** the LLM reads `data://accounts/{account_id}` (the lean endpoint, not the full one)
- **THEN** the response JSON does not contain a `full_details` key
- **AND** the response is byte-for-byte the same shape as before this change

