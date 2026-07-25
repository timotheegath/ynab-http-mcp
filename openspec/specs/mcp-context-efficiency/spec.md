# mcp-context-efficiency Specification

## Purpose
TBD - created by archiving change optimize-mcp-context-efficiency. Update Purpose after archive.
## Requirements
### Requirement: Compact MCP tool catalog

The system SHALL expose its FastMCP tool definitions in a compact form while preserving the complete callable contract. When all registered tools are serialized from `tools/list` using `model_dump(mode="json", exclude_none=True)` and compact JSON separators, the combined payload SHALL contain no more than 10,000 characters.

#### Scenario: Tool catalog stays within its context budget
- **WHEN** an in-memory MCP client lists all registered tools
- **AND** each tool definition is serialized with the documented compact JSON method
- **THEN** the combined serialized definitions contain at most 10,000 characters
- **AND** the catalog still includes all explicit YNAB tools plus `list_resources` and `read_resource`

#### Scenario: Tool contracts survive description trimming
- **WHEN** the optimized catalog is compared with the pre-change callable contract
- **THEN** tool names, input-field names, required fields, data types, enums, numeric bounds, string bounds, and standard MCP annotations are unchanged
- **AND** no existing tool invocation requires a different argument shape

### Requirement: Concise descriptions retain operational semantics

The system SHALL retain description text only where it helps an agent choose or call a tool correctly. Descriptions SHALL preserve monetary units, accepted date formats and boundary semantics, meaningful `null` behavior, operation-specific effects, and distinctions not represented by structural JSON Schema constraints.

#### Scenario: Monetary mutation inputs remain unambiguous
- **WHEN** an agent inspects a tool input that accepts a YNAB monetary amount
- **THEN** the catalog identifies that amount as integer milliunits
- **AND** structural positivity or non-negativity constraints remain encoded in the schema

#### Scenario: Similar category operations remain distinguishable
- **WHEN** an agent compares recurring-goal, target-date-goal, category-details, and clear-goal tools
- **THEN** each tool has a concise operation-specific purpose
- **AND** its accepted goal fields, required fields, and destructive annotation remain discoverable

#### Scenario: Date filters retain boundary behavior
- **WHEN** a catalog description is the only place an inclusive or exclusive date boundary is expressed
- **THEN** the optimized description retains that boundary behavior and accepted date format

### Requirement: Compact resource catalog

The system SHALL keep the combined native static-resource and resource-template catalog at no more than 6,500 compact JSON characters using the same deterministic serialization method as the tool-catalog measurement.

#### Scenario: Resource catalog stays within its context budget
- **WHEN** an in-memory MCP client lists static resources and resource templates
- **AND** both lists are serialized with `model_dump(mode="json", exclude_none=True)` and compact JSON separators
- **THEN** their combined serialized length is at most 6,500 characters
- **AND** all existing resource URIs and URI templates remain registered

#### Scenario: Repeated examples and convention essays are removed
- **WHEN** resource descriptions are inspected
- **THEN** they use concise summaries rather than repeated multi-line examples or repeated Lean/Full convention explanations
- **AND** query parameters or usage constraints that affect correct reads remain documented

### Requirement: Full drill-ins remain discoverable on demand

The system SHALL keep every existing Full resource registered and discoverable. Each Full-resource description SHALL concisely identify the endpoint as a drill-in, identify the `full_details` field, and state that it is intended for raw SDK-field access, integer milliunit arithmetic, or equivalent SDK-fidelity needs.

#### Scenario: Category Full path remains available
- **WHEN** an agent lists resource templates
- **THEN** `data://categories/{category_id}/full` is present
- **AND** its description directs the agent to use it only when the lean category is insufficient

#### Scenario: All Full entity paths remain available
- **WHEN** an agent lists resource templates
- **THEN** the Full paths for accounts, categories, payees, transactions, months, and month-specific categories remain present
- **AND** each description identifies `full_details` without repeating the complete Lean/Full convention

#### Scenario: Lean remains the primary read path
- **WHEN** both a lean URI and its Full counterpart can answer a request
- **THEN** their descriptions identify the lean resource as the default path and Full as the deeper escape hatch
- **AND** neither resource response shape changes as part of this optimization

### Requirement: Resource access remains portable across MCP clients

The system SHALL retain the `ResourcesAsTools` transform and its `list_resources` and `read_resource` tools so agents without first-class MCP resource support can discover and read every registered resource.

#### Scenario: Tool-only client discovers resources
- **WHEN** a client exposes MCP tools to its agent but does not expose native MCP resources
- **THEN** the agent can call `list_resources` to discover Lean, Full, and Aggregate URIs
- **AND** the agent can call `read_resource` with a discovered URI

#### Scenario: Native-resource client remains compatible
- **WHEN** a client uses native `resources/list`, `resources/templates/list`, and resource reads
- **THEN** the same existing resource registrations remain available
- **AND** the resource gateway does not alter native resource behavior

### Requirement: Standard MCP interoperability

The optimized server SHALL NOT require a custom search/describe/call meta-protocol or vendor-specific deferred-loading metadata for discovery or invocation. Clients MAY apply their own lazy loading or tool search to the standard MCP catalogs.

#### Scenario: Eager client receives a complete compact catalog
- **WHEN** a generic MCP client eagerly loads `tools/list`
- **THEN** it receives the complete callable surface within the tool-catalog budget
- **AND** no vendor-specific discovery step is required before a normal tool call

#### Scenario: Lazy client can defer standard definitions
- **WHEN** Claude, Hermes, or another client performs client-side tool search
- **THEN** it can index and load the same standard tool definitions without server-specific integration

