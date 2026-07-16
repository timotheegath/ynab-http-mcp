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

#### Scenario: Category structure
- **WHEN** category data is returned
- **THEN** it contains the following fields:
  - id: UUID identifying the category
  - name: String name of the category
  - hidden: Boolean indicating if category is hidden
  - deleted: Boolean indicating if category is deleted
  - note: Optional string note
  - budgeted: Amount budgeted for this category
  - activity: Amount of activity in this category
  - balance: Current balance of this category

### Requirement: Transaction Data Model
The system SHALL use consistent data models for transaction information.

#### Scenario: Transaction structure
- **WHEN** transaction data is returned
- **THEN** it contains the following fields:
  - id: UUID identifying the transaction
  - date: Date of the transaction (YYYY-MM-DD format)
  - amount: Transaction amount in milliunits
  - memo: Optional memo text
  - cleared: Cleared status (cleared, uncleared, reconciled)
  - approved: Boolean indicating if transaction is approved
  - flag_color: Optional flag color
  - account_id: UUID of the associated account
  - payee_id: Optional UUID of the associated payee
  - category_id: Optional UUID of the associated category
  - transfer_account_id: Optional UUID for transfers
  - import_id: Optional import identifier

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