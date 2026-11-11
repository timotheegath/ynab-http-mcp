"""
Focused tests for the exclusion of YNAB's internal categories.

YNAB exposes one internal bookkeeping category per plan — "Inflow: Ready to
Assign" — whose balance is a cumulative Ready-to-Assign artifact rather than
money assigned to a spendable category. Summing it with the real category
balances produces a meaningless total, so it must never reach a category
listing nor any balance aggregate built over one.
"""

from __future__ import annotations

import asyncio
import json
import os
from unittest.mock import Mock
from uuid import UUID

import pytest
import ynab

os.environ.setdefault("YNAB_API_KEY", "00000000-0000-0000-0000-000000000000")
os.environ.setdefault("ENVIRONMENT", "dev")

from fastmcp import FastMCP
from fastmcp.client import Client

from ynab_http_mcp.schemas.categories import MCPCategories
from ynab_http_mcp.schemas.planning import PlanMonth, PlanMonthFull
from ynab_http_mcp.ynab_service import YnabService


INTERNAL_CATEGORY_ID = "00000000-0000-0000-0000-0000000000ff"
SPENDABLE_CATEGORY_ID = "00000000-0000-0000-0000-000000000001"
INTERNAL_GROUP_ID = "33333333-3333-3333-3333-333333333333"
SPENDABLE_GROUP_ID = "11111111-1111-1111-1111-111111111111"


# ---------------------------------------------------------------------------
# Fixtures / builders
# ---------------------------------------------------------------------------


def _category(
    cat_id: str,
    name: str,
    balance: int,
    internal: bool = False,
) -> dict:
    """Build a raw YNAB category payload."""
    return {
        "id": cat_id,
        "category_group_id": INTERNAL_GROUP_ID if internal else SPENDABLE_GROUP_ID,
        "name": name,
        "hidden": False,
        "internal": internal,
        "deleted": False,
        "budgeted": 500000,
        "activity": -100000,
        "balance": balance,
        "budgeted_formatted": "$500.00",
        "activity_formatted": "-$100.00",
        "balance_formatted": f"${balance / 1000:,.2f}",
    }


def _categories_response() -> ynab.CategoriesResponse:
    internal_cat = _category(
        INTERNAL_CATEGORY_ID, "Inflow: Ready to Assign", 126466520, internal=True
    )
    spendable_cat = _category(SPENDABLE_CATEGORY_ID, "Groceries", 200000)
    return ynab.CategoriesResponse(
        data=ynab.CategoriesResponseData(
            category_groups=[
                ynab.CategoryGroupWithCategories(
                    id=UUID(INTERNAL_GROUP_ID),
                    name="Internal Master Category",
                    hidden=False,
                    internal=True,
                    deleted=False,
                    categories=[internal_cat],
                ),
                ynab.CategoryGroupWithCategories(
                    id=UUID(SPENDABLE_GROUP_ID),
                    name="Bills",
                    hidden=False,
                    internal=False,
                    deleted=False,
                    categories=[spendable_cat],
                ),
            ],
            server_knowledge=0,
        ),
    )


def _month_detail_response() -> ynab.MonthDetailResponse:
    return ynab.MonthDetailResponse.model_validate(
        {
            "data": {
                "month": {
                    "month": "2026-07-01",
                    "income": 5000000,
                    "budgeted": 4000000,
                    "activity": -3000000,
                    "to_be_budgeted": 1000000,
                    "age_of_money": 30,
                    "deleted": False,
                    "categories": [
                        _category(
                            INTERNAL_CATEGORY_ID,
                            "Inflow: Ready to Assign",
                            126466520,
                            internal=True,
                        ),
                        _category(SPENDABLE_CATEGORY_ID, "Groceries", 200000),
                    ],
                }
            }
        }
    )


def _read_resource(uri: str, service: Mock) -> dict:
    """Register the category tools against a mocked service and read a URI."""
    mcp = FastMCP("ynab")
    import ynab_http_mcp.tools.categories as category_tools

    category_tools.register(mcp, service)

    async def _run() -> dict:
        async with Client(mcp) as client:
            contents = await client.read_resource(uri)
        return json.loads(contents[0].text)  # type: ignore[union-attr]

    return asyncio.run(_run())


# ---------------------------------------------------------------------------
# data://categories — the resource the feedback is about
# ---------------------------------------------------------------------------


class TestCategoriesResourceExcludesInternal:
    def test_wire_payload_has_no_internal_category(self) -> None:
        service = Mock(spec=YnabService)
        service.get_categories.return_value = _categories_response()

        payload = _read_resource("data://categories", service)
        payload_text = json.dumps(payload)

        # Neither the internal group nor its pseudo-category is reported.
        assert "Inflow: Ready to Assign" not in payload_text
        assert "Internal Master Category" not in payload_text
        # The spendable category survives.
        assert "Groceries" in payload_text

    def test_listing_balances_sum_to_a_real_total(self) -> None:
        result = MCPCategories.from_ynab(_categories_response())

        balances = [
            category.balance_formatted
            for group in result.category_groups
            for category in group.categories
        ]
        # $126,466.52 of internal Ready-to-Assign is not part of the sum.
        assert balances == ["$200.00"]


# ---------------------------------------------------------------------------
# data://months/{ym} — the other balance-bearing surface
# ---------------------------------------------------------------------------


class TestPlanMonthExcludesInternal:
    def test_lean_month_drops_internal_category(self) -> None:
        result = PlanMonth.from_ynab_response(_month_detail_response())

        assert [c.category_name for c in result.categories] == ["Groceries"]
        assert [c.category_id for c in result.categories] == [SPENDABLE_CATEGORY_ID]

    def test_full_month_drops_internal_category_from_full_details(self) -> None:
        result = PlanMonthFull.from_ynab_response(_month_detail_response())

        assert [c.category_name for c in result.categories] == ["Groceries"]

        raw_categories = result.full_details["categories"]
        assert [c["name"] for c in raw_categories] == ["Groceries"]
        assert "Inflow: Ready to Assign" not in json.dumps(result.full_details)

    def test_ready_to_assign_still_available_on_the_month(self) -> None:
        # The information the internal category carried is not lost: the
        # month envelope still reports Ready to Assign as to_be_budgeted.
        result = PlanMonth.from_ynab_response(_month_detail_response())

        assert result.to_be_budgeted == 1000000


if __name__ == "__main__":
    import sys

    sys.exit(pytest.main([__file__, "-v"]))
