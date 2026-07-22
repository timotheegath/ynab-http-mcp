## Purpose

Define the data models for the YNAB HTTP MCP read-side API, including the Lean / Full / Aggregate convention that the read resources follow. Also documents the date, currency, and error-shape conventions that all read resources must honor.
## Requirements
### Requirement: Plan Data Model
The system SHALL use consistent data models for plan-related information.

#### Scenario: Plan summary structure
- **WHEN** plan data is returned
- **THEN** it contains the following fields:
  - id: UUID identifying the plan
  - name: String name of the plan
  - last_modified_on: Datetime of last modification
  - currency_format: Currency formatting information

#### Scenario: Month detail structure
- **WHEN** month detail data is returned
- **THEN** it contains the following fields:
  - month: Date identifier (YYYY-MM-DD format)
  - income: Total income for the month
  - budgeted: Total budgeted amount
  - activity: Total activity
  - to_be_budgeted: Amount remaining to be budgeted
  - categories: Array of category budget information

### Requirement: Category Data Model

The system SHALL use consistent data models for category information.

#### Scenario: Category group structure
- **WHEN** category group data is returned
- **THEN** it contains the following fields:
  - id: UUID identifying the category group
  - name: String name of the category group
  - hidden: Boolean indicating if group is hidden
  - deleted: Boolean indicating if group is deleted
  - categories: Array of category objects

#### Scenario: Category lean read structure
- **WHEN** category data is returned by a lean read resource (`data://categories`, `data://categories/{id}`)
- **THEN** it contains the following fields:
  - id: UUID identifying the category
  - name: String name of the category
  - hidden: Boolean indicating if category is hidden
  - deleted: Boolean indicating if category is deleted
  - internal: Boolean indicating if category is internal
  - category_group_id: UUID of the parent group
  - budgeted_formatted: Optional formatted currency string
  - activity_formatted: Optional formatted currency string
  - balance_formatted: Optional formatted currency string
  - goal: Optional lean `MCPCategoryGoal` (3 raw fields + 2 derived strings)
- **AND** the lean payload does NOT include integer milliunit equivalents of `budgeted`, `activity`, `balance` (those live in `data://categories/{id}/full`)

#### Scenario: Category full read structure
- **WHEN** category data is returned by the drill-in read resource (`data://categories/{id}/full`)
- **THEN** it contains every field of the lean response
- **AND** it additionally contains `full_details: dict` with the cleaned raw `ynab.Category`, including any field the lean layer dropped (e.g. `note`, integer `budgeted`/`activity`/`balance` in milliunits, full `MCPCategoryGoal` raw field set)

### Requirement: Transaction Data Model

The system SHALL use consistent data models for transaction information.

#### Scenario: Transaction lean read structure
- **WHEN** transaction data is returned by a lean read resource (`data://transactions`, `data://transactions/{id}`)
- **THEN** it contains the following fields:
  - id: UUID identifying the transaction
  - date: Date of the transaction (YYYY-MM-DD format)
  - amount: Optional formatted currency string (e.g. "-£45.00")
  - memo: Optional memo text
  - cleared: Cleared status (cleared, uncleared, reconciled)
  - approved: Boolean indicating if transaction is approved
  - flag_color: Optional flag color
  - account_id: UUID of the associated account
  - payee_id: Optional UUID of the associated payee
  - category_id: Optional UUID of the associated category
  - transfer_account_id: Optional UUID for transfers
  - subtransactions: Optional array of lean sub-transactions
- **AND** the lean payload does NOT include `milli_amount` (the integer milliunit representation); that field lives in `data://transactions/{id}/full` under `full_details`

#### Scenario: Transaction full read structure
- **WHEN** transaction data is returned by the drill-in read resource (`data://transactions/{id}/full`)
- **THEN** it contains every field of the lean response
- **AND** it additionally contains `full_details: dict` with the cleaned raw `ynab.TransactionDetail`, including `milli_amount` and any other field the lean layer dropped

#### Scenario: Transaction write request uses integer milliunits
- **WHEN** the LLM submits a `CreateTransactionRequest` or other `MCPRequest`-typed write payload
- **THEN** the `amount` field is an integer in milliunits (1/1000 of the currency unit)
- **AND** the request schema validates that `amount` is an integer
- **AND** this is independent of the read-side `amount` field, which is a formatted string on the lean resource and an integer inside `full_details`

### Requirement: Date Format Validation
The system SHALL validate and standardize date formats.

#### Scenario: ISO date format validation
- **WHEN** a date string is provided
- **THEN** it must conform to ISO 8601 format (YYYY-MM-DD)
- **AND** invalid formats return a validation error

### Requirement: Currency Handling
The system SHALL handle currency values consistently.

#### Scenario: Currency amount format
- **WHEN** currency amounts are processed
- **THEN** they are represented in milliunits (1/1000 of currency unit)
- **AND** converted to appropriate display format when needed

### Requirement: Read-side model convention — Lean / Full / Aggregate

The system SHALL follow the Lean / Full / Aggregate convention for every read resource. Lean models SHALL expose: identity fields (id, name), state booleans (hidden, deleted, internal, approved), minimum-viable raw fields needed for filter / sort / date math, formatted currency strings, and derived plain-English strings for opaque nested concepts. Lean models SHALL NOT expose: integer milliunit fields when a formatted string twin exists, formatted strings whose value is fully captured in a derived string, or any field not needed for the queries above. Every lean model SHALL have a `*Full` sibling that inherits the lean fields and adds `full_details: dict`. Aggregate resources (currently only transactions) SHALL expose pre-computed insights at dedicated URIs, never embedded in lean resources.

