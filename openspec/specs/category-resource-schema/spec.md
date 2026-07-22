# category-resource-schema Specification

## Purpose
TBD - created by archiving change refactor-category-schema. Update Purpose after archive.
## Requirements
### Requirement: MCPCategory inherits from MCPResponse

The system SHALL define `MCPCategory(MCPResponse[ynab.Category])` with the same shape used by `MCPAccount`: a single class with all category fields, a classmethod `from_ynab(raw: ynab.Category | ynab.CategoryResponse) -> MCPCategory` that accepts either a bare `ynab.Category` or a wrapped `ynab.CategoryResponse` (unwrapping via `raw.data.category` in the latter case). No separate response wrapper for the single-category case.

#### Scenario: from_ynab accepts a bare ynab.Category
- **WHEN** `MCPCategory.from_ynab` is called with a `ynab.Category` instance
- **THEN** it returns a populated `MCPCategory` with id, name, group id, hidden, deleted, note, formatted budget/activity/balance, and a nested `MCPCategoryGoal` populated from the same raw object

#### Scenario: from_ynab accepts a wrapped ynab.CategoryResponse
- **WHEN** `MCPCategory.from_ynab` is called with a `ynab.CategoryResponse` instance
- **THEN** it unwraps `raw.data.category` and returns the same shape as the bare case

#### Scenario: MCPCategory surfaces formatted currency
- **WHEN** `MCPCategory.from_ynab` populates the budget fields
- **THEN** `budgeted_formatted`, `activity_formatted`, and `balance_formatted` contain YNAB's pre-formatted strings (e.g. `"-£450.00"`)
- **AND** no milliunit-to-decimal conversion is performed in this layer

### Requirement: MCPCategoryGoal produces LLM-friendly summary strings

The system SHALL define `MCPCategoryGoal(MCPResponse[ynab.Category])` with the following fields: three raw fields — `goal_type` (string, nullable), `goal_target_date` (ISO date, nullable), `goal_percentage_complete` (integer 0..100, nullable) — plus two derived optional strings, `goal_summary` and `goal_status`. The `from_ynab` classmethod SHALL populate the two derived strings by calling two module-level helpers — `_explain_goal_type(raw)` and `_explain_goal_funding_status(raw)` — and SHALL return an empty-instance `MCPCategoryGoal()` (every field None) when `raw.goal_type` is None. The model SHALL NOT expose milliunit fields, formatted-twins of fields already in `goal_summary`/`goal_status`, or goal attributes whose values are fully captured in the derived strings (e.g. `goal_under_funded`, `goal_overall_left`, `goal_target`, `goal_overall_funded`, `goal_snoozed_at`, `goal_day`, `goal_cadence`, `goal_cadence_frequency`, `goal_creation_month`, `goal_months_to_budget`, `goal_needs_whole_amount`). All 16 dropped fields remain reachable via the `data://categories/{id}/full` drill-in (`full_details`).

#### Scenario: No goal yields empty goal model
- **WHEN** `MCPCategoryGoal.from_ynab` is called with a `ynab.Category` whose `goal_type` is None
- **THEN** the returned instance has every field set to None, including `goal_summary` and `goal_status`

#### Scenario: TB goal explains target balance
- **WHEN** the raw category has `goal_type = "TB"` and a `goal_target_formatted` value
- **THEN** `goal_summary` contains the literal phrase "Target Category Balance" and references the formatted target amount
- **AND** `goal_status` reflects whether the category is currently under- or over-funded

#### Scenario: TBD goal explains target balance by date
- **WHEN** the raw category has `goal_type = "TBD"` and a `goal_target_date`
- **THEN** `goal_summary` contains "Target Category Balance by Date" and references the target date and formatted target amount

#### Scenario: MF goal explains cadence and refill vs set-aside
- **WHEN** the raw category has `goal_type = "MF"`
- **THEN** `goal_summary` describes the cadence in plain English (e.g. "every 2 months", "weekly", "every 2 years", "by <date>" when cadence is 0)
- **AND** the phrasing uses "Refill" when `goal_needs_whole_amount` is False and "Set aside" when True
- **AND** `_explain_goal_type` raises `ValueError` for any cadence value outside 0–14 or any missing required `goal_cadence_frequency`

#### Scenario: Weekly cadence uses frequency, not cadence*frequency
- **WHEN** the raw category has `goal_type = "MF"`, `goal_cadence = 2` (weekly), and `goal_cadence_frequency = 1`
- **THEN** `goal_summary` reads "every week" (or "weekly")
- **AND** it does NOT read "every 2 weeks" — cadence 2 means weekly, and `goal_cadence_frequency` is a multiplier (`2` would mean "every 2 weeks")

#### Scenario: Yearly cadence uses frequency, not cadence*frequency
- **WHEN** the raw category has `goal_type = "MF"`, `goal_cadence = 13` (yearly), and `goal_cadence_frequency = 1`
- **THEN** `goal_summary` reads "every year" (or "yearly")
- **AND** it does NOT read "every 13 years" — cadence 13 means yearly, and `goal_cadence_frequency` is a multiplier (`2` would mean "every 2 years")

#### Scenario: Biweekly cadence is "every 2 weeks"
- **WHEN** the raw category has `goal_type = "MF"`, `goal_cadence = 2` (weekly), and `goal_cadence_frequency = 2`
- **THEN** `goal_summary` reads "every 2 weeks"
- **AND** the math is `goal_cadence_frequency` (2) weeks apart, NOT `goal_cadence * goal_cadence_frequency` (4) weeks apart

#### Scenario: Every-N-months cadence is cadence-1
- **WHEN** the raw category has `goal_type = "MF"`, `goal_cadence = 3`
- **THEN** `goal_summary` reads "every 2 months" (cadence 3 means "every (3-1) months")
- **AND** `goal_cadence_frequency` is ignored for cadence values 3-12 and 14

