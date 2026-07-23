"""
Unit tests for the transaction aggregate computation.

Covers the empty window, single month, multi-month, top-N truncation,
unassigned payee / uncategorized, the increasing / stable / decreasing
trend classification, and the error path.
"""

from __future__ import annotations

from datetime import date
from uuid import uuid4

import ynab

from ynab_http_mcp.schemas.transaction_aggregate import (
    ClearedBreakdown,
    TransactionInsightsResponse,
    _classify_trend,
    _default_window,
    _months_in_window,
    build_transaction_insights,
)


def _make_tx(
    amount: int,
    txn_date: date,
    *,
    payee_id: str | None = "11111111-1111-1111-1111-111111111111",
    payee_name: str | None = "Test Payee",
    category_id: str | None = "22222222-2222-2222-2222-222222222222",
    category_name: str | None = "Test Cat",
    cleared: str = "cleared",
) -> ynab.TransactionDetail:
    """Build a single ``ynab.TransactionDetail`` for testing."""
    sign = "-" if amount < 0 else ""
    abs_amount = abs(amount)
    whole = abs_amount // 1000
    cents = abs_amount % 1000
    amount_formatted = f"{sign}${whole}.{cents:02d}"
    payload = {
        "id": str(uuid4()),
        "date": txn_date,
        "amount": amount,
        "cleared": cleared,
        "approved": True,
        "account_id": str(uuid4()),
        "account_name": "Test",
        "payee_id": payee_id,
        "payee_name": payee_name,
        "category_id": category_id,
        "category_name": category_name,
        "deleted": False,
        "amount_formatted": amount_formatted,
        "subtransactions": [],
    }
    return ynab.TransactionDetail.model_validate(payload)


# ---------------------------------------------------------------------------
# Window helpers
# ---------------------------------------------------------------------------


class TestDefaultWindow:
    def test_default_window_is_three_months(self) -> None:
        from datetime import date

        # Use a known today to make this test deterministic.
        today = date(2025, 3, 15)
        since, until = _default_window(today)
        assert since == date(2025, 1, 1)
        assert until == date(2025, 4, 1)
        assert (until.year - since.year) * 12 + (until.month - since.month) == 3

    def test_months_in_window(self) -> None:
        months = _months_in_window(date(2024, 1, 1), date(2024, 4, 1))
        assert [m.strftime("%Y-%m") for m in months] == [
            "2024-01",
            "2024-02",
            "2024-03",
        ]


class TestClassifyTrend:
    def test_stable(self) -> None:
        # Constant outflows across 3 months
        assert _classify_trend([-100, -100, -100]) == "stable"

    def test_increasing(self) -> None:
        # Outflow magnitude growing month over month
        assert _classify_trend([-100, -200, -300]) == "increasing"

    def test_decreasing(self) -> None:
        # Outflow magnitude shrinking month over month
        assert _classify_trend([-300, -200, -100]) == "decreasing"

    def test_single_point_is_stable(self) -> None:
        # One data point is not enough for a directional read
        assert _classify_trend([-100]) == "stable"


# ---------------------------------------------------------------------------
# build_transaction_insights
# ---------------------------------------------------------------------------


