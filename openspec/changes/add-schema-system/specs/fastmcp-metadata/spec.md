## ADDED Requirements

### Requirement: FastMCP Schema Metadata
The system SHALL integrate Pydantic schemas with FastMCP tool metadata.

#### Scenario: Metadata generation
- **WHEN** an MCP tool is registered with Pydantic return type
- **THEN** its annotations SHALL include returnSchema with JSON schema

#### Scenario: Transaction metadata
- **WHEN** get_transactions tool is registered
- **THEN** its returnSchema SHALL contain CleanTransaction JSON schema

#### Scenario: Category metadata
- **WHEN** get_categories tool is registered
- **THEN** its returnSchema SHALL contain CleanCategory JSON schema

### Requirement: Metadata Format
The system SHALL generate FastMCP-compatible JSON schema metadata.

#### Scenario: JSON schema format
- **WHEN** Pydantic model_json_schema() is called
- **THEN** it SHALL return a valid JSON Schema draft 7+ compatible object

#### Scenario: Type mapping
- **WHEN** JSON schema is generated
- **THEN** Python types SHALL map correctly to JSON Schema types:
  - str → "string"
  - int → "integer"
  - bool → "boolean"
  - List[T] → "array"
  - Optional[T] → not required
  - UUID → "string" with format: "uuid"

### Requirement: Metadata Accessibility
The system SHALL make schema metadata accessible to agents.

#### Scenario: Agent tool discovery
- **WHEN** an agent queries available tools
- **THEN** each tool's metadata SHALL include complete schema information

#### Scenario: Schema documentation
- **WHEN** schema metadata is generated
- **THEN** it SHALL include field descriptions from docstrings