#### Scenario: Every 2 years cadence ignores frequency
- **WHEN** the raw category has `goal_type = "MF"`, `goal_cadence = 14`
- **THEN** `goal_summary` reads "every 2 years"
- **AND** `goal_cadence_frequency` is ignored

#### Scenario: NEED goal explains plan-your-spending
- **WHEN** the raw category has `goal_type = "NEED"`
- **THEN** `goal_summary` contains "Plan Your Spending"

#### Scenario: Unknown goal type is labelled but not an error
- **WHEN** the raw category has an unrecognised `goal_type`
- **THEN** `goal_summary` returns `"Unknown goal type: {raw.goal_type}"` and `from_ynab` does not raise

#### Scenario: Lean MCPCategoryGoal exposes only 5 fields
- **WHEN** `MCPCategoryGoal.model_fields` is inspected
- **THEN** exactly 5 fields are present: `goal_type`, `goal_target_date`, `goal_percentage_complete`, `goal_summary`, `goal_status`
- **AND** none of the following fields exist on the lean model: `goal_needs_whole_amount`, `goal_day`, `goal_cadence`, `goal_cadence_frequency`, `goal_creation_month`, `goal_target`, `goal_under_funded`, `goal_overall_funded`, `goal_overall_left`, `goal_snoozed_at`, `goal_target_formatted`, `goal_under_funded_formatted`, `goal_overall_funded_formatted`, `goal_overall_left_formatted`, `goal_months_to_budget`

#### Scenario: Dropped fields remain reachable via full_details
- **WHEN** the LLM reads `data://categories/{id}/full`
- **THEN** `full_details` contains all the fields the lean `MCPCategoryGoal` dropped: `goal_under_funded`, `goal_overall_funded`, `goal_overall_left`, `goal_snoozed_at`, `goal_target`, `goal_creation_month`, `goal_cadence`, `goal_cadence_frequency`, `goal_needs_whole_amount`, `goal_day`, and the four `*_formatted` companions
- **AND** those fields are reachable in the drill-in dict by their original YNAB field names

### Requirement: MCPCategories is a flat-list wrapper with HIDE_DELETED

The system SHALL define `MCPCategories(MCPResponse[ynab.CategoriesResponse])` as a higher-level wrapper that holds `category_groups: List[MCPCategoryGroup]` and a class constant `HIDE_DELETED: bool = True`. The classmethod `from_ynab(raw: ynab.CategoriesResponse) -> MCPCategories` SHALL iterate `raw.data.category_groups`, skip groups where `HIDE_DELETED and group.deleted` is True, build each remaining group via `MCPCategoryGroup.from_ynab`, and return a `MCPCategories` containing the assembled list. The wire shape MUST match the YNAB-native `{"category_groups": [...]}` envelope (the flat-list shape from the previous change is removed).

#### Scenario: Default behaviour filters deleted groups and categories
- **WHEN** `MCPCategories.from_ynab` is called on a response containing a deleted group and a non-deleted group that itself contains a deleted category
- **THEN** the deleted group is omitted from the result
- **AND** the surviving group's `categories` list contains only non-deleted categories

#### Scenario: HIDE_DELETED can be disabled
- **WHEN** a subclass sets `HIDE_DELETED = False`
- **THEN** `from_ynab` includes deleted groups in the returned list
- **AND** each surviving group's `MCPCategoryGroup.from_ynab` still applies its own `HIDE_DELETED` filter on the inner categories list (settable independently on `MCPCategoryGroup`)

### Requirement: Categories schema module imports cleanly under mypy and ruff

The system SHALL keep `src/ynab_http_mcp/schemas/categories.py` free of undefined names, broken indentation, stray braces, and unused imports. `uv run mypy src` and `uv run ruff check .` SHALL both succeed on the file.

#### Scenario: No undefined names remain
- **WHEN** `schemas/categories.py` is imported
- **THEN** no `NameError` is raised
- **AND** every type referenced in field annotations is imported

### Requirement: MCPCategoryGroup nests categories with its own HIDE_DELETED

The system SHALL define `MCPCategoryGroup(MCPResponse[ynab.CategoryGroupWithCategories])` with the YNAB category-group fields (`id`, `name`, `hidden`, `internal`, `deleted`) and a `categories: List[MCPCategory]` slot. The class constant `HIDE_DELETED: bool = True` SHALL live on the class. The classmethod `from_ynab(raw: ynab.CategoryGroupWithCategories) -> MCPCategoryGroup` SHALL iterate `raw.categories`, skip entries where `HIDE_DELETED and category.deleted` is True, build each remaining category via `MCPCategory.from_ynab`, and return a `MCPCategoryGroup` whose `categories` slot holds the filtered list.

#### Scenario: from_ynab populates group metadata and nested categories
- **WHEN** `MCPCategoryGroup.from_ynab` is called with a `ynab.CategoryGroupWithCategories` containing two non-deleted categories
- **THEN** the returned instance has `id`, `name`, `hidden`, `internal`, `deleted` copied from the raw
- **AND** the `categories` list contains two `MCPCategory` instances built via `MCPCategory.from_ynab`

#### Scenario: Default behaviour filters deleted categories inside a group
- **WHEN** `MCPCategoryGroup.from_ynab` is called with a raw group containing both deleted and non-deleted categories
- **THEN** the returned `categories` list contains only the non-deleted categories

#### Scenario: HIDE_DELETED can be disabled on the inner class
- **WHEN** a subclass sets `MCPCategoryGroup.HIDE_DELETED = False`
- **THEN** `from_ynab` includes deleted categories in the returned `categories` list

