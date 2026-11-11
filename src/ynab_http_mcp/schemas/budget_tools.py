"""
Budget tool schemas for YNAB HTTP MCP.
"""

from typing import Optional, Dict, Any, Literal
from pydantic import BaseModel, Field, model_validator


class AssignBudgetCategoryRequest(BaseModel):
    """Request schema for updating a month category budget amount."""

    month: str = Field(..., description="Month YYYY-MM")
    category_id: str = Field(..., description="Category UUID")
    budgeted_amount: int = Field(..., description="Budgeted amount in milliunits", ge=0)


class UpdateCategoryRequest(BaseModel):
    """Request schema for updating a category in YNAB."""

    category_id: str = Field(
        ...,
        description="YNAB category ID (UUID).",
        pattern=r"^[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}$",
    )
    name: Optional[str] = Field(
        None,
        description="New category name (max 50 chars). null = unchanged.",
        max_length=50,
    )
    note: Optional[str] = Field(
        None,
        description="Category note (max 500 chars). null = unchanged.",
        max_length=500,
    )
    category_group_id: Optional[str] = Field(
        None,
        description="Move to this category group (UUID). null = unchanged.",
        pattern=r"^[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}$",
    )
    goal_target: Optional[int] = Field(
        None,
        description="Goal target in milliunits (>=0). With goal_target_date = target-by-date; with goal_frequency = recurring; alone = monthly. null = keep existing.",
        ge=0,
    )
    goal_target_date: Optional[str] = Field(
        None,
        description="Target date YYYY-MM-DD. Cannot combine with goal_frequency. null = no date target.",
        pattern=r"^\d{4}-\d{2}-\d{2}$",
    )
    goal_needs_whole_amount: Optional[bool] = Field(
        None,
        description="NEED goal: true = 'Set aside another' (accumulating), false = 'Refill up to' (maintaining). null = unchanged.",
    )
    goal_frequency: Optional[Literal["monthly", "weekly", "daily", "yearly"]] = Field(
        None,
        description="Recurring NEED goal frequency. Requires goal_target. Cannot combine with goal_target_date. null = unchanged.",
    )


class SetCategoryGoalRequest(BaseModel):
    """Request schema for setting or clearing a category's goal in one call."""

    category_id: str = Field(
        ...,
        description="Category UUID.",
        pattern=r"^[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}$",
    )
    note: Optional[str] = Field(
        None,
        description="Note (max 500). null = unchanged.",
        max_length=500,
    )
    goal_type: Literal["monthly", "recurring", "target_by_date", "clear"] = Field(
        ...,
        description=(
            "Goal to set: 'monthly' = save goal_target each month; "
            "'recurring' = NEED goal repeated on goal_frequency; "
            "'target_by_date' = NEED goal saved by goal_target_date; "
            "'clear' = remove the goal entirely."
        ),
    )
    goal_target: Optional[int] = Field(
        None,
        description="Target in milliunits (>=0). Required unless goal_type='clear'.",
        ge=0,
    )
    goal_target_date: Optional[str] = Field(
        None,
        description="Date YYYY-MM-DD. Required when goal_type='target_by_date'; not allowed otherwise.",
        pattern=r"^\d{4}-\d{2}-\d{2}$",
    )
    goal_needs_whole_amount: Optional[bool] = Field(
        None,
        description="NEED goal: true = 'Set aside another' (accumulating), false = 'Refill up to' (maintaining). Required when goal_type='recurring'.",
    )
    goal_frequency: Optional[Literal["monthly", "weekly", "daily", "yearly"]] = Field(
        None,
        description="Recurring NEED frequency. Required when goal_type='recurring'.",
    )

    @model_validator(mode="after")
    def _check_goal_fields(self) -> "SetCategoryGoalRequest":
        if self.goal_type == "clear":
            if any(
                v is not None
                for v in (
                    self.goal_target,
                    self.goal_target_date,
                    self.goal_needs_whole_amount,
                    self.goal_frequency,
                )
            ):
                raise ValueError(
                    "goal_type='clear' removes the goal and takes no goal fields"
                )
            return self
        if self.goal_target is None:
            raise ValueError(
                f"goal_target is required when goal_type='{self.goal_type}'"
            )
        if self.goal_type == "monthly" and any(
            v is not None
            for v in (
                self.goal_target_date,
                self.goal_needs_whole_amount,
                self.goal_frequency,
            )
        ):
            raise ValueError("goal_type='monthly' takes only goal_target")
        if self.goal_type == "target_by_date":
            if self.goal_target_date is None:
                raise ValueError(
                    "goal_target_date is required when goal_type='target_by_date'"
                )
            if (
                self.goal_needs_whole_amount is not None
                or self.goal_frequency is not None
            ):
                raise ValueError(
                    "goal_type='target_by_date' does not take "
                    "goal_needs_whole_amount or goal_frequency"
                )
        if self.goal_type == "recurring":
            if self.goal_target_date is not None:
                raise ValueError(
                    "goal_target_date cannot combine with goal_type='recurring'"
                )
            if self.goal_needs_whole_amount is None:
                raise ValueError(
                    "goal_needs_whole_amount is required when goal_type='recurring'"
                )
            if self.goal_frequency is None:
                raise ValueError(
                    "goal_frequency is required when goal_type='recurring'"
                )
        return self

    def to_update_category_request(self) -> UpdateCategoryRequest:
        if self.goal_type == "clear":
            # goal_target=0 with no other goal fields signals a full goal
            # removal in YnabService.update_category.
            return UpdateCategoryRequest(
                category_id=self.category_id, note=self.note, goal_target=0
            )  # type: ignore
        return UpdateCategoryRequest(
            category_id=self.category_id,
            note=self.note,
            goal_target=self.goal_target,
            goal_target_date=self.goal_target_date,
            goal_needs_whole_amount=self.goal_needs_whole_amount,
            goal_frequency=self.goal_frequency,
        )  # type: ignore