class TestBuildInsights:
    def test_empty_window(self) -> None:
        result = build_transaction_insights([], date(2024, 1, 1), date(2024, 4, 1))
        assert result.transaction_count == 0
        assert result.spending_trend == "stable"
        assert result.total_inflow_formatted == "$0.00"
        assert result.total_outflow_formatted == "$0.00"
        assert result.net_formatted == "$0.00"
        # 3 calendar months, zero-filled
        assert len(result.monthly_buckets) == 3
        assert [b.month for b in result.monthly_buckets] == [
            "2024-01",
            "2024-02",
            "2024-03",
        ]
        for b in result.monthly_buckets:
            assert b.transaction_count == 0
            assert b.inflow_formatted == "$0.00"
            assert b.outflow_formatted == "$0.00"
            assert b.net_formatted == "$0.00"
            assert b.average_transaction_formatted == "$0.00"
        assert result.top_payees == []
        assert result.top_categories == []
        assert result.by_cleared_status == ClearedBreakdown(
            cleared=0, uncleared=0, reconciled=0
        )
        assert result.period_start == "2024-01-01"
        assert result.period_end == "2024-04-01"
        assert result.error is None

    def test_single_month(self) -> None:
        tx = _make_tx(-50000, date(2024, 1, 15))
        result = build_transaction_insights([tx], date(2024, 1, 1), date(2024, 2, 1))
        assert result.transaction_count == 1
        assert len(result.monthly_buckets) == 1
        assert result.monthly_buckets[0].month == "2024-01"
        assert result.monthly_buckets[0].transaction_count == 1
        assert result.monthly_buckets[0].outflow_formatted == "-$50.00"
        assert result.monthly_buckets[0].inflow_formatted == "$0.00"
        assert result.monthly_buckets[0].net_formatted == "-$50.00"
        assert result.monthly_buckets[0].average_transaction_formatted == "-$50.00"
        assert result.total_outflow_formatted == "-$50.00"
        assert result.total_inflow_formatted == "$0.00"
        assert result.net_formatted == "-$50.00"
        # Single month → stable (no directional read)
        assert result.spending_trend == "stable"

    def test_multi_month_increasing(self) -> None:
        txs = [
            _make_tx(-10000, date(2024, 1, 15)),
            _make_tx(-20000, date(2024, 2, 15)),
            _make_tx(-30000, date(2024, 3, 15)),
        ]
        result = build_transaction_insights(txs, date(2024, 1, 1), date(2024, 4, 1))
        assert result.transaction_count == 3
        assert result.spending_trend == "increasing"
        assert result.total_outflow_formatted == "-$60.00"
        assert [b.transaction_count for b in result.monthly_buckets] == [1, 1, 1]
        assert [b.outflow_formatted for b in result.monthly_buckets] == [
            "-$10.00",
            "-$20.00",
            "-$30.00",
        ]

    def test_multi_month_stable(self) -> None:
        txs = [
            _make_tx(-20000, date(2024, 1, 15)),
            _make_tx(-20000, date(2024, 2, 15)),
            _make_tx(-20000, date(2024, 3, 15)),
        ]
        result = build_transaction_insights(txs, date(2024, 1, 1), date(2024, 4, 1))
        assert result.spending_trend == "stable"

    def test_multi_month_decreasing(self) -> None:
        txs = [
            _make_tx(-30000, date(2024, 1, 15)),
            _make_tx(-20000, date(2024, 2, 15)),
            _make_tx(-10000, date(2024, 3, 15)),
        ]
        result = build_transaction_insights(txs, date(2024, 1, 1), date(2024, 4, 1))
        assert result.spending_trend == "decreasing"

    def test_top_n_truncation(self) -> None:
        # 10 distinct payees with decreasing absolute amounts.
        txs = []
        for i in range(10):
            txs.append(
                _make_tx(
                    -1000 * (i + 1),
                    date(2024, 2, 1 + i),
                    payee_id=f"00000000-0000-0000-0000-{i:012d}",
                    payee_name=f"P{i}",
                    category_id=f"11111111-1111-1111-1111-{i:012d}",
                    category_name=f"C{i}",
                )
            )
        result = build_transaction_insights(txs, date(2024, 1, 1), date(2024, 4, 1))
        assert len(result.top_payees) == 5
        assert len(result.top_categories) == 5
        # Top payee is the largest absolute amount (P9 = -$10.00)
        assert result.top_payees[0].payee_name == "P9"
        # Sorted by absolute milliunits descending
        abs_totals = [abs(p.total_milliunits) for p in result.top_payees]
        assert abs_totals == sorted(abs_totals, reverse=True)

    def test_unassigned_payee(self) -> None:
        tx = _make_tx(
            -50000,
            date(2024, 1, 15),
            payee_id=None,
            payee_name=None,
        )
        result = build_transaction_insights([tx], date(2024, 1, 1), date(2024, 4, 1))
        assert len(result.top_payees) == 1
        assert result.top_payees[0].payee_name == "Unassigned"
        assert result.top_payees[0].payee_id is None

    def test_uncategorized(self) -> None:
        tx = _make_tx(
            -50000,
            date(2024, 1, 15),
            category_id=None,
            category_name=None,
        )
        result = build_transaction_insights([tx], date(2024, 1, 1), date(2024, 4, 1))
        assert len(result.top_categories) == 1
        assert result.top_categories[0].category_name == "Uncategorized"
        assert result.top_categories[0].category_id is None

    def test_cleared_breakdown(self) -> None:
        txs = [
            _make_tx(-1000, date(2024, 1, 1), cleared="cleared"),
            _make_tx(-1000, date(2024, 1, 2), cleared="uncleared"),
            _make_tx(-1000, date(2024, 1, 3), cleared="reconciled"),
        ]
        result = build_transaction_insights(txs, date(2024, 1, 1), date(2024, 4, 1))
        assert result.by_cleared_status.cleared == 1
        assert result.by_cleared_status.uncleared == 1
        assert result.by_cleared_status.reconciled == 1

    def test_inflow_and_outflow(self) -> None:
        txs = [
            _make_tx(-50000, date(2024, 1, 5)),  # outflow
            _make_tx(200000, date(2024, 1, 6)),  # inflow
        ]
        result = build_transaction_insights(txs, date(2024, 1, 1), date(2024, 4, 1))
        assert result.transaction_count == 2
        assert result.total_inflow_formatted == "$200.00"
        assert result.total_outflow_formatted == "-$50.00"
        assert result.net_formatted == "$150.00"

    def test_zero_fill_for_empty_months(self) -> None:
        # Only January has transactions; Feb / Mar are zero-filled.
        tx = _make_tx(-10000, date(2024, 1, 15))
        result = build_transaction_insights([tx], date(2024, 1, 1), date(2024, 4, 1))
        assert len(result.monthly_buckets) == 3
        assert result.monthly_buckets[0].transaction_count == 1
        assert result.monthly_buckets[1].transaction_count == 0
        assert result.monthly_buckets[2].transaction_count == 0
        assert result.monthly_buckets[1].outflow_formatted == "$0.00"

    def test_buckets_sum_to_window_total(self) -> None:
        txs = [
            _make_tx(-5000, date(2024, 1, 1)),
            _make_tx(-10000, date(2024, 2, 1)),
            _make_tx(-15000, date(2024, 3, 1)),
        ]
        result = build_transaction_insights(txs, date(2024, 1, 1), date(2024, 4, 1))
        # transaction_count consistency
        assert (
            sum(b.transaction_count for b in result.monthly_buckets)
            == result.transaction_count
        )

    def test_inverted_period_returns_error(self) -> None:
        result = build_transaction_insights([], date(2024, 4, 1), date(2024, 1, 1))
        assert result.error is not None
        assert "period_end" in result.error
        assert result.transaction_count == 0


