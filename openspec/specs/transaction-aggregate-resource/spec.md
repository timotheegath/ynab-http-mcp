# transaction-aggregate-resource Specification

## Purpose
TBD - created by archiving change apply-lean-full-aggregate-read-convention. Update Purpose after archive.
## Requirements
### Requirement: `data://transactions/insights` aggregate resource is registered

The system SHALL register a FastMCP resource template at `data://transactions/insights` that returns a `TransactionInsightsResponse` JSON payload with MIME type `application/json`. The resource accepts three optional query parameters: `since_date` (ISO 8601, inclusive), `until_date` (ISO 8601, exclusive), and `account_id` (UUID). The resource SHALL be discoverable via `list_mcp_resources()` and `list_mcp_resource_templates()`.

#### Scenario: Resource is registered on server start
- **WHEN** the server module is imported and `main()` is called
- **THEN** `list_mcp_resource_templates()` returns a template with URI pattern `data://transactions/insights`
- **AND** the template's documentation describes the time-window parameters

#### Scenario: Default time window is last 3 calendar months
- **WHEN** the LLM reads `data://transactions/insights` with no `since_date` or `until_date`
- **THEN** the server computes `since_date` as the first day of (current month − 2 months)
- **AND** `until_date` is the first day of the month after the current month
- **AND** the response covers exactly 3 calendar months, including the current month and the previous two

#### Scenario: Custom time window is honoured
- **WHEN** the LLM reads `data://transactions/insights?since_date=2024-01-01&until_date=2024-04-01`
- **THEN** the response's `monthly_buckets` contain entries for 2024-01, 2024-02, and 2024-03 only
- **AND** `period_start == "2024-01-01"` and `period_end == "2024-04-01"` (or the last day of the prior month — whichever convention is documented)

#### Scenario: account_id filter scopes the aggregate
- **WHEN** the LLM reads `data://transactions/insights?account_id=...`
- **THEN** the response's totals, top payees, top categories, and `monthly_buckets` reflect only transactions on that account
- **AND** `top_payees` and `top_categories` do not include entries from other accounts

#### Scenario: Invalid dates return an error response
- **WHEN** the LLM reads `data://transactions/insights?since_date=not-a-date`
- **THEN** the response contains a JSON object with an `error` key
- **AND** the error message indicates the invalid date format
- **AND** the server logs the error via the existing `debug_exception` utility

### Requirement: `TransactionInsightsResponse` includes monthly buckets, totals, top-N, and trend

The system SHALL return a `TransactionInsightsResponse` containing:
- `period_start: str` — ISO date of the first day of the analysis window
- `period_end: str` — ISO date of the day after the last day of the analysis window
- `monthly_buckets: List[MonthlyTransactionBucket]` — one bucket per calendar month in the window (zero-filled if no transactions)
- `total_inflow_formatted: str` — sum of positive `amount` over the window, YNAB-formatted
- `total_outflow_formatted: str` — sum of negative `amount` over the window, YNAB-formatted (negative sign included)
- `net_formatted: str` — `total_inflow + total_outflow`, YNAB-formatted
- `average_monthly_spending_formatted: str` — `total_outflow / months_in_window`, YNAB-formatted
- `average_transaction_formatted: str` — `total_outflow / outflow_transaction_count`, YNAB-formatted
- `spending_trend: Literal["increasing", "decreasing", "stable"]` — directional read of outflow over `monthly_buckets`
- `top_payees: List[PayeeAggregate]` — top 5 payees by absolute `amount` sum, sorted descending
- `top_categories: List[CategoryAggregate]` — top 5 categories by absolute `amount` sum, sorted descending
- `by_cleared_status: ClearedBreakdown` — counts of transactions by `cleared` value (cleared / uncleared / reconciled)
- `transaction_count: int` — total number of transactions in the window
- `error: Optional[str]` — populated when computation fails

#### Scenario: monthly_buckets are zero-filled
- **WHEN** the analysis window includes 3 months and only 1 month has transactions
- **THEN** `monthly_buckets` contains 3 entries
- **AND** the empty months have `transaction_count == 0`, `outflow_formatted == "$0.00"`, `inflow_formatted == "$0.00"`
- **AND** the populated month has the actual sums and count

#### Scenario: top_payees returns at most 5 entries
- **WHEN** the window contains transactions against 10 distinct payees
- **THEN** `top_payees` contains exactly 5 entries
- **AND** they are sorted by `total_milliunits` (absolute value) descending
- **AND** unassigned transactions (`payee_id is None`) are aggregated under a single `PayeeAggregate` with `payee_name == "Unassigned"`

