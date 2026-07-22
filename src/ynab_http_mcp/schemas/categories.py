"""
Simplified category schemas for YNAB HTTP MCP.

This module defines simplified Pydantic models for validating
YNAB category data using basic data types suitable for agents.
"""

from typing import Optional, List, Self
from unittest import case
from pydantic import BaseModel, Field
from uuid import UUID
from ynab import (
    CategoriesResponse as ynabCategoriesResponse,
    CategoryResponse as ynabCategoryResponse,
)
import ynab
from .base import MCPResponse, uuid_type, date_type
from ynab_http_mcp.utils.schema_utils import clean_ynab_data, simple_validate

class MCPCategoryGoal(MCPResponse[ynab.Category]):

    goal_type: Optional[StrictStr] = Field(default=None, description="The type of goal, if the category has a goal (TB='Target Category Balance', TBD='Target Category Balance by Date', MF='Monthly Funding', NEED='Plan Your Spending')")
    goal_needs_whole_amount: Optional[StrictBool] = Field(default=None, description="Indicates the monthly rollover behavior for \"NEED\"-type goals. When \"true\", the goal will always ask for the target amount in the new month (\"Set Aside\"). When \"false\", previous month category funding is used (\"Refill\"). For other goal types, this field will be null.")
    goal_day: Optional[StrictInt] = Field(default=None, description="A day offset modifier for the goal's due date. When goal_cadence is 2 (Weekly), this value specifies which day of the week the goal is due (0 = Sunday, 6 = Saturday). Otherwise, this value specifies which day of the month the goal is due (1 = 1st, 31 = 31st, null = Last day of Month).")
    goal_cadence: Optional[StrictInt] = Field(default=None, description="The goal cadence. Value in range 0-14. There are two subsets of these values which behave differently. For values 0, 1, 2, and 13, the goal's due date repeats every goal_cadence * goal_cadence_frequency, where 0 = None, 1 = Monthly, 2 = Weekly, and 13 = Yearly. For example, goal_cadence 1 with goal_cadence_frequency 2 means the goal is due every other month. For values 3-12 and 14, goal_cadence_frequency is ignored and the goal's due date repeats every goal_cadence, where 3 = Every 2 Months, 4 = Every 3 Months, ..., 12 = Every 11 Months, and 14 = Every 2 Years.")
    goal_cadence_frequency: Optional[StrictInt] = Field(default=None, description="The goal cadence frequency. When goal_cadence is 0, 1, 2, or 13, a goal's due date repeats every goal_cadence * goal_cadence_frequency. For example, goal_cadence 1 with goal_cadence_frequency 2 means the goal is due every other month.  When goal_cadence is 3-12 or 14, goal_cadence_frequency is ignored.")
    goal_creation_month: Optional[date] = Field(default=None, description="The month a goal was created")
    goal_target: Optional[StrictInt] = Field(default=None, description="The goal target amount in milliunits")
    goal_target_date: Optional[date] = Field(default=None, description="The target date for the goal to be completed.  Only some goal types specify this date.")
    goal_percentage_complete: Optional[StrictInt] = Field(default=None, description="The percentage completion of the goal")
    goal_months_to_budget: Optional[StrictInt] = Field(default=None, description="The number of months, including the current month, left in the current goal period.")
    goal_under_funded: Optional[StrictInt] = Field(default=None, description="The amount of funding still needed in the current month to stay on track towards completing the goal within the current goal period. This amount will generally correspond to the 'Underfunded' amount in the web and mobile clients except when viewing a category with a Needed for Spending Goal in a future month.  The web and mobile clients will ignore any funding from a prior goal period when viewing category with a Needed for Spending Goal in a future month.")
    goal_overall_funded: Optional[StrictInt] = Field(default=None, description="The total amount funded towards the goal within the current goal period.")
    goal_overall_left: Optional[StrictInt] = Field(default=None, description="The amount of funding still needed to complete the goal within the current goal period.")
    goal_snoozed_at: Optional[datetime] = Field(default=None, description="The date/time the goal was snoozed.  If the goal is not snoozed, this will be null.")
    goal_target_formatted: Optional[StrictStr] = Field(default=None, description="The goal target amount formatted in the plan's currency format")
    goal_target_currency: Optional[Union[StrictFloat, StrictInt]] = Field(default=None, description="The goal target amount as a decimal currency amount")
    goal_under_funded_formatted: Optional[StrictStr] = Field(default=None, description="The goal underfunded amount formatted in the plan's currency format")
    goal_under_funded_currency: Optional[Union[StrictFloat, StrictInt]] = Field(default=None, description="The goal underfunded amount as a decimal currency amount")
    goal_overall_funded_formatted: Optional[StrictStr] = Field(default=None, description="The total amount funded towards the goal formatted in the plan's currency format")
    goal_overall_funded_currency: Optional[Union[StrictFloat, StrictInt]] = Field(default=None, description="The total amount funded towards the goal as a decimal currency amount")
    goal_overall_left_formatted: Optional[StrictStr] = Field(default=None, description="The amount of funding still needed to complete the goal formatted in the plan's currency format")
    goal_overall_left_currency: Optional[Union[StrictFloat, StrictInt]] = Field(default=None, description="The amount of funding still needed to complete the goal as a decimal currency amount")

    @classmethod
    def from_ynab(cls, raw: ynab.Category) -> Self:
        if not raw.goal_type:
            return cls(goal_type=None)
        def explain_goal_type() -> str:
            # First, branch out depending on goal type
            match raw.goal_type:
                # TB and TBD have no frequency to take into account, and no other special handling needed, so we can just return a simple explanation
                case "TB":
                    output = f"Target Category Balance: The goal is to reach a balance of {raw.goal_target_formatted} in the category."
                case "TBD":
                    output = f"Target Category Balance by Date: The goal is to reach a balance of {raw.goal_target_formatted} in the category by {raw.goal_target_date}."
                case "MF":
                    # When the goal does not repeat. None shouldn't be a thing here since we established the type as MF
                    if not raw.goal_cadence or raw.goal_cadence == 0:
                        if raw.goal_needs_whole_amount:
                            output = f"Set aside: The goal is to set aside {raw.goal_target_formatted} for the category by {raw.goal_target_date}."
                        else:
                            output = f"Refill: The goal is to refill the category to {raw.goal_target_formatted} by {raw.goal_target_date}."
                    # Monthly
                    elif raw.goal_cadence == 1:
                        if not raw.goal_cadence_frequency:
                            raise ValueError("goal_cadence_frequency cannot be null for a standard monthly goal")
                        if raw.goal_needs_whole_amount:
                            output = f"Set aside: The goal is to set aside {raw.goal_target_formatted} for the category every {raw.goal_cadence * raw.goal_cadence_frequency} month(s)."
                        else:
                            output = f"Refill: The goal is to refill the category to {raw.goal_target_formatted} every {raw.goal_cadence * raw.goal_cadence_frequency} month(s)."
                    # Weekly
                    elif raw.goal_cadence == 2:
                        if not raw.goal_cadence_frequency:
                            raise ValueError(f"Error while converting YNAB response to MCP-friendly object. goal_cadence_frequency cannot be null for a standard weekly goal fo category {raw.name}")
                        if raw.goal_needs_whole_amount:
                            output = f"Set aside: The goal is to set aside {raw.goal_target_formatted} for the category every {raw.goal_cadence * raw.goal_cadence_frequency} week(s)."
                        else:
                            output = f"Refill: The goal is to refill the category to {raw.goal_target_formatted} every {raw.goal_cadence * raw.goal_cadence_frequency} week(s)."
                    # Every x months
                    elif 3 <= raw.goal_cadence <= 12:
                        if raw.goal_needs_whole_amount:
                            output = f"Set aside: The goal is to set aside {raw.goal_target_formatted} for the category every {raw.goal_cadence - 1} months."
                        else:
                            output = f"Refill: The goal is to refill the category to {raw.goal_target_formatted} every {raw.goal_cadence - 1} months."
                    # Yearly
                    elif raw.goal_cadence == 13:
                        if not raw.goal_cadence_frequency:
                            raise ValueError(f"Error while converting YNAB response to MCP-friendly object. goal_cadence_frequency cannot be null for a standard yearly goal for category {raw.name}")
                        if raw.goal_needs_whole_amount:
                            output = f"Set aside: The goal is to set aside {raw.goal_target_formatted} for the category every {raw.goal_cadence * raw.goal_cadence_frequency} year(s)."
                        else:
                            output = f"Refill: The goal is to refill the category to {raw.goal_target_formatted} every {raw.goal_cadence * raw.goal_cadence_frequency} year(s)."
                    # Special every 2 years
                    elif raw.goal_cadence == 14:
                        if raw.goal_needs_whole_amount:
                            output = f"Set aside: The goal is to set aside {raw.goal_target_formatted} for the category every 2 years."
                        else:
                            output = f"Refill: The goal is to refill the category to {raw.goal_target_formatted} every 2 years."
                    else:
                        raise ValueError(f"Error while converting YNAB response to MCP-friendly object. Unrecognized goal cadence in category {raw.name}: goal_cadence {raw.goal_cadence}")
                case "NEED":
                    output = "Plan Your Spending: The goal is to plan your spending for the category, ensuring you have enough funds available."
                case _:
                    output = f"Unknown goal type: {raw.goal_type}"
            return output
            }

            output="### Goal type: \n {}"

            return output

        def explain_goal_funding_status():

        return cls()