#### Scenario: Lean model carries no milliunit twins
- **WHEN** a lean read model is inspected (e.g. `MCPTransaction`, `MCPSubTransaction`, `MCPAccount`, `MCPCategory`, `MonthCategory`)
- **THEN** the model does not include integer milliunit fields (`amount`, `budgeted`, `activity`, `balance`, `goal_target`, `goal_under_funded`, etc.) alongside their formatted string twins
- **AND** milliunit values are reachable only via the `*Full` model's `full_details` dict
- **AND** `MCPSubTransaction.amount` is a formatted string only; its `milli_amount` is dropped from the lean layer and reachable only via `data://transactions/{id}/full` inside `full_details.subtransactions[i].amount` (as an integer)

#### Scenario: Derived string captures redundant raw fields
- **WHEN** a lean model has both a raw field and a derived string for the same concept (e.g. `goal_type` is raw, but `goal_summary` is the derived string that includes the type in prose)
- **THEN** the model retains the raw field only when it is needed for filter, sort, or date math
- **AND** the model does not retain the raw field if it adds no query capability beyond what the derived string provides

#### Scenario: *Full model adds exactly one field
- **WHEN** a `*Full` model is diffed against its lean parent
- **THEN** exactly one new field is added: `full_details: dict`
- **AND** no other typed Pydantic field is added at the Full layer
- **AND** the Full model is suitable for the LLM to do arithmetic or to inspect SDK-fidelity fields without losing the lean fields the LLM is already looking at

### Requirement: Date and currency conventions are stable across the read API

The system SHALL continue to expose dates as ISO 8601 strings (or `datetime.date` objects serialised to ISO), UUIDs as strings, and money as either a YNAB-formatted string (lean) or an integer milliunit (drill-in / write). No new representation types are introduced.

#### Scenario: UUID is a string on every read response
- **WHEN** any lean or full read response is serialised to JSON
- **THEN** every `id`, `*_id`, `category_group_id`, `account_id`, `payee_id`, `transfer_account_id` field is a string in the form `xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx`
- **AND** no UUID object leaks into the JSON

#### Scenario: Date is ISO 8601
- **WHEN** any read response containing a `date` or `goal_target_date` field is serialised
- **THEN** the value is `YYYY-MM-DD` or `YYYY-MM-DDTHH:MM:SS.ffffff+00:00` for datetimes
- **AND** no `datetime` object leaks into the JSON

#### Scenario: Money is string on lean, integer on full
- **WHEN** the same entity's `amount` (or `budgeted` / `activity` / `balance`) is read via lean and via full
- **THEN** the lean response has a formatted string (e.g. `"-£45.00"`)
- **AND** the full response's `full_details` has the same value as an integer in milliunits (e.g. `-45000`)

#### Scenario: Lean resources serialize Optional fields with exclude_none
- **WHEN** a lean read resource is serialised to JSON via `model.model_dump_json(exclude_none=True)`
- **THEN** every field whose value is `None` is omitted from the JSON output
- **AND** no `"field_name": null` appears in the response for a field whose lean value is the default `None`
- **AND** this convention applies to every lean list, single-entity, and embedded resource (e.g. `MCPCategoryGoal` embedded inside `MCPCategory` shall not emit 5 null keys when the category has no goal — it should be `goal: null` or omitted, not 5 null siblings)
- **AND** the Full layer also follows this convention for its lean fields, but the `full_details` dict is serialised as a nested JSON object (the dict itself is never `None`)

### Requirement: Canonical error shape for read resources

The system SHALL return errors from every read resource in a single canonical shape. On error, the response is a JSON object containing `{"error": "<human-readable message>"}` as the top-level shape, with all other resource fields at their zero/empty defaults. On success, the response is the resource's normal typed shape (e.g. `MCPCategories`, `MCPTransaction`, `TransactionInsightsResponse`) and the `error` field, if present on the schema, is `None`. Resources SHALL NOT propagate raw exceptions to the MCP framework; resource functions SHALL catch known failure modes and return the canonical shape.

#### Scenario: Resource error returns canonical shape
- **WHEN** a read resource encounters an error (invalid UUID, YNAB API failure, validation failure, missing parameter)
- **THEN** the response is a top-level JSON object containing `error: str` with a human-readable description
- **AND** every other field on the response model is populated with its zero/empty default (or omitted under `exclude_none=True`)
- **AND** no other error shape is used (no list of error objects, no exception message, no wrapped envelope)

#### Scenario: Successful response omits the error field
- **WHEN** a read resource completes successfully
- **THEN** the response is the resource's normal typed shape
- **AND** the `error` field, if declared on the schema, is `None` (or omitted under `exclude_none=True`)

#### Scenario: Existing tool functions are updated to the canonical shape
- **WHEN** the canonical shape is applied across all read resources
- **THEN** the resource functions in `src/ynab_http_mcp/tools/categories.py`, `accounts.py`, `payees.py`, `transactions.py`, `planning.py` SHALL wrap the call to `ynab_service` in a try/except
- **AND** known failure modes (invalid UUID format, YNAB 4xx/5xx responses, validation errors from `simple_validate` / `clean_ynab_data`) SHALL be caught and converted to the canonical `{"error": str}` shape
- **AND** unknown exceptions SHALL still propagate (defensive default; only known failures get the canonical shape)

