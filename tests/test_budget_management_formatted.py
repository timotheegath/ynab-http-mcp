"""
Active focused tests for budget management tool formatted fields.

Exercises the actual registered FastMCP tools (check_budget_health,
get_spending_insights) via fastmcp.client.Client with a mocked
YnabService, verifying that formatted currency strings are present,
correct for negative values, preserved in nested entries, and that
raw milliunit fields are kept unchanged.
"""

from __future__ import annotations

import json
import os
from unittest.mock import Mock, MagicMock
from datetime import date
from uuid import UUID

import pytest

os.environ.setdefault("YNAB_API_KEY", "00000000-0000-0000-0000-000000000000")
os.environ.setdefault("ENVIRONMENT", "dev")

from fastmcp import FastMCP
from fastmcp.client import Client
from fastmcp.server.transforms import ResourcesAsTools

from ynab_http_mcp.ynab_service import YnabService
from ynab_http_mcp.schemas.transaction_aggregate import _ynab_format


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _call_tool(client: Client, name: str, arguments: dict) -> dict:
    """Synchronous wrapper around ``client.call_tool``."""
    import asyncio

    async def _run():
        async with client:
            result = await client.call_tool(name, arguments)
        for item in result.content:
            if item.type == "text":
                return json.loads(item.text)
        raise RuntimeError("No text content in tool result")

    return asyncio.run(_run())


def _mock_category(
    cat_id: str,
    name: str,
    budgeted: int,
    activity: int,
    balance: int,
    budgeted_f: str | None = None,
    activity_f: str | None = None,
    balance_f: str | None = None,
) -> MagicMock:
    cat = MagicMock()
    cat.id = UUID(cat_id) if len(cat_id) == 36 else cat_id
    cat.name = name
    cat.budgeted = budgeted
    cat.activity = activity
    cat.balance = balance
    cat.budgeted_formatted = budgeted_f
    cat.activity_formatted = activity_f
    cat.balance_formatted = balance_f
    return cat


def _mock_month_detail(
    budgeted: int,
    activity: int,
    tbb: int,
    categories: list,
    budgeted_f: str | None = None,
    activity_f: str | None = None,
    tbb_f: str | None = None,
) -> MagicMock:
    md = MagicMock()
    md.month = date(2024, 1, 1)
    md.budgeted = budgeted
    md.activity = activity
    md.to_be_budgeted = tbb
    md.categories = categories
    md.budgeted_formatted = budgeted_f
    md.activity_formatted = activity_f
    md.to_be_budgeted_formatted = tbb_f
    return md


def _mock_transaction(
    amount: int,
    cat_id: str | None = None,
    cat_name: str | None = None,
    amount_f: str | None = None,
) -> MagicMock:
    txn = MagicMock()
    txn.amount = amount
    txn.category_id = cat_id
    txn.category_name = cat_name
    txn.amount_formatted = amount_f
    return txn


def _build_client(service: Mock) -> Client:
    """Register real budget_management tools with a mocked service."""
    mcp = FastMCP("ynab")
    import ynab_http_mcp.tools.budget_management as bt

    bt.register(mcp, service)
    mcp.add_transform(ResourcesAsTools(mcp))
    return Client(mcp)


# ---------------------------------------------------------------------------
# Pure-helper unit test (no FastMCP needed)
# ---------------------------------------------------------------------------


class TestYnabFormat:
    """Exercises _ynab_format directly — pure function, no mocking."""

    def test_positive_value(self):
        assert _ynab_format(50000, "$0.00") == "$50.00"

    def test_negative_value(self):
        assert _ynab_format(-50000, "$0.00") == "-$50.00"

    def test_zero_value(self):
        assert _ynab_format(0, "$0.00") == "$0.00"

    def test_truncation_not_rounding(self):
        assert _ynab_format(-123456, "$0.00") == "-$123.45"

    def test_thousands_separator(self):
        assert _ynab_format(-1234567, "$0.00") == "-$1,234.56"

    def test_no_template_fallback(self):
        assert _ynab_format(1000) == "$1.00"

    def test_negative_sdk_template(self):
        assert _ynab_format(-50000, "-$50.00") == "-$50.00"


