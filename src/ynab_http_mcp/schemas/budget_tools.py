"""
Budget tool schemas for YNAB HTTP MCP.

This module defines Pydantic models for budget management tool
requests and responses.
"""

from typing import Optional, Dict, List, Any, Literal
from pydantic import BaseModel, Field, ConfigDict


class AssignBudgetCategoryRequest(BaseModel):
    """
    Request schema for updating a month category budget amount.
    """

    month: str = Field(..., description="Month in YYYY-MM format")
    category_id: str = Field(..., description="YNAB category ID")
    budgeted_amount: int = Field(
        ..., description="New budgeted amount in milliunits", ge=0
    )


class UpdateCategoryRequest(BaseModel):
    """
    Request schema for updating a category in YNAB.

    This schema maps to the YNAB API's ExistingCategory model and supports comprehensive
    category updates including name, note, category group changes, and various goal configurations.

    Usage examples:
    - To set a monthly funding goal: provide goal_target with goal_frequency='monthly'
    - To set a target date goal: provide goal_target with goal_target_date
    - To remove a goal: set goal_type='none' or omit all goal-related fields
    - To update category metadata: provide name, note, or category_group_id

    Note: This is a comprehensive schema that supports all YNAB category update operations.
    Not all fields are required for every operation - provide only the fields you want to update.
    """

    category_id: str = Field(
        ...,
        description="YNAB category ID. The unique identifier for the category to update.",
        pattern=r"^[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}$",
    )
    name: Optional[str] = Field(
        None,
        description="Optional new name for the category. When provided, updates the category name. Use null to leave unchanged.",
        max_length=50,
    )
    note: Optional[str] = Field(
        None,
        description="Optional note for the category. When provided, updates the category note. Use null to leave unchanged.",
        max_length=500,
    )
    category_group_id: Optional[str] = Field(
        None,
        description="Optional ID of category group to move to. When provided, moves the category to a different group. Cannot be used to move to internal category groups. Use null to leave in current group.",
        pattern=r"^[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}$",
    )
    goal_target: Optional[int] = Field(
        None,
        description="""Goal target amount in milliunits. When specified, configures the goal target amount. 
        - If goal_target_date is also provided: Creates a target-by-date goal
        - If goal_frequency is also provided: Creates a recurring goal with this target
        - If neither is provided and goal has not been configured: Creates a monthly goal
        - Use null to remove an existing target while keeping other goal settings
        - For Credit Card Payment categories, defaults to 'NEED' goal type if goal_type not specified""",
        ge=0,
    )
    goal_target_date: Optional[str] = Field(
        None,
        description="Goal target date in ISO format (YYYY-MM-DD). When provided with goal_target, creates a target-by-date goal. Cannot be combined with goal_frequency. Use null for non-date-based goals.",
        pattern=r"^\d{4}-\d{2}-\d{2}$",
    )
    goal_needs_whole_amount: Optional[bool] = Field(
        None,
        description="""Whether the goal requires the full target amount each period. Only applicable for 'NEED' type goals. 
        - true: Goal is configured as 'Set aside another...' (accumulating)
        - false: Goal is configured as 'Refill up to...' (maintaining balance)
        - null: Leaves existing setting unchanged
        Only supported for 'NEED' goals. Ignored for other goal types.""",
    )
    goal_frequency: Optional[Literal["monthly", "weekly", "daily", "yearly"]] = Field(
        None,
        description="""Frequency for recurring goals. When specified with goal_target, configures a recurring 'NEED' target. 
        Supported values: 'monthly', 'weekly', 'daily', 'yearly'
        - Cannot be combined with goal_target_date
        - Not supported for Credit Card Payment categories
        - Requires goal_target to be set
        - Use null to leave an existing target's cadence unchanged""",
    )
class UpdateCategoryGoalRecurringRequest(UpdateCategoryRequest):
    """
    Request schema for updating a category goal to a recurring goal in YNAB.
    Usage examples:
    - To set a monthly funding goal: provide goal_target with goal_frequency='monthly'
    """
    # Excluded fields:
    name: Optional[str] = Field(default=None, exclude=True)
    category_group_id: Optional[str] = Field(default=None, exclude=True)
    goal_target_date: Optional[str] = Field(default=None, exclude=True)

    # Fields with updated parameters
    goal_target: int = Field(
        ...,
        description="""Goal target amount in milliunits.""",
        ge=0,
    )
    goal_needs_whole_amount: bool = Field(
        ...,
        description="""Whether the goal requires the full target amount each period. Only applicable for 'NEED' type goals. 
        - true: Goal is configured as 'Set aside another...' (accumulating)
        - false: Goal is configured as 'Refill up to...' (maintaining balance)""",
    )
    goal_frequency: Literal["monthly", "weekly", "daily", "yearly"] = Field(
        ...,
        description="""Frequency for recurring goals. When specified with goal_target, configures a recurring 'NEED' target. 
        Supported values: 'monthly', 'weekly', 'daily', 'yearly'"""
    )


    def to_update_category_request(self) -> UpdateCategoryRequest:
        return UpdateCategoryRequest(
            category_id=self.category_id,
            note=self.note,
            goal_target=self.goal_target,
            goal_needs_whole_amount=self.goal_needs_whole_amount,
            goal_frequency=self.goal_frequency
        ) # type: ignore