class MCPCategory(MCPResponse[ynab.Category]):

    """
    Simplified category model using basic data types.

    Represents a YNAB category with all essential fields
    using simple types that are easily consumable by AI agents.
    """

    # Required fields
    id: uuid_type = Field(..., description="Unique category identifier")
    category_group_id: uuid_type = Field(..., description="ID of the parent category group")
    name: str = Field(..., description="Category name")
    hidden: bool = Field(..., description="Whether category is hidden")
    deleted: bool = Field(..., description="Whether category is deleted")

    # Budget fields (using formatted currency from YNAB)
    budgeted_formatted: Optional[str] = Field(
        None, description="Budgeted amount with currency formatting"
    )
    activity_formatted: Optional[str] = Field(
        None, description="Activity amount with currency formatting"
    )
    balance_formatted: Optional[str] = Field(
        None, description="Balance with currency formatting"
    )

    # Optional fields
    original_category_group_id: Optional[str] = Field(
        None, description="Original category group ID if moved"
    )
    note: Optional[str] = Field(None, description="Category note")
    goal_type: Optional[str] = Field(None, description="Type of goal if set")
    goal_day: Optional[int] = Field(None, description="Day of month for goal")
    goal_cadence: Optional[int] = Field(None, description="Goal cadence")
    goal_cadence_frequency: Optional[int] = Field(
        None, description="Goal cadence frequency"
    )
    goal_creation_month: Optional[str] = Field(
        None, description="Month when goal was created"
    )
    goal_target: Optional[int] = Field(None, description="Goal target amount")
    goal_target_month: Optional[str] = Field(None, description="Target month for goal")
    goal_percentage_complete: Optional[int] = Field(
        None, description="Percentage of goal completed"
    )

    # Goal summary fields (human-readable)
    goal_summary: Optional[str] = Field(None, description="Human-readable goal summary")
    goal_status: Optional[str] = Field(None, description="Human-readable goal status")
    goal_technical_details: Optional[str] = Field(
        None, description="Technical goal details for advanced use"
    )