class UpdateCategoryDetailsRequest(BaseModel):
    """Request schema for updating a category's basic fields (name, note, group)."""

    category_id: str = Field(
        ...,
        description="Category UUID.",
        pattern=r"^[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}$",
    )
    name: Optional[str] = Field(
        None,
        description="Name (max 50). null = unchanged.",
        max_length=50,
    )
    note: Optional[str] = Field(
        None,
        description="Note (max 500). null = unchanged.",
        max_length=500,
    )
    category_group_id: Optional[str] = Field(
        None,
        description="Group UUID. null = unchanged.",
        pattern=r"^[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}$",
    )

    def to_update_category_request(self) -> UpdateCategoryRequest:
        return UpdateCategoryRequest(
            category_id=self.category_id,
            note=self.note,
            name=self.name,
            category_group_id=self.category_group_id,
        )  # type: ignore


class CreateTransactionRequest(BaseModel):
    """Request schema for creating a new transaction."""

    account_id: str = Field(..., description="Account UUID")
    date: str = Field(..., description="Date YYYY-MM-DD")
    amount: int = Field(..., description="Amount in milliunits")
    payee_id: Optional[str] = Field(None, description="Payee UUID")
    payee_name: Optional[str] = Field(None, description="Payee name")
    category_id: Optional[str] = Field(None, description="Category UUID")
    memo: Optional[str] = Field(None, description="Memo")
    cleared: str = Field("cleared", description="Cleared")
    approved: bool = Field(True, description="Approved")
    flag_color: Optional[str] = Field(None, description="Flag")


class BudgetHealthResponse(BaseModel):
    """Response schema for budget health check."""

    month: str = Field(..., description="Month in YYYY-MM format")
    total_budgeted: int = Field(..., description="Total budgeted in milliunits")
    total_budgeted_formatted: str = Field(
        ...,
        description="Fmt budgeted (e.g. $800.00)",
    )
    total_activity: int = Field(..., description="Total activity in milliunits")
    total_activity_formatted: str = Field(
        ...,
        description="Fmt activity (e.g. $600.00)",
    )
    to_be_budgeted: int = Field(..., description="To be budgeted in milliunits")
    to_be_budgeted_formatted: str = Field(
        ...,
        description="Fmt TBB (e.g. $200.00)",
    )
    category_health: Dict[str, Dict[str, Any]] = Field(
        ..., description="Category-level health metrics"
    )
    health_percentage: float = Field(
        ..., description="Percentage of healthy categories"
    )
    is_healthy: bool = Field(..., description="Whether budget is healthy overall")


class SpendingInsightCategory(BaseModel):
    """Category spending insight."""

    category_id: str = Field(..., description="Category ID")
    category_name: str = Field(..., description="Category name")
    total: int = Field(..., description="Total spending in milliunits")
    count: int = Field(..., description="Number of transactions")


class SpendingInsightsResponse(BaseModel):
    """Response schema for spending insights."""

    month: str = Field(..., description="Month in YYYY-MM format")
    category_id: Optional[str] = Field(
        None, description="Filtered category ID if applicable"
    )
    total_spending: int = Field(..., description="Total spending in milliunits")
    total_spending_formatted: str = Field(
        ...,
        description="Fmt spending (e.g. -$1,000.00)",
    )
    average_transaction: float = Field(..., description="Average transaction amount")
    average_transaction_formatted: str = Field(
        ...,
        description="Fmt avg (e.g. -$33)",
    )
    transaction_count: int = Field(..., description="Number of transactions")
    category_insights: Dict[str, Dict[str, Any]] = Field(
        ..., description="Category-level spending insights"
    )