#### Scenario: top_categories returns at most 5 entries
- **WHEN** the window contains transactions against 12 distinct categories
- **THEN** `top_categories` contains exactly 5 entries
- **AND** unassigned transactions (`category_id is None`) are aggregated under a single `CategoryAggregate` with `category_name == "Uncategorized"`

#### Scenario: spending_trend is computed from outflow over monthly_buckets
- **WHEN** `monthly_buckets` shows outflow growing month over month
- **THEN** `spending_trend == "increasing"`
- **WHEN** `monthly_buckets` shows outflow shrinking month over month
- **THEN** `spending_trend == "decreasing"`
- **WHEN** the absolute change across buckets is below a defined threshold (e.g. < 5% of mean)
- **THEN** `spending_trend == "stable"`

### Requirement: MonthlyTransactionBucket and PayeeAggregate schemas are defined

The system SHALL define three supporting Pydantic models: `MonthlyTransactionBucket`, `PayeeAggregate`, and `CategoryAggregate`, each with the fields described below.

`MonthlyTransactionBucket`:
- `month: str` — YYYY-MM
- `transaction_count: int`
- `inflow_formatted: str`
- `outflow_formatted: str`
- `net_formatted: str`
- `average_transaction_formatted: str`

`PayeeAggregate`:
- `payee_id: Optional[str]` — None for unassigned
- `payee_name: str`
- `transaction_count: int`
- `total_milliunits: int` — sum of `amount` in milliunits (negative for outflow payees); used as the sort key for `top_payees`
- `total_formatted: str` — same value formatted via the plan's currency

`CategoryAggregate`:
- `category_id: Optional[str]` — None for uncategorized
- `category_name: str`
- `transaction_count: int`
- `total_milliunits: int` — sum of `amount` in milliunits; used as the sort key for `top_categories`
- `total_formatted: str` — same value formatted via the plan's currency

`ClearedBreakdown`:
- `cleared: int`
- `uncleared: int`
- `reconciled: int`

#### Scenario: All supporting schemas are importable
- **WHEN** `from ynab_http_mcp.schemas.transaction_aggregate import MonthlyTransactionBucket, PayeeAggregate, CategoryAggregate, ClearedBreakdown, TransactionInsightsResponse` is executed
- **THEN** no `ImportError` is raised
- **AND** each model can be instantiated with its documented fields

#### Scenario: Bucket aggregates sum to window totals
- **WHEN** the response is computed for a window of 3 months
- **THEN** `sum(bucket.transaction_count for bucket in monthly_buckets) == transaction_count`
- **AND** the absolute value of the sum of bucket outflows equals `total_outflow_formatted` (modulo currency rounding)
- **AND** the absolute value of the sum of bucket inflows equals `total_inflow_formatted` (modulo currency rounding)

### Requirement: Aggregate computation reuses YNAB SDK pagination

The system SHALL use the existing `ynab_service.get_transactions(...)` method to fetch the transaction window. The server SHALL NOT make multiple parallel YNAB API calls per month when one paged call covering the whole window suffices. The `server_knowledge` value from YNAB's response SHALL be ignored for this resource (the aggregate is not delta-based).

#### Scenario: One YNAB call covers a 3-month window
- **WHEN** the LLM reads `data://transactions/insights` with the default 3-month window
- **THEN** the server invokes `ynab_service.get_transactions(since_date=..., until_date=..., type="all")` exactly once
- **AND** the resulting transactions are grouped into `monthly_buckets` in-memory

#### Scenario: YNAB API failure produces an error response
- **WHEN** the underlying YNAB API call fails (network, auth, rate limit)
- **THEN** the response contains `error: str` describing the failure
- **AND** every numeric field is exactly `0` (or `"$0.00"` for formatted strings)
- **AND** every list field is exactly `[]` (including `monthly_buckets`, `top_payees`, `top_categories`)
- **AND** every Optional field is `None` (the only non-None string when `error` is set is `error` itself)
- **AND** `monthly_buckets` contains exactly one entry per month in the requested window, every entry with `transaction_count: 0`, `inflow_formatted: "$0.00"`, `outflow_formatted: "$0.00"`, `net_formatted: "$0.00"`, `average_transaction_formatted: "$0.00"`
- **AND** the LLM can pattern-match `if response.error: ...` without worrying about partial data