# ---------------------------------------------------------------------------
# check_budget_health — via FastMCP tool call
# ---------------------------------------------------------------------------


class TestCheckBudgetHealthTool:
    """Calls the actual registered check_budget_health tool with mock data."""

    @pytest.fixture
    def mock_service(self):
        return Mock(spec=YnabService)

    # --- top-level formatted fields ---

    def test_top_level_formatted(self, mock_service):
        cat = _mock_category(
            "00000000-0000-0000-0000-000000000001",
            "Groceries",
            40000,
            30000,
            10000,
            budgeted_f="$400.00",
            activity_f="$300.00",
            balance_f="$100.00",
        )
        md = _mock_month_detail(
            80000,
            60000,
            20000,
            [cat],
            budgeted_f="$800.00",
            activity_f="$600.00",
            tbb_f="$200.00",
        )
        mock_service.get_plan_month.return_value.data.month = md

        client = _build_client(mock_service)
        result = _call_tool(client, "check_budget_health", {"month": "2024-01"})

        # Raw fields preserved
        assert result["total_budgeted"] == 80000
        assert result["total_activity"] == 60000
        assert result["to_be_budgeted"] == 20000
        # Formatted
        assert result["total_budgeted_formatted"] == "$800.00"
        assert result["total_activity_formatted"] == "$600.00"
        assert result["to_be_budgeted_formatted"] == "$200.00"

    def test_negative_activity_formatted(self, mock_service):
        cat = _mock_category(
            "00000000-0000-0000-0000-000000000001",
            "Groceries",
            40000,
            -5000,
            10000,
            budgeted_f="$400.00",
            activity_f="-$50.00",
            balance_f="$100.00",
        )
        md = _mock_month_detail(
            80000,
            -5000,
            20000,
            [cat],
            budgeted_f="$800.00",
            activity_f="-$50.00",
            tbb_f="$200.00",
        )
        mock_service.get_plan_month.return_value.data.month = md

        client = _build_client(mock_service)
        result = _call_tool(client, "check_budget_health", {"month": "2024-01"})

        assert result["total_activity_formatted"] == "-$50.00"
        entry = result["category_health"]["00000000-0000-0000-0000-000000000001"]
        assert entry["activity_formatted"] == "-$50.00"

    # --- nested category formatted fields ---

    def test_category_formatted_present(self, mock_service):
        cat1 = _mock_category(
            "00000000-0000-0000-0000-000000000001",
            "Groceries",
            40000,
            30000,
            10000,
            budgeted_f="$400.00",
            activity_f="$300.00",
            balance_f="$100.00",
        )
        md = _mock_month_detail(
            60000,
            45000,
            5000,
            [cat1],
            budgeted_f="$600.00",
            activity_f="$450.00",
            tbb_f="$50.00",
        )
        mock_service.get_plan_month.return_value.data.month = md

        client = _build_client(mock_service)
        result = _call_tool(client, "check_budget_health", {"month": "2024-01"})

        entry = result["category_health"]["00000000-0000-0000-0000-000000000001"]
        assert entry["budgeted_formatted"] == "$400.00"
        assert entry["activity_formatted"] == "$300.00"
        assert entry["balance_formatted"] == "$100.00"
        # Raw milliunits also present
        assert entry["budgeted"] == 40000
        assert entry["activity"] == 30000
        assert entry["balance"] == 10000

    def test_formatted_fallback_when_sdk_none(self, mock_service):
        """When SDK formatted fields are None, _ynab_format fallback fires."""
        cat = _mock_category(
            "00000000-0000-0000-0000-000000000001",
            "Groceries",
            40000,
            30000,
            10000,
        )
        md = _mock_month_detail(80000, 60000, 20000, [cat])
        mock_service.get_plan_month.return_value.data.month = md

        client = _build_client(mock_service)
        result = _call_tool(client, "check_budget_health", {"month": "2024-01"})

        # Fallback uses default "$0.00" template since no SDK formatted template
        assert result["total_budgeted_formatted"] == "$80.00"
        entry = result["category_health"]["00000000-0000-0000-0000-000000000001"]
        assert entry["budgeted_formatted"] == "$40.00"