class CategoryGroup(BaseModel):
    """
    Simplified category group model using basic data types.

    Represents a group of related categories.
    """

    id: str = Field(..., description="Unique category group identifier")
    name: str = Field(..., description="Category group name")
    hidden: bool = Field(..., description="Whether category group is hidden")
    deleted: bool = Field(..., description="Whether category group is deleted")
    categories: List[MCPCategory] = Field(
        default_factory=list, description="List of categories in this group"
    )


class CategoriesResponse(BaseModel):
    """
    Simplified response structure for categories endpoint.

    Wraps the list of category groups.
    """

    category_groups: List[CategoryGroup] = Field(
        ..., description="List of category groups"
    )

    @staticmethod
    def from_ynab_response(
        ynab_response: ynabCategoriesResponse,
    ) -> "CategoriesResponse":
        """Transform YNAB API response to match our simplified schema."""
        # Convert to dict
        raw_data = ynab_response.to_dict()

        # Clean and validate category groups and categories using simplified approach
        cleaned_category_groups = []

        for group_data in raw_data.get("data", {}).get("category_groups", []):
            # Clean categories within the group using unified cleaning
            cleaned_categories = []
            for category_data in group_data.get("categories", []):
                try:
                    # Clean data using unified function
                    cleaned_data = clean_ynab_data(category_data)

                    # Validate using simplified approach
                    validated_category = simple_validate(cleaned_data, MCPCategory)
                    cleaned_categories.append(validated_category.model_dump())
                except Exception:
                    from ynab_http_mcp.debug import debug_exception

                    debug_exception(
                        f"Failed to validate category {category_data.get('id', 'unknown')}"
                    )
                    continue

            # Clean group data using unified cleaning
            cleaned_group_data = clean_ynab_data(group_data)
            cleaned_group_data["categories"] = cleaned_categories

            try:
                cleaned_group = simple_validate(cleaned_group_data, CategoryGroup)
                cleaned_category_groups.append(cleaned_group.model_dump())
            except Exception:
                from ynab_http_mcp.debug import debug_exception

                debug_exception(
                    f"Failed to validate category group {group_data.get('id', 'unknown')}"
                )
                continue

        # Create final response
        final_response = {"category_groups": cleaned_category_groups}

        # Validate complete response structure using simplified approach
        try:
            validated_response = simple_validate(final_response, CategoriesResponse)
            return validated_response
        except Exception:
            from ynab_http_mcp.debug import debug_exception

            debug_exception("Failed to validate final categories response")
            # Return a fallback response if validation fails
            # Convert dicts back to CategoryGroup objects for type safety
            fallback_groups = []
            for group_dict in cleaned_category_groups:
                try:
                    # Convert categories back to CleanCategory objects
                    categories = []
                    for cat_dict in group_dict.get("categories", []):
                        categories.append(MCPCategory(**cat_dict))

                    # Create CategoryGroup object
                    group_obj = CategoryGroup(
                        id=group_dict["id"],
                        name=group_dict["name"],
                        hidden=group_dict.get("hidden", False),
                        deleted=group_dict.get("deleted", False),
                        categories=categories,
                    )
                    fallback_groups.append(group_obj)
                except Exception:
                    # If conversion fails, skip this group
                    continue

            fallback_response = CategoriesResponse(category_groups=fallback_groups)
            return fallback_response


