#!/usr/bin/env python3
"""
Unit tests for the plans module.
"""

import pytest
from datetime import datetime, timezone
from uuid import UUID
from ynab import PlanSummaryResponse
from ynab.models.plan_summary_response_data import PlanSummaryResponseData
from ynab.models.plan_summary import PlanSummary

# Import the function to test
from ynab_http_mcp.ynab_service import YnabService


def test_find_latest_plan_empty():
    """Test find_latest_plan with empty plans."""
    # Create an empty PlanSummaryResponse
    empty_response = PlanSummaryResponse(data=PlanSummaryResponseData(plans=[]))

    result = YnabService._find_latest_plan(empty_response)
    assert result is None


def test_find_latest_plan_single():
    """Test find_latest_plan with a single plan."""
    # Create a single plan
    plan_id = UUID("12345678-1234-5678-1234-567812345678")
    last_modified = datetime(2023, 1, 15, 10, 30, 0, tzinfo=timezone.utc)

    plan = PlanSummary(id=plan_id, name="Test Plan", last_modified_on=last_modified)

    response = PlanSummaryResponse(data=PlanSummaryResponseData(plans=[plan]))

    result = YnabService._find_latest_plan(response)
    assert result == plan_id


def test_find_latest_plan_multiple():
    """Test find_latest_plan with multiple plans."""
    # Create multiple plans with different modification times
    plan1_id = UUID("12345678-1234-5678-1234-567812345678")
    plan2_id = UUID("87654321-4321-8765-4321-876543218765")
    plan3_id = UUID("11111111-1111-1111-1111-111111111111")

    # Plan 1: oldest
    plan1 = PlanSummary(
        id=plan1_id,
        name="Old Plan",
        last_modified_on=datetime(2023, 1, 1, 0, 0, 0, tzinfo=timezone.utc),
    )

    # Plan 2: middle
    plan2 = PlanSummary(
        id=plan2_id,
        name="Middle Plan",
        last_modified_on=datetime(2023, 1, 15, 12, 0, 0, tzinfo=timezone.utc),
    )

    # Plan 3: newest
    plan3 = PlanSummary(
        id=plan3_id,
        name="New Plan",
        last_modified_on=datetime(2023, 2, 1, 18, 30, 0, tzinfo=timezone.utc),
    )

    response = PlanSummaryResponse(
        data=PlanSummaryResponseData(plans=[plan1, plan2, plan3])
    )

    result = YnabService._find_latest_plan(response)
    assert result == plan3_id  # Should return the newest plan


def test_find_latest_plan_with_none_timestamps():
    """Test find_latest_plan when some plans have None last_modified_on."""
    plan1_id = UUID("12345678-1234-5678-1234-567812345678")
    plan2_id = UUID("87654321-4321-8765-4321-876543218765")

    # Plan 1: has timestamp
    plan1 = PlanSummary(
        id=plan1_id,
        name="Plan with timestamp",
        last_modified_on=datetime(2023, 1, 15, 10, 0, 0, tzinfo=timezone.utc),
    )

    # Plan 2: no timestamp (None)
    plan2 = PlanSummary(
        id=plan2_id, name="Plan without timestamp", last_modified_on=None
    )

    response = PlanSummaryResponse(data=PlanSummaryResponseData(plans=[plan1, plan2]))

    result = YnabService._find_latest_plan(response)
    assert result == plan1_id  # Should return the plan with timestamp


def test_find_latest_plan_all_none_timestamps():
    """Test find_latest_plan when all plans have None last_modified_on."""
    plan1_id = UUID("12345678-1234-5678-1234-567812345678")
    plan2_id = UUID("87654321-4321-8765-4321-876543218765")

    # Both plans have None timestamps
    plan1 = PlanSummary(id=plan1_id, name="Plan 1", last_modified_on=None)

    plan2 = PlanSummary(id=plan2_id, name="Plan 2", last_modified_on=None)

    response = PlanSummaryResponse(data=PlanSummaryResponseData(plans=[plan1, plan2]))

    # This should still work and return one of the plans
    # The behavior with all None timestamps is undefined, but shouldn't crash
    result = YnabService._find_latest_plan(response)
    assert result in [plan1_id, plan2_id]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
