## ADDED Requirements

### Requirement: Category Response Structure
The system SHALL define a CleanCategory schema that represents a cleaned category response.

#### Scenario: Required fields
- **WHEN** CleanCategory schema is defined
- **THEN** it SHALL include these required fields:
  - id: str
  - category_group_id: str
  - name: str
  - hidden: bool
  - original_category_group_id: Optional[str]
  - note: Optional[str]
  - goal_type: Optional[str]
  - goal_day: Optional[int]
  - goal_cadence: Optional[int]
  - goal_cadence_frequency: Optional[int]
  - goal_creation_month: Optional[str]
  - goal_target: Optional[int]
  - goal_target_month: Optional[str]
  - goal_percentage_complete: Optional[int]
  - deleted: bool

#### Scenario: Category validation
- **WHEN** get_categories tool receives valid YNAB category data
- **THEN** it SHALL successfully validate and return CleanCategory objects

### Requirement: Categories Response Container
The system SHALL define a CategoriesResponse schema for the complete response structure.

#### Scenario: Response structure
- **WHEN** CategoriesResponse schema is defined
- **THEN** it SHALL include:
  - category_groups: List[CategoryGroup]

#### Scenario: Category group structure
- **WHEN** CategoryGroup schema is defined
- **THEN** it SHALL include:
  - id: str
  - name: str
  - hidden: bool
  - deleted: bool
  - categories: List[CleanCategory]