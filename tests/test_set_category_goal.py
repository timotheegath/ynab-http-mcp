"""
Tests for the combined ``SetCategoryGoalRequest`` schema.

The three former goal tools (recurring / target-by-date / clear) are now one
``set_category_goal`` tool; these tests pin the goal_type field combinations
the validator accepts and rejects, and the mapping to
``UpdateCategoryRequest`` (including the goal_target=0 clear signal).
"""

import pytest
from pydantic import ValidationError

from ynab_http_mcp.schemas.budget_tools import SetCategoryGoalRequest

CAT = "123e4567-e89b-12d3-a456-426614174000"


def test_monthly_goal_maps_to_target_only():
    req = SetCategoryGoalRequest(
        category_id=CAT, goal_type="monthly", goal_target=50000
    )
    out = req.to_update_category_request()
    assert out.goal_target == 50000
    assert out.goal_target_date is None
    assert out.goal_needs_whole_amount is None
    assert out.goal_frequency is None


def test_recurring_goal_maps_all_fields():
    req = SetCategoryGoalRequest(
        category_id=CAT,
        goal_type="recurring",
        goal_target=50000,
        goal_needs_whole_amount=True,
        goal_frequency="weekly",
    )
    out = req.to_update_category_request()
    assert out.goal_target == 50000
    assert out.goal_needs_whole_amount is True
    assert out.goal_frequency == "weekly"
    assert out.goal_target_date is None


def test_target_by_date_goal_maps_date():
    req = SetCategoryGoalRequest(
        category_id=CAT,
        goal_type="target_by_date",
        goal_target=3000000,
        goal_target_date="2026-12-01",
    )
    out = req.to_update_category_request()
    assert out.goal_target == 3000000
    assert out.goal_target_date == "2026-12-01"
    assert out.goal_frequency is None


def test_clear_goal_maps_to_zero_target_signal():
    req = SetCategoryGoalRequest(category_id=CAT, goal_type="clear")
    out = req.to_update_category_request()
    # goal_target=0 with no other goal fields is the service-level clear signal
    assert out.goal_target == 0
    assert out.goal_target_date is None
    assert out.goal_needs_whole_amount is None
    assert out.goal_frequency is None


def test_note_passes_through():
    req = SetCategoryGoalRequest(
        category_id=CAT, goal_type="clear", note="no longer needed"
    )
    assert req.to_update_category_request().note == "no longer needed"


@pytest.mark.parametrize(
    "payload",
    [
        # clear takes no goal fields
        {"goal_type": "clear", "goal_target": 1000},
        # non-clear types require goal_target
        {"goal_type": "monthly"},
        {
            "goal_type": "recurring",
            "goal_needs_whole_amount": True,
            "goal_frequency": "monthly",
        },
        {"goal_type": "target_by_date", "goal_target_date": "2026-12-01"},
        # monthly takes only goal_target
        {"goal_type": "monthly", "goal_target": 1000, "goal_frequency": "monthly"},
        # target_by_date requires the date and rejects frequency fields
        {"goal_type": "target_by_date", "goal_target": 1000},
        {
            "goal_type": "target_by_date",
            "goal_target": 1000,
            "goal_target_date": "2026-12-01",
            "goal_frequency": "monthly",
        },
        # recurring requires needs_whole_amount + frequency, rejects date
        {"goal_type": "recurring", "goal_target": 1000, "goal_frequency": "monthly"},
        {
            "goal_type": "recurring",
            "goal_target": 1000,
            "goal_needs_whole_amount": True,
        },
        {
            "goal_type": "recurring",
            "goal_target": 1000,
            "goal_needs_whole_amount": True,
            "goal_frequency": "monthly",
            "goal_target_date": "2026-12-01",
        },
    ],
)
def test_invalid_goal_combinations_rejected(payload):
    with pytest.raises(ValidationError):
        SetCategoryGoalRequest(category_id=CAT, **payload)


def test_category_id_pattern_enforced():
    with pytest.raises(ValidationError):
        SetCategoryGoalRequest(category_id="not-a-uuid", goal_type="clear")
