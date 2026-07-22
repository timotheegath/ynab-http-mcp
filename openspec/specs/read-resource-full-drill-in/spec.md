# read-resource-full-drill-in Specification

## Purpose
TBD - created by archiving change apply-lean-full-aggregate-read-convention. Update Purpose after archive.
## Requirements
### Requirement: Every read entity exposes a `*Full` drill-in resource

The system SHALL define a `*Full` Pydantic model for each read entity — `MCPCategoryFull`, `MCPAccountFull`, `MCPTransactionFull`, `CleanPayeeFull`, `PlanMonthFull`, `MonthCategoryFull` — that inherits from the corresponding lean model and adds exactly one new field, `full_details: dict`. The `*Full` model SHALL NOT introduce any other new typed fields. The `full_details` value SHALL be the result of `clean_ynab_data(raw_sdk_object.to_dict())` with the documented transformations: UUID objects become strings; datetime values are truncated to ISO 8601 date strings (the time component is discarded); money values are integer milliunits; YNAB-specific import fields (`import_id`, `import_payee_name`, `import_payee_name_original`) are removed. `full_details` is therefore a *cleaned* dump, not a byte-identical SDK payload — it is suitable for the LLM to read every field the SDK exposes for normal use, but it is not suitable for code that needs SDK-fidelity timestamps or import-pipeline metadata.

#### Scenario: MCPCategoryFull inherits lean fields and adds full_details
- **WHEN** `MCPCategoryFull` is instantiated
- **THEN** it accepts all the fields of `MCPCategory` (id, name, hidden, internal, deleted, formatted budget/activity/balance, lean `MCPCategoryGoal`)
- **AND** it requires one additional field, `full_details: dict`, containing the cleaned raw `ynab.Category` as a dict

#### Scenario: full_details contains every non-import SDK field after cleaning
- **WHEN** a `*Full` model is built from a raw YNAB SDK object
- **THEN** `full_details` equals the result of `clean_ynab_data(raw.to_dict())` for the same raw object
- **AND** the dict contains every field the YNAB SDK exposes for that entity, including fields the lean model drops (e.g. `goal_overall_left`, `goal_under_funded`, `goal_cadence_frequency`, `cleared_balance`, `uncleared_balance`)
- **AND** the dict does NOT contain `import_id`, `import_payee_name`, or `import_payee_name_original` (these are removed by `clean_ynab_data`)
- **AND** any datetime-valued SDK field appears in the dict as a YYYY-MM-DD string (not a full ISO 8601 datetime)

#### Scenario: Full model adds no typed fields beyond full_details
- **WHEN** the `*Full` model is diffed against its lean parent
- **THEN** exactly one new field appears: `full_details`
- **AND** no other typed Pydantic field is added at the Full layer

### Requirement: Each entity exposes a `data://{entity}/{id}/full` drill-in resource

The system SHALL register a FastMCP resource template at `data://{entity}/{id}/full` for each of the five read entities: categories, accounts, payees, transactions, and months. The resource template URI parameter (`{id}` for single-entity entities, `{month_date}` or `{ym}` for months) SHALL match the existing single-entity resource URI pattern. The drill-in resource SHALL return the `*Full` model's JSON representation as a string with MIME type `application/json`.

#### Scenario: Drill-in resource URI is registered
- **WHEN** the server module is imported and `main()` is called
- **THEN** a resource template is registered at `data://categories/{category_id}/full`
- **AND** a resource template is registered at `data://accounts/{account_id}/full`
- **AND** a resource template is registered at `data://payees/{id}/full`
- **AND** a resource template is registered at `data://transactions/{id}/full`
- **AND** a resource template is registered at `data://months/{ym}/full`
- **AND** a resource template is registered at `data://months/{ym}/categories/{category_id}/full` (per-month per-category drill-in for month-sensitive goal fields)
- **AND** each is discoverable via `list_mcp_resource_templates()`

#### Scenario: Drill-in returns the same lean fields as the single-entity endpoint
- **WHEN** the LLM reads `data://categories/{category_id}/full`
- **THEN** the response JSON contains every field present in the lean `data://categories/{category_id}` response
- **AND** the response JSON additionally contains the `full_details` dict
- **AND** the lean fields are not omitted, abbreviated, or rearranged in the Full response

#### Scenario: Transaction drill-in includes embedded subtransactions
- **WHEN** the LLM reads `data://transactions/{id}/full` for a split transaction
- **THEN** the response JSON contains the lean `MCPTransaction` fields (id, date, amount formatted, memo, cleared, approved, etc.)
- **AND** the response JSON contains the `subtransactions` array with each `MCPSubTransaction` carrying the lean `amount` (formatted) — no `milli_amount` field on any subtransaction
- **AND** the response's `full_details` dict contains the raw `ynab.TransactionDetail` including its `subtransactions` array with integer milliunit `amount` per sub
- **AND** the LLM can answer split-transaction questions with a single read, drilling in only when integer arithmetic on a sub-amount is needed

#### Scenario: Drill-in resource validates the same way as the single-entity resource
- **WHEN** the LLM reads a drill-in resource with an invalid UUID or non-existent ID
- **THEN** the resource returns the same error shape the single-entity resource returns for the same input
- **AND** the error is logged via the existing `debug_exception` utility

### Requirement: The lean layer never embeds `full_details`

The system SHALL NOT include `full_details` in any lean model (`MCPCategory`, `MCPAccount`, `MCPTransaction`, `CleanPayee`, `PlanMonth`, `MonthCategory`). The lean layer is the LLM's primary read path; the Full layer is the drill-in. A single MCP response SHALL never carry both shapes inline.

#### Scenario: Lean list response has no full_details field
- **WHEN** the LLM reads `data://categories` (the list)
- **THEN** no `full_details` field appears on any `MCPCategory` instance in the response
- **AND** no `full_details` field appears on any `MCPCategoryGroup` instance in the response
- **AND** the response payload is byte-for-byte the same shape as before the convention was applied (modulo the documented field drops elsewhere in this change)

#### Scenario: Lean single-entity response has no full_details field
- **WHEN** the LLM reads `data://categories/{category_id}` (the single-entity endpoint)
- **THEN** the response JSON does not contain a `full_details` key
- **AND** the LLM is expected to drill into `data://categories/{category_id}/full` to retrieve raw data

### Requirement: `full_details` is a typed `dict`, not a Pydantic model

The system SHALL type `full_details` as `dict` (or `Dict[str, Any]`) on every `*Full` model, NOT as a Pydantic model mirroring the YNAB SDK. The dict's keys and value shapes are not validated at the Pydantic layer; the LLM is expected to navigate the dict by field name.

#### Scenario: full_details is a Pydantic dict field
- **WHEN** `*Full` is imported
- **THEN** the `full_details` field has type `dict` (or `Dict[str, Any]`)
- **AND** no Pydantic model class wraps the cleaned raw output

#### Scenario: JSON serialization of full_details is stable
- **WHEN** `*Full.model_dump_json()` is called
- **THEN** the `full_details` value serializes as a nested JSON object
- **AND** no UUID or datetime field appears as a non-string type in the JSON output
- **AND** no SDK-specific types (e.g. `ynab.HybridDecimal`) leak through

