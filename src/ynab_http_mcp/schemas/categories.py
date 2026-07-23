"""
Simplified category schemas for YNAB HTTP MCP.

This module defines simplified Pydantic models for validating
YNAB category data using basic data types suitable for agents.
"""

from __future__ import annotations

from typing import Any, ClassVar, Dict, Optional, List, Self

from pydantic import Field

import ynab

from ynab_http_mcp.utils.schema_utils import clean_ynab_data

from .base import MCPResponse, uuid_type, date_type


# ---------------------------------------------------------------------------
# Goal explanation helpers (module-level so they can be unit-tested and
# reused without re-binding cls). Both helpers take a raw ``ynab.Category``
# and return a single human-readable sentence.
# ---------------------------------------------------------------------------


def _explain_goal_type(raw: ynab.Category) -> str:
    """Produce a one-sentence explanation of the category's goal type.

    Covers TB (Target Category Balance), TBD (Target Category Balance by
    Date), MF (Monthly Funding) with cadence values 0/1/2/3-12/13/14, NEED
    (Plan Your Spending), and an unknown fallback so the function is total.

    Cadence semantics (per YNAB SDK + spec convention):

    - Cadence 0 = one-time (no repetition)
    - Cadence 1 = Monthly: period = ``goal_cadence_frequency`` months
      (frequency 1 = monthly, 2 = every 2 months)
    - Cadence 2 = Weekly: period = ``goal_cadence_frequency`` weeks
      (frequency 1 = weekly, 2 = biweekly)
    - Cadences 3-12 = Every (N-1) months (frequency ignored)
    - Cadence 13 = Yearly: period = ``goal_cadence_frequency`` years
      (frequency 1 = yearly, 2 = every 2 years)
    - Cadence 14 = Every 2 years (frequency ignored)
    """
    goal_type = raw.goal_type
    target = raw.goal_target_formatted

    if goal_type == "TB":
        return (
            f"Target Category Balance: The goal is to reach a balance of "
            f"{target} in the category."
        )

    if goal_type == "TBD":
        return (
            f"Target Category Balance by Date: The goal is to reach a "
            f"balance of {target} in the category by {raw.goal_target_date}."
        )

    if goal_type == "MF":
        whole_amount = bool(raw.goal_needs_whole_amount)
        verb = "Set aside" if whole_amount else "Refill"
        cadence = raw.goal_cadence

        # Cadence 0 = one-time (no repetition)
        if cadence is None or cadence == 0:
            return (
                f"{verb}: The goal is to {verb.lower()} {target} for the "
                f"category by {raw.goal_target_date}."
            )

        # Cadence 1 = Monthly, period = frequency months
        # (cadence 1 is the base period, frequency is the multiplier)
        if cadence == 1:
            if raw.goal_cadence_frequency is None:
                raise ValueError(
                    "goal_cadence_frequency cannot be null for a standard "
                    "monthly goal for category "
                    f"{raw.name}"
                )
            return (
                f"{verb}: The goal is to {verb.lower()} {target} for the "
                f"category every {raw.goal_cadence_frequency} month(s)."
            )

        # Cadence 2 = Weekly, period = frequency weeks
        # (cadence 2 is the base period, frequency is the multiplier;
        #  frequency 1 = weekly, frequency 2 = biweekly)
        if cadence == 2:
            if raw.goal_cadence_frequency is None:
                raise ValueError(
                    "goal_cadence_frequency cannot be null for a standard "
                    "weekly goal for category "
                    f"{raw.name}"
                )
            return (
                f"{verb}: The goal is to {verb.lower()} {target} for the "
                f"category every {raw.goal_cadence_frequency} week(s)."
            )

        # Cadences 3-12 = Every (N-1) months (cadence_frequency is ignored)
        if 3 <= cadence <= 12:
            return (
                f"{verb}: The goal is to {verb.lower()} {target} for the "
                f"category every {cadence - 1} months."
            )

        # Cadence 13 = Yearly, period = frequency years
        # (cadence 13 is the base period, frequency is the multiplier;
        #  frequency 1 = yearly, frequency 2 = every 2 years)
        if cadence == 13:
            if raw.goal_cadence_frequency is None:
                raise ValueError(
                    "goal_cadence_frequency cannot be null for a standard "
                    "yearly goal for category "
                    f"{raw.name}"
                )
            return (
                f"{verb}: The goal is to {verb.lower()} {target} for the "
                f"category every {raw.goal_cadence_frequency} year(s)."
            )

        # Cadence 14 = Every 2 years (cadence_frequency is ignored)
        if cadence == 14:
            return (
                f"{verb}: The goal is to {verb.lower()} {target} for the "
                f"category every 2 years."
            )

        raise ValueError(
            f"Unrecognized goal cadence in category {raw.name}: goal_cadence {cadence}"
        )

    if goal_type == "NEED":
        return (
            "Plan Your Spending: The goal is to plan your spending for the "
            "category, ensuring you have enough funds available."
        )

    return f"Unknown goal type: {goal_type}"


def _explain_goal_funding_status(raw: ynab.Category) -> str:
    """Produce a one-sentence progress report for the category's goal.

    Reads ``goal_snoozed_at``, ``goal_percentage_complete``, ``goal_under_funded``,
    ``goal_overall_left``, ``goal_overall_funded``, ``goal_months_to_budget``,
    and ``goal_target`` so the LLM can summarise progress without raw integers.
    """
    if raw.goal_snoozed_at is not None:
        return f"Snoozed at {raw.goal_snoozed_at}."

    if raw.goal_target in (None, 0):
        return "No target set."

    percentage = raw.goal_percentage_complete or 0
    under_funded = raw.goal_under_funded_formatted
    overall_left = raw.goal_overall_left_formatted

    if percentage >= 100 or (
        raw.goal_overall_left is not None and raw.goal_overall_left <= 0
    ):
        return f"Fully funded ({percentage}% complete)."

    if raw.goal_under_funded is None or raw.goal_under_funded == 0:
        suffix = ""
        if raw.goal_months_to_budget and raw.goal_months_to_budget > 1:
            suffix = f" — {raw.goal_months_to_budget} months remaining in period."
        return f"On track this period ({percentage}% complete overall).{suffix}"

    months = raw.goal_months_to_budget or 1
    return (
        f"Underfunded by {under_funded} ({percentage}% complete overall, "
        f"{overall_left} left over {months} month(s))."
    )


# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------


class MCPCategoryGoal(MCPResponse[ynab.Category]):
    """Lean goal sub-model for a YNAB category, with LLM-friendly summary strings.

    The Lean layer exposes only 5 fields:

    - ``goal_type`` (filter key)
    - ``goal_target_date`` (date math)
    - ``goal_percentage_complete`` (sort / compare)
    - ``goal_summary`` (derived prose describing the goal type, target, cadence)
    - ``goal_status`` (derived progress sentence)

    Every other goal attribute the YNAB SDK exposes
    (``goal_under_funded``, ``goal_overall_left``, ``goal_cadence``,
    ``goal_cadence_frequency``, ``goal_target``, etc.) is dropped from
    the Lean layer and reachable only via the Full layer
    (``data://categories/{id}/full`` → ``full_details``).
    """

    goal_type: Optional[str] = Field(
        default=None,
        description=(
            "The type of goal, if the category has a goal (TB='Target "
            "Category Balance', TBD='Target Category Balance by Date', "
            "MF='Monthly Funding', NEED='Plan Your Spending')."
        ),
    )
    goal_target_date: Optional[date_type] = Field(
        default=None,
        description="The target date for the goal to be completed.",
    )
    goal_percentage_complete: Optional[int] = Field(
        default=None, description="The percentage completion of the goal."
    )
    goal_summary: Optional[str] = Field(
        default=None,
        description=(
            "Plain-English summary of what the goal is (goal type, target, cadence)."
        ),
    )
    goal_status: Optional[str] = Field(
        default=None,
        description=(
            "Plain-English progress sentence (underfunded, on track, fully "
            "funded, snoozed)."
        ),
    )

    @classmethod
    def from_ynab(cls, raw: ynab.Category) -> Self:
        """Build an ``MCPCategoryGoal`` from a raw ``ynab.Category``.

        Returns an empty instance (every field ``None``, including the
        summary strings) when the raw category has no goal.
        """
        if raw.goal_type is None:
            return cls()

        return cls(
            goal_type=raw.goal_type,
            goal_target_date=raw.goal_target_date,
            goal_percentage_complete=raw.goal_percentage_complete,
            goal_summary=_explain_goal_type(raw),
            goal_status=_explain_goal_funding_status(raw),
        )


class MCPCategory(MCPResponse[ynab.Category]):
    """
    Simplified category model using basic data types.

    Represents a YNAB category with all essential fields using simple
    types that are easily consumable by AI agents.
    """

    # Required identity / state fields
    id: uuid_type = Field(..., description="Unique category identifier")
    category_group_id: uuid_type = Field(
        ..., description="ID of the parent category group"
    )
    name: str = Field(..., description="Category name")
    hidden: bool = Field(..., description="Whether the category is hidden")
    internal: bool = Field(..., description="Whether the category is internal to YNAB")
    deleted: bool = Field(..., description="Whether the category is deleted")

    # Currency fields — YNAB already formats these for the plan's locale.
    budgeted_formatted: Optional[str] = Field(
        default=None, description="Budgeted amount with currency formatting"
    )
    activity_formatted: Optional[str] = Field(
        default=None, description="Activity amount with currency formatting"
    )
    balance_formatted: Optional[str] = Field(
        default=None, description="Balance with currency formatting"
    )

    # Nested goal sub-model
    goal: Optional[MCPCategoryGoal] = Field(
        default=None, description="Goal attached to this category, if any"
    )

    @classmethod
    def from_ynab(cls, raw: ynab.Category | ynab.CategoryResponse) -> Self:
        """Build an ``MCPCategory`` from a raw ``ynab.Category`` or wrapped
        ``ynab.CategoryResponse``.
        """
        if isinstance(raw, ynab.CategoryResponse):
            raw = raw.data.category

        return cls(
            id=raw.id,
            category_group_id=raw.category_group_id,
            name=raw.name,
            hidden=raw.hidden,
            internal=raw.internal,
            deleted=raw.deleted,
            budgeted_formatted=raw.budgeted_formatted,
            activity_formatted=raw.activity_formatted,
            balance_formatted=raw.balance_formatted,
            goal=MCPCategoryGoal.from_ynab(raw),
        )


class MCPCategoryGroup(MCPResponse[ynab.CategoryGroupWithCategories]):
    """
    Simplified category-group model.

    Represents a YNAB category group and the categories that live under it.
    Mirrors ``MCPAccount`` / ``MCPAccounts``: typed, ``MCPResponse``-backed,
    exposes a ``HIDE_DELETED`` class constant and a ``from_ynab`` classmethod.
    """

    HIDE_DELETED: ClassVar[bool] = True

    id: uuid_type = Field(..., description="Unique category group identifier")
    name: str = Field(..., description="Category group name")
    hidden: bool = Field(..., description="Whether the group is hidden")
    internal: bool = Field(..., description="Whether the group is internal to YNAB")
    deleted: bool = Field(..., description="Whether the group is deleted")
    categories: List[MCPCategory] = Field(
        default_factory=list,
        description="Categories that live under this group",
    )

    @classmethod
    def from_ynab(cls, raw: ynab.CategoryGroupWithCategories) -> Self:
        categories: List[MCPCategory] = []
        for ynab_category in raw.categories or []:
            if cls.HIDE_DELETED and ynab_category.deleted:
                continue
            categories.append(MCPCategory.from_ynab(ynab_category))
        return cls(
            id=raw.id,
            name=raw.name,
            hidden=raw.hidden,
            internal=raw.internal,
            deleted=raw.deleted,
            categories=categories,
        )


class MCPCategories(MCPResponse[ynab.CategoriesResponse]):
    """
    Grouped-list wrapper for a YNAB categories response.

    Iterates the raw ``category_groups`` envelope and emits a list of
    ``MCPCategoryGroup``, each carrying its own filtered ``categories`` list.
    Wire shape matches the YNAB-native ``{"category_groups": [...]}`` form.
    """

    HIDE_DELETED: ClassVar[bool] = True
    category_groups: List[MCPCategoryGroup] = Field(
        default_factory=list, description="List of category groups"
    )

    @classmethod
    def from_ynab(cls, raw: ynab.CategoriesResponse) -> Self:
        groups: List[MCPCategoryGroup] = []
        for ynab_group in raw.data.category_groups or []:
            if cls.HIDE_DELETED and ynab_group.deleted:
                continue
            groups.append(MCPCategoryGroup.from_ynab(ynab_group))
        return cls(category_groups=groups)


# ---------------------------------------------------------------------------
# Full layer — inherits every lean field and adds one ``full_details`` dict
# carrying the cleaned raw ``ynab.Category`` for the same entity. The Full
# layer is the drill-in escape hatch for fields the Lean layer dropped
# (``note``, integer milliunit budget/activity/balance, the full goal raw
# field set, etc.).
# ---------------------------------------------------------------------------


class MCPCategoryFull(MCPCategory):
    """Full sibling of ``MCPCategory`` — same lean fields plus ``full_details``.

    Built from a raw ``ynab.Category`` (or wrapped ``ynab.CategoryResponse``)
    via ``MCPCategoryFull.from_ynab``; the lean fields are populated by the
    parent ``from_ynab`` and ``full_details`` is the cleaned raw dict.
    """

    full_details: Dict[str, Any] = Field(
        default_factory=dict,
        description=(
            "Cleaned raw ``ynab.Category`` as a dict. Contains every field the "
            "YNAB SDK exposes for a category, including fields the Lean layer "
            "dropped (``note``, integer milliunit budget/activity/balance, the "
            "full goal raw field set, etc.). UUIDs are strings, datetimes are "
            "ISO dates, and YNAB-specific import fields are removed."
        ),
    )

    @classmethod
    def from_ynab(cls, raw: ynab.Category | ynab.CategoryResponse) -> Self:
        """Build an ``MCPCategoryFull`` from a raw ``ynab.Category``.

        Reuses the lean ``MCPCategory.from_ynab`` to populate the lean fields,
        then attaches the cleaned raw ``to_dict()`` under ``full_details``.
        """
        if isinstance(raw, ynab.CategoryResponse):
            raw_cat: ynab.Category = raw.data.category
        else:
            raw_cat = raw

        lean = MCPCategory.from_ynab(raw_cat)
        return cls(
            **lean.model_dump(),
            full_details=clean_ynab_data(raw_cat.to_dict()),
        )