class CategoryResponse(BaseModel):
    """
    Simplified response structure for single category endpoint.

    Wraps a single category with its group information.
    """

    category: MCPCategory = Field(..., description="Single category details")
    category_group: CategoryGroup = Field(..., description="Parent category group")

    @staticmethod
    def from_ynab_response(ynab_response: ynabCategoryResponse) -> "CategoryResponse":
        """Transform YNAB API response to match our simplified schema."""
        # Convert to dict
        raw_data = ynab_response.to_dict()

        # Extract category and group data from YNAB response structure
        category_data = raw_data.get("data", {}).get("category", {})
        group_data = raw_data.get("data", {}).get("category_group", {})

        try:
            # Clean and validate category data
            cleaned_category_data = clean_ynab_data(category_data)
            validated_category = simple_validate(cleaned_category_data, MCPCategory)

            # Clean and validate group data
            cleaned_group_data = clean_ynab_data(group_data)
            # Add the cleaned category to the group
            cleaned_group_data["categories"] = [validated_category.model_dump()]
            validated_group = simple_validate(cleaned_group_data, CategoryGroup)

            # Create final response
            final_response = {
                "category": validated_category.model_dump(),
                "category_group": validated_group.model_dump(),
            }

            # Validate complete response structure
            validated_response = simple_validate(final_response, CategoryResponse)
            return validated_response

        except Exception:
            from ynab_http_mcp.debug import debug_exception

            debug_exception(
                f"Failed to validate category response for category {category_data.get('id', 'unknown')}"
            )

            # Return a fallback response if validation fails
            try:
                # Try to create basic objects even if validation failed
                basic_category = MCPCategory(**clean_ynab_data(category_data))
                basic_group = CategoryGroup(
                    id=group_data.get("id", ""),
                    name=group_data.get("name", ""),
                    hidden=group_data.get("hidden", False),
                    deleted=group_data.get("deleted", False),
                    categories=[basic_category],
                )
                fallback_response = CategoryResponse(
                    category=basic_category, category_group=basic_group
                )
                return fallback_response
            except Exception:
                # If all else fails, raise the original exception
                raise
