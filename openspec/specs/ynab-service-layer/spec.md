## Requirements

### Requirement: YNAB Service Initialization
The system SHALL initialize a YnabService instance with proper YNAB API configuration.

#### Scenario: Service initialization with API key
- **WHEN** YnabService is instantiated
- **THEN** it loads the YNAB_API_KEY from environment variables
- **AND** creates a YNAB API configuration with the access token

#### Scenario: Automatic plan selection
- **WHEN** YnabService is initialized without YNAB_PLAN_ID
- **THEN** it automatically selects the most recently modified plan
- **AND** uses that plan for all subsequent API calls

### Requirement: Plan Management
The system SHALL provide methods for retrieving plan information.

#### Scenario: List all plans
- **WHEN** list_plans() is called
- **THEN** it returns a PlanSummaryResponse containing all available plans

#### Scenario: Get specific plan month
- **WHEN** get_plan_month(date) is called with a valid date
- **THEN** it returns the MonthDetail for that specific month

#### Scenario: Get all plan months
- **WHEN** get_all_plan_months() is called
- **THEN** it returns a MonthSummariesResponse containing all months

### Requirement: Category Management
The system SHALL provide methods for retrieving category information.

#### Scenario: Get all categories
- **WHEN** get_categories() is called
- **THEN** it returns a CategoriesResponse containing all category groups and categories

### Requirement: Transaction Querying
The system SHALL provide flexible transaction querying capabilities.

#### Scenario: Get transactions with date filtering
- **WHEN** get_transactions() is called with since_date and until_date parameters
- **THEN** it returns transactions within that date range

#### Scenario: Get transactions by account
- **WHEN** get_transactions() is called with account_id parameter
- **THEN** it returns transactions for that specific account

#### Scenario: Get transactions by month
- **WHEN** get_transactions() is called with month parameter
- **THEN** it returns transactions for that specific month

#### Scenario: Get transactions by type
- **WHEN** get_transactions() is called with type parameter
- **THEN** it returns transactions of the specified type (uncleared, cleared, reconciled)

### Requirement: Error Handling Decorator
The system SHALL provide a decorator for handling YNAB API errors.

#### Scenario: Handle 404 errors gracefully
- **WHEN** a method decorated with @handle_ynab_errors encounters a 404 error
- **AND** expected_404=True
- **THEN** it returns None or an empty response object based on configuration

#### Scenario: Re-raise unexpected errors
- **WHEN** a method decorated with @handle_ynab_errors encounters a non-404 error
- **THEN** it re-raises the original exception