# ---------------------------------------------------------------------------
# get_spending_insights — via FastMCP tool call
# ---------------------------------------------------------------------------


class TestGetSpendingInsightsTool:
    """Calls the actual registered get_spending_insights tool with mock data."""

    @pytest.fixture
    def mock_service(self):
        return Mock(spec=YnabService)

    def test_top_level_formatted(self, mock_service):
        txns = [
            _mock_transaction(-50000, "cat-1", "Groceries", "-$50.00"),
            _mock_transaction(-30000, "cat-1", "Groceries", "-$30.00"),
            _mock_transaction(-20000, "cat-2", "Dining Out", "-$20.00"),
        ]
        resp = MagicMock()
        resp.data.transactions = txns
        mock_service.get_transactions.return_value = resp

        client = _build_client(mock_service)
        result = _call_tool(client, "get_spending_insights", {"month": "2024-01"})

        # Raw fields
        assert result["total_spending"] == -100000
        assert result["transaction_count"] == 3

        # Formatted: total = -$100.00, avg rounded to -33333 milli -> -$33.33
        assert result["total_spending_formatted"] == "-$100.00"
        assert result["average_transaction_formatted"] == "-$33.33"

    def test_empty_transactions_fallback(self, mock_service):
        resp = MagicMock()
        resp.data.transactions = []
        mock_service.get_transactions.return_value = resp

        client = _build_client(mock_service)
        result = _call_tool(client, "get_spending_insights", {"month": "2024-01"})

        assert result["total_spending"] == 0
        assert result["average_transaction"] == 0
        assert result["total_spending_formatted"] == "$0.00"
        assert result["average_transaction_formatted"] == "$0.00"

    def test_category_insights_total_formatted(self, mock_service):
        txns = [
            _mock_transaction(-50000, "cat-1", "Groceries", "-$50.00"),
            _mock_transaction(-30000, "cat-1", "Groceries", "-$30.00"),
            _mock_transaction(-20000, "cat-2", "Dining Out", "-$20.00"),
        ]
        resp = MagicMock()
        resp.data.transactions = txns
        mock_service.get_transactions.return_value = resp

        client = _build_client(mock_service)
        result = _call_tool(client, "get_spending_insights", {"month": "2024-01"})

        cat1 = result["category_insights"]["cat-1"]
        assert cat1["total_formatted"] == "-$80.00"
        assert cat1["total"] == -80000

        cat2 = result["category_insights"]["cat-2"]
        assert cat2["total_formatted"] == "-$20.00"
        assert cat2["total"] == -20000

    def test_raw_fields_preserved(self, mock_service):
        txns = [
            _mock_transaction(-50000, "cat-1", "Groceries", "-$50.00"),
        ]
        resp = MagicMock()
        resp.data.transactions = txns
        mock_service.get_transactions.return_value = resp

        client = _build_client(mock_service)
        result = _call_tool(client, "get_spending_insights", {"month": "2024-01"})

        assert result["total_spending"] == -50000
        assert isinstance(result["total_spending"], int)
        assert isinstance(result["average_transaction"], float)

    def test_negative_spending_formatted(self, mock_service):
        txns = [
            _mock_transaction(-75000, "cat-1", "Bills", "-$75.00"),
        ]
        resp = MagicMock()
        resp.data.transactions = txns
        mock_service.get_transactions.return_value = resp

        client = _build_client(mock_service)
        result = _call_tool(client, "get_spending_insights", {"month": "2024-01"})

        assert result["total_spending_formatted"] == "-$75.00"
        assert result["average_transaction_formatted"] == "-$75.00"


if __name__ == "__main__":
    import sys

    sys.exit(pytest.main([__file__, "-v"]))
