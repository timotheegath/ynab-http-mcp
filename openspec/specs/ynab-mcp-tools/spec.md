## Requirements

### Requirement: MCP Server Initialization
The system SHALL initialize a FastMCP server with the name "ynab" and register all available tools.

#### Scenario: Server initialization
- **WHEN** the server module is imported and main() is called
- **THEN** a FastMCP server instance is created with name "ynab"
- **AND** all YNAB service tools are registered with the server

### Requirement: Planning Tools Registration
The system SHALL provide MCP tools for budget planning operations.

#### Scenario: Planning tools available
- **WHEN** the planning tools are registered
- **THEN** the following tools are available:
  - `get_plan_month`: Get details of a specific plan month
  - `get_all_plan_months`: Get summary of all plan months

### Requirement: Category Tools Registration
The system SHALL provide MCP tools for category management operations.

#### Scenario: Category tools available
- **WHEN** the category tools are registered
- **THEN** the following tool is available:
  - `get_categories`: Get all categories and their groups

**Note**: The categories functionality has been moved to a resource-based approach. See the Resources spec for current implementation.

### Requirement: Transaction Tools Registration
The system SHALL provide MCP tools for transaction querying operations.

#### Scenario: Transaction tools available
- **WHEN** the transaction tools are registered
- **THEN** the following tool is available:
  - `get_transactions`: Get transactions with flexible filtering options

**Note**: Transaction tools are implemented but currently not registered in the server.

### Requirement: Tool Error Handling
All MCP tools SHALL handle errors gracefully and return appropriate error responses.

#### Scenario: Invalid input handling
- **WHEN** a tool receives invalid input parameters
- **THEN** the tool returns a descriptive error message
- **AND** does not crash the server

#### Scenario: YNAB API error handling
- **WHEN** a YNAB API call fails
- **THEN** the tool returns an appropriate error response
- **AND** logs the error for debugging