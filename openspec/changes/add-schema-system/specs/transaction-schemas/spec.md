## ADDED Requirements

### Requirement: Transaction Response Structure
The system SHALL define a CleanTransaction schema that represents a cleaned transaction response.

#### Scenario: Required fields
- **WHEN** CleanTransaction schema is defined
- **THEN** it SHALL include these required fields:
  - id: str
  - date: datetime.date
  - amount: int
  - memo: Optional[str]
  - cleared: str
  - approved: bool
  - account_id: UUID
  - account_name: str

#### Scenario: Optional fields
- **WHEN** CleanTransaction schema is defined
- **THEN** it SHALL include these optional fields:
  - payee_id: Optional[UUID]
  - payee_name: Optional[str]
  - category_id: Optional[UUID]
  - category_name: Optional[str]
  - transfer_account_id: Optional[UUID]
  - transfer_transaction_id: Optional[str]
  - matched_transaction_id: Optional[str]
  - flag_color: Optional[str]
  - flag_name: Optional[str]
  - debt_transaction_type: Optional[str]
  - amount_formatted: Optional[str]
  - amount_currency: Optional[Union[float, int]]
  - subtransactions: List[dict]

#### Scenario: Excluded fields
- **WHEN** CleanTransaction schema is defined
- **THEN** it SHALL NOT include these fields:
  - import_id
  - import_payee_name
  - import_payee_name_original

### Requirement: Transaction Response Validation
The system SHALL validate transaction responses against the CleanTransaction schema.

#### Scenario: Valid transaction
- **WHEN** get_transactions tool receives valid YNAB transaction data
- **THEN** it SHALL successfully validate and return CleanTransaction objects

#### Scenario: Invalid transaction
- **WHEN** get_transactions tool receives invalid transaction data
- **THEN** it SHALL log validation error and return graceful fallback

#### Scenario: Partial transaction data
- **WHEN** get_transactions tool receives transaction with missing optional fields
- **THEN** it SHALL validate successfully with None values for missing fields

### Requirement: Transactions Response Container
The system SHALL define a TransactionsResponse schema for the complete response structure.

#### Scenario: Response structure
- **WHEN** TransactionsResponse schema is defined
- **THEN** it SHALL include:
  - transactions: List[CleanTransaction]
  - server_knowledge: int

#### Scenario: Response validation
- **WHEN** get_transactions tool is called
- **THEN** the complete response SHALL be validated against TransactionsResponse schema