## ADDED Requirements

### Requirement: Schema Infrastructure
The system SHALL provide a comprehensive schema infrastructure using Pydantic models for all MCP tool responses.

#### Scenario: Schema module structure
- **WHEN** the system is initialized
- **THEN** a schemas module SHALL exist with base models and utilities

#### Scenario: Schema validation
- **WHEN** an MCP tool receives a YNAB API response
- **THEN** the response SHALL be validated against the appropriate schema

#### Scenario: Type safety
- **WHEN** mypy type checking is run
- **THEN** all MCP tool responses SHALL pass type validation

### Requirement: Import Field Filtering
The system SHALL filter out import-related fields from transaction responses.

#### Scenario: Transaction field filtering
- **WHEN** a transaction response is processed
- **THEN** fields starting with "import_" SHALL be excluded from the final response

#### Scenario: Clean transaction schema
- **WHEN** the CleanTransaction schema is defined
- **THEN** it SHALL NOT include import_id, import_payee_name, or import_payee_name_original fields

### Requirement: FastMCP Metadata Integration
The system SHALL automatically generate FastMCP metadata from Pydantic schema definitions.

#### Scenario: Metadata generation
- **WHEN** an MCP tool is registered
- **THEN** its returnSchema annotation SHALL contain the JSON schema from the corresponding Pydantic model

#### Scenario: Agent visibility
- **WHEN** an agent queries tool metadata
- **THEN** the response SHALL include complete schema information

### Requirement: Error Handling
The system SHALL handle validation errors gracefully with appropriate debug logging.

#### Scenario: Validation failure
- **WHEN** schema validation fails
- **THEN** the error SHALL be logged using debug_exception
- **AND** a graceful fallback response SHALL be returned

#### Scenario: Debug logging
- **WHEN** DEBUG_MODE is enabled
- **THEN** validation errors SHALL be logged with full details

#### Scenario: Production resilience
- **WHEN** DEBUG_MODE is disabled
- **THEN** agents SHALL receive clean error responses without stack traces

### Requirement: Transaction Schema
The system SHALL provide a comprehensive schema for transaction responses.

#### Scenario: Transaction fields
- **WHEN** the CleanTransaction schema is defined
- **THEN** it SHALL include all standard transaction fields except import-related ones

#### Scenario: Transaction validation
- **WHEN** the get_transactions tool is called
- **THEN** the response SHALL be validated against CleanTransaction schema

#### Scenario: Transaction metadata
- **WHEN** the get_transactions tool is registered
- **THEN** its FastMCP metadata SHALL include the CleanTransaction schema

### Requirement: Category Schema
The system SHALL provide a comprehensive schema for category responses.

#### Scenario: Category fields
- **WHEN** the CleanCategory schema is defined
- **THEN** it SHALL include all standard category fields

#### Scenario: Category validation
- **WHEN** the get_categories tool is called
- **THEN** the response SHALL be validated against CleanCategory schema

### Requirement: Scalable Pattern
The system SHALL establish a scalable pattern for adding schemas to new tools.

#### Scenario: New tool schema
- **WHEN** a new MCP tool is created
- **THEN** it SHALL follow the established schema pattern

#### Scenario: Schema registry
- **WHEN** multiple schemas are defined
- **THEN** they SHALL be organized in a consistent module structure