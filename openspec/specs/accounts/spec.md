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