class UpdateCategoryDetailsRequest(UpdateCategoryRequest):
    """
    Request schema for updating a category's basic fields.
    
    """
    # Excluded fields:
    goal_target_date: Optional[str] = Field(default=None, exclude=True)
    goal_target: Optional[int] = Field(default=None, exclude=True)
    goal_frequency: Optional[Literal["monthly", "weekly", "daily", "yearly"]] = Field(default=None, exclude=True)
    goal_needs_whole_amount: Optional[bool] = Field(default=None, exclude=True)


    # Fields with updated parameters



    def to_update_category_request(self) -> UpdateCategoryRequest:
        return UpdateCategoryRequest(
            category_id=self.category_id,
            note=self.note,
            name=self.name,
            category_group_id=self.category_group_id
        ) # type: ignore

class UpdateCategoryTargetDateRequest(UpdateCategoryRequest):
    """
    Request schema for updating a category goal to a target date in YNAB.
    Usage examples:
    - To set a target date goal: provide goal_target with goal_target_date
    """
    # Excluded fields:
    name: Optional[str] = Field(default=None, exclude=True)
    category_group_id: Optional[str] = Field(default=None, exclude=True)
    goal_frequency: Optional[Literal["monthly", "weekly", "daily", "yearly"]] = Field(default=None, exclude=True)
    goal_needs_whole_amount: Optional[bool] = Field(default=None, exclude=True)

    goal_target: int = Field(
        ...,
        description="""Goal target amount in milliunits. When specified, configures the goal target amount. 
        - If goal_target_date is also provided: Creates a target-by-date goal
        - For Credit Card Payment categories, defaults to 'NEED' goal type if goal_type not specified""",
        ge=0,
    )
    goal_target_date: str = Field(
        ...,
        description="Goal target date in ISO format (YYYY-MM-DD).",
        pattern=r"^\d{4}-\d{2}-\d{2}$",
    )
    def to_update_category_request(self) -> UpdateCategoryRequest:
        return UpdateCategoryRequest(
            category_id=self.category_id,
            note=self.note,
            goal_target=self.goal_target,
            goal_target_date=self.goal_target_date
        ) # type: ignore
    
class ClearCategoryGoalRequest(UpdateCategoryRequest):
    """
    Request schema for clearing a category goal.
    """
    # Excluded fields:
    name: Optional[str] = Field(default=None, exclude=True)
    category_group_id: Optional[str] = Field(default=None, exclude=True)
    goal_frequency: Optional[Literal["monthly", "weekly", "daily", "yearly"]] = Field(default=None, exclude=True)
    goal_needs_whole_amount: Optional[bool] = Field(default=None, exclude=True)
    goal_target: Optional[int] = Field(default=None, exclude=True)
    goal_target_date: Optional[str] = Field(default=None, exclude=True)
    
    def to_update_category_request(self) -> UpdateCategoryRequest:
        return UpdateCategoryRequest(
            category_id=self.category_id,
            note=self.note,
            goal_target=None
        ) # type: ignore



class CreateTransactionRequest(BaseModel):
    """
    Request schema for creating a new transaction.
    """

    account_id: str = Field(..., description="YNAB account ID")
    date: str = Field(..., description="Transaction date in YYYY-MM-DD format")
    amount: int = Field(..., description="Transaction amount in milliunits")
    payee_id: Optional[str] = Field(None, description="YNAB payee ID")
    payee_name: Optional[str] = Field(None, description="Payee name")
    category_id: Optional[str] = Field(None, description="YNAB category ID")
    memo: Optional[str] = Field(None, description="Transaction memo")
    cleared: str = Field("cleared", description="Transaction cleared status")
    approved: bool = Field(True, description="Whether transaction is approved")
    flag_color: Optional[str] = Field(None, description="Transaction flag color")


class BudgetHealthResponse(BaseModel):
    """
    Response schema for budget health check.
    """

    month: str = Field(..., description="Month in YYYY-MM format")
    total_budgeted: int = Field(..., description="Total budgeted in milliunits")
    total_activity: int = Field(..., description="Total activity in milliunits")
    to_be_budgeted: int = Field(..., description="To be budgeted in milliunits")
    category_health: Dict[str, Dict[str, Any]] = Field(
        ..., description="Category-level health metrics"
    )
    health_percentage: float = Field(
        ..., description="Percentage of healthy categories"
    )
    is_healthy: bool = Field(..., description="Whether budget is healthy overall")


class SpendingInsightCategory(BaseModel):
    """
    Category spending insight.
    """

    category_id: str = Field(..., description="Category ID")
    category_name: str = Field(..., description="Category name")
    total: int = Field(..., description="Total spending in milliunits")
    count: int = Field(..., description="Number of transactions")


class SpendingInsightsResponse(BaseModel):
    """
    Response schema for spending insights.
    """

    month: str = Field(..., description="Month in YYYY-MM format")
    category_id: Optional[str] = Field(
        None, description="Filtered category ID if applicable"
    )
    total_spending: int = Field(..., description="Total spending in milliunits")
    average_transaction: float = Field(..., description="Average transaction amount")
    transaction_count: int = Field(..., description="Number of transactions")
    category_insights: Dict[str, Dict[str, Any]] = Field(
        ..., description="Category-level spending insights"
    )