class TestPublicSchemaSurface:
    def test_models_are_exported(self) -> None:
        # The package-level public API exposes every required symbol.
        from ynab_http_mcp.schemas import (  # noqa: F401
            ClearedBreakdown,
            MonthlyTransactionBucket,
            PayeeAggregate,
            CategoryAggregate,
            TransactionInsightsResponse,
        )

    def test_from_transactions_classmethod(self) -> None:
        # The spec describes a `from_transactions` classmethod; verify the
        # function-level builder produces a model with the same shape.
        result = TransactionInsightsResponse.from_transactions(
            [], date(2024, 1, 1), date(2024, 4, 1)
        )
        assert result.transaction_count == 0
        assert len(result.monthly_buckets) == 3


# ---------------------------------------------------------------------------
# Lean / Full shape — verify the milliunit twin is dropped from the Lean
# layer and lives only in the Full layer's ``full_details`` dict.
# ---------------------------------------------------------------------------


class TestLeanFullShape:
    def test_lean_transaction_has_no_milli_amount(self) -> None:
        from ynab_http_mcp.schemas.transactions import MCPTransaction

        # Lean: integer milliunit ``amount`` is dropped; the formatted
        # ``amount`` string is the only currency field.
        assert "milli_amount" not in MCPTransaction.model_fields
        assert "amount" in MCPTransaction.model_fields

    def test_lean_subtransaction_has_no_milli_amount(self) -> None:
        from ynab_http_mcp.schemas.transactions import MCPTransaction

        assert "milli_amount" not in MCPTransaction.MCPSubTransaction.model_fields
        assert "amount" in MCPTransaction.MCPSubTransaction.model_fields

    def test_transaction_full_details_contains_integer_amount(self) -> None:
        from uuid import UUID as _UUID
        from ynab_http_mcp.schemas.transactions import MCPTransactionFull

        # The Full layer exposes the cleaned raw ``ynab.TransactionDetail``
        # including the integer ``amount`` (milliunits).
        full_dump = MCPTransactionFull(
            id=_UUID("00000000-0000-0000-0000-000000000001"),
            date=date(2024, 1, 15),
            amount="-$45.00",
            memo=None,
            cleared="cleared",
            approved=True,
            account_id=_UUID("00000000-0000-0000-0000-000000000002"),
            account_name="Checking",
            payee_id=None,
            payee_name=None,
            category_id=None,
            category_name=None,
            transfer_account_id=None,
            transfer_transaction_id=None,
            import_payee_name_original=None,
            flag_color=None,
            debt_transaction_type=None,
            subtransactions=[],
            full_details={"amount": -45000, "id": "abc"},
        ).model_dump()
        assert full_dump["amount"] == "-$45.00"
        assert full_dump["full_details"]["amount"] == -45000

    def test_transaction_full_inherits_lean_fields(self) -> None:
        from ynab_http_mcp.schemas.transactions import (
            MCPTransaction,
            MCPTransactionFull,
        )

        # The *Full model adds exactly one new field on top of its lean parent.
        full_fields = set(MCPTransactionFull.model_fields.keys())
        lean_fields = set(MCPTransaction.model_fields.keys())
        assert full_fields - lean_fields == {"full_details"}

    def test_lean_resource_never_embeds_full_details(self) -> None:
        # The Lean layer does not include ``full_details`` on the read model.
        from ynab_http_mcp.schemas.transactions import (
            MCPTransaction,
            MCPTransactions,
        )
        from ynab_http_mcp.schemas.accounts import MCPAccount, MCPAccounts
        from ynab_http_mcp.schemas.categories import MCPCategory, MCPCategories
        from ynab_http_mcp.schemas.payees import (
            CleanPayee,
            PayeesResponse,
        )
        from ynab_http_mcp.schemas.planning import MonthCategory, PlanMonth

        for model in (
            MCPTransaction,
            MCPTransactions,
            MCPAccount,
            MCPAccounts,
            MCPCategory,
            MCPCategories,
            CleanPayee,
            PayeesResponse,
            MonthCategory,
            PlanMonth,
        ):
            assert "full_details" not in model.model_fields, (
                f"{model.__name__} is a lean model and must not carry full_details"
            )
