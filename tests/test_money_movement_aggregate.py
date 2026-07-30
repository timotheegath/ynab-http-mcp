"""
Unit tests for the money movement aggregate computation.

Covers the empty window, single month, multi-month, top-N truncation,
TBA vs other-category split, recurring-pair detection, proactive_pct
computation, _classify_planning_health rules, and the error path on an
inverted window.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import List, Optional
from uuid import uuid4

import ynab

from ynab_http_mcp.schemas.money_movement_aggregate import (
    _classify_planning_health,
    build_money_movement_insights,
)


def _make_movement(
    amount: int,
    month: date,
    *,
    from_category_id: Optional[str] = None,
    to_category_id: Optional[str] = None,
    moved_at: Optional[datetime] = None,
) -> ynab.MoneyMovement:
    """Build a single ``ynab.MoneyMovement`` for testing."""
    if moved_at is None:
        moved_at = datetime(month.year, month.month, 15)
    abs_amount = abs(amount)
    whole = abs_amount // 1000
    cents = abs_amount % 1000
    amount_formatted = (
        f"-${whole}.{cents:02d}" if amount < 0 else f"${whole}.{cents:02d}"
    )
    payload = {
        "id": uuid4(),
        "month": month,
        "moved_at": moved_at,
        "from_category_id": (
            from_category_id if from_category_id is not None else None
        ),
        "to_category_id": to_category_id if to_category_id is not None else uuid4(),
        "amount": amount,
        "amount_formatted": amount_formatted,
    }
    return ynab.MoneyMovement.model_validate(payload)


def _identity_lookup(cat_id: Optional[str]) -> str:
    """Test category-name lookup. ``None`` → ``Ready to Assign``,
    everything else → ``"Cat-" + first 8 hex chars``. Unresolved ids
    are not expected here, so we fall back to ``"Unknown"``."""
    if cat_id is None:
        return "Ready to Assign"
    return f"Cat-{cat_id[:8]}"


# ---------------------------------------------------------------------------
# planning_health classification
# ---------------------------------------------------------------------------


class TestClassifyPlanningHealth:
    def test_zero_count_is_excellent(self) -> None:
        assert _classify_planning_health(0, 0.0, 0) == "excellent"

    def test_low_tba_ratio_is_reactive(self) -> None:
        assert _classify_planning_health(10, 0.30, 0) == "reactive"

    def test_many_recurring_pairs_is_reactive(self) -> None:
        # Even with high TBA ratio, 3+ recurring pairs pushes reactive.
        assert _classify_planning_health(10, 0.95, 3) == "reactive"

    def test_high_tba_no_pairs_is_healthy(self) -> None:
        assert _classify_planning_health(10, 0.90, 0) == "healthy"

    def test_mid_tba_ratio_is_mixed(self) -> None:
        assert _classify_planning_health(10, 0.65, 0) == "mixed"

    def test_one_recurring_pair_is_mixed(self) -> None:
        assert _classify_planning_health(10, 0.95, 1) == "mixed"


# ---------------------------------------------------------------------------
# build_money_movement_insights
# ---------------------------------------------------------------------------


class TestBuildInsights:
    def test_empty_window_is_excellent(self) -> None:
        result = build_money_movement_insights(
            [], date(2024, 1, 1), date(2024, 4, 1), _identity_lookup
        )
        assert result.total_movement_count == 0
        assert result.planning_health == "excellent"
        assert result.from_ready_to_assign_count == 0
        assert result.from_other_categories_count == 0
        assert result.top_source_categories == []
        assert result.top_destination_categories == []
        assert result.recurring_pairs == []
        assert result.total_moved_formatted == "$0.00"
        assert result.average_movement_formatted == "$0.00"
        assert result.from_ready_to_assign_total_formatted == "$0.00"
        assert result.from_other_categories_total_formatted == "$0.00"
        assert result.movement_trend == "stable"
        assert result.proactive_pct is None
        assert result.period_start == "2024-01-01"
        assert result.period_end == "2024-04-01"
        # 3 calendar months, zero-filled
        assert len(result.monthly_buckets) == 3
        for b in result.monthly_buckets:
            assert b.movement_count == 0
            assert b.from_tba_count == 0
            assert b.from_other_count == 0
            assert b.from_tba_total_formatted == "$0.00"
            assert b.from_other_total_formatted == "$0.00"
            assert b.average_moved_day_of_month is None
        assert result.error is None

    def test_tba_vs_other_split(self) -> None:
        # 2 TBA movements, 1 other-category movement.
        from_cat = str(uuid4())
        to_cat = str(uuid4())
        m1 = _make_movement(
            -10000,
            date(2024, 1, 5),
            from_category_id=None,
            to_category_id=to_cat,
        )
        m2 = _make_movement(
            -20000,
            date(2024, 1, 6),
            from_category_id=None,
            to_category_id=to_cat,
        )
        m3 = _make_movement(
            -30000,
            date(2024, 1, 7),
            from_category_id=from_cat,
            to_category_id=to_cat,
        )
        result = build_money_movement_insights(
            [m1, m2, m3], date(2024, 1, 1), date(2024, 2, 1), _identity_lookup
        )
        assert result.total_movement_count == 3
        assert result.from_ready_to_assign_count == 2
        assert result.from_other_categories_count == 1
        assert result.from_ready_to_assign_total_formatted == "-$30.00"
        assert result.from_other_categories_total_formatted == "-$30.00"
        assert result.total_moved_formatted == "$60.00"
        assert result.average_movement_formatted == "$20.00"
        # 2/3 TBA-sourced → mixed (0.50 ≤ 0.67 < 0.80)
        assert result.planning_health == "mixed"

    def test_top_n_truncation_donors(self) -> None:
        # 8 distinct source categories with decreasing absolute amounts.
        # TBA is one of them.
        movements: List[ynab.MoneyMovement] = []
        for i in range(7):
            movements.append(
                _make_movement(
                    -1000 * (i + 1),
                    date(2024, 1, 1 + i),
                    from_category_id=str(uuid4()),
                    to_category_id=str(uuid4()),
                )
            )
        # TBA movement at the index to test inclusion of TBA row.
        movements.append(
            _make_movement(
                -5000,
                date(2024, 1, 10),
                from_category_id=None,
                to_category_id=str(uuid4()),
            )
        )
        result = build_money_movement_insights(
            movements, date(2024, 1, 1), date(2024, 2, 1), _identity_lookup
        )
        assert len(result.top_source_categories) == 5
        # Sorted by abs(total_milliunits) descending.
        abs_totals = [abs(s.total_milliunits) for s in result.top_source_categories]
        assert abs_totals == sorted(abs_totals, reverse=True)
        # TBA aggregate is one of the entries (TBA has 5000 absolute).
        tba_rows = [s for s in result.top_source_categories if s.category_id is None]
        assert len(tba_rows) == 1
        assert tba_rows[0].category_name == "Ready to Assign"

    def test_top_n_truncation_recipients(self) -> None:
        # 12 distinct destination categories with decreasing absolute amounts.
        movements: List[ynab.MoneyMovement] = []
        for i in range(12):
            movements.append(
                _make_movement(
                    -1000 * (i + 1),
                    date(2024, 1, 1 + i),
                    from_category_id=str(uuid4()),
                    to_category_id=str(uuid4()),
                )
            )
        result = build_money_movement_insights(
            movements, date(2024, 1, 1), date(2024, 2, 1), _identity_lookup
        )
        assert len(result.top_destination_categories) == 5
        abs_totals = [
            abs(d.total_milliunits) for d in result.top_destination_categories
        ]
        assert abs_totals == sorted(abs_totals, reverse=True)

    def test_recurring_pairs(self) -> None:
        # Same (from, to) pair appears 3 times in the window.
        from_cat = str(uuid4())
        to_cat = str(uuid4())
        # A second one-off pair to ensure it's filtered out.
        from_cat2 = str(uuid4())
        to_cat2 = str(uuid4())
        movements = [
            _make_movement(
                -5000,
                date(2024, 1, 5),
                from_category_id=from_cat,
                to_category_id=to_cat,
            ),
            _make_movement(
                -7000,
                date(2024, 1, 15),
                from_category_id=from_cat,
                to_category_id=to_cat,
            ),
            _make_movement(
                -3000,
                date(2024, 1, 20),
                from_category_id=from_cat,
                to_category_id=to_cat,
            ),
            # One-off pair — must NOT appear in recurring_pairs.
            _make_movement(
                -1000,
                date(2024, 1, 25),
                from_category_id=from_cat2,
                to_category_id=to_cat2,
            ),
        ]
        result = build_money_movement_insights(
            movements, date(2024, 1, 1), date(2024, 2, 1), _identity_lookup
        )
        assert len(result.recurring_pairs) == 1
        pair = result.recurring_pairs[0]
        assert pair.from_category_id == from_cat
        assert pair.to_category_id == to_cat
        assert pair.movement_count == 3
        assert pair.total_formatted == "-$15.00"

    def test_proactive_pct(self) -> None:
        # 4 movements: 2 on day 5 (proactive), 1 on day 15, 1 on day 25.
        to_cat = str(uuid4())
        movements = [
            _make_movement(
                -1000,
                date(2024, 1, 5),
                from_category_id=str(uuid4()),
                to_category_id=to_cat,
                moved_at=datetime(2024, 1, 5, 0, 0),
            ),
            _make_movement(
                -1000,
                date(2024, 1, 7),
                from_category_id=None,
                to_category_id=to_cat,
                moved_at=datetime(2024, 1, 7, 0, 0),
            ),
            _make_movement(
                -1000,
                date(2024, 1, 15),
                from_category_id=str(uuid4()),
                to_category_id=to_cat,
                moved_at=datetime(2024, 1, 15, 0, 0),
            ),
            _make_movement(
                -1000,
                date(2024, 1, 25),
                from_category_id=str(uuid4()),
                to_category_id=to_cat,
                moved_at=datetime(2024, 1, 25, 0, 0),
            ),
        ]
        result = build_money_movement_insights(
            movements, date(2024, 1, 1), date(2024, 2, 1), _identity_lookup
        )
        assert result.proactive_pct == 0.5

    def test_inverted_period_returns_error(self) -> None:
        result = build_money_movement_insights(
            [], date(2024, 4, 1), date(2024, 1, 1), _identity_lookup
        )
        assert result.error is not None
        assert "period_end" in result.error
        assert result.total_movement_count == 0
        assert result.planning_health == "excellent"

    def test_zero_movement_planning_health(self) -> None:
        # Explicit positive assertion for the spec scenario.
        result = build_money_movement_insights(
            [], date(2024, 1, 1), date(2024, 2, 1), _identity_lookup
        )
        assert result.planning_health == "excellent"
        assert result.proactive_pct is None
        assert result.recurring_pairs == []
        assert result.top_source_categories == []
        assert result.top_destination_categories == []

    def test_reactive_planning_health_low_tba(self) -> None:
        # 1 TBA + 4 other-category → tba_ratio = 0.20 → reactive.
        movements: List[ynab.MoneyMovement] = []
        for i in range(4):
            movements.append(
                _make_movement(
                    -1000,
                    date(2024, 1, 1 + i),
                    from_category_id=str(uuid4()),
                    to_category_id=str(uuid4()),
                )
            )
        movements.append(
            _make_movement(
                -1000,
                date(2024, 1, 5),
                from_category_id=None,
                to_category_id=str(uuid4()),
            )
        )
        result = build_money_movement_insights(
            movements, date(2024, 1, 1), date(2024, 2, 1), _identity_lookup
        )
        assert result.planning_health == "reactive"

    def test_healthy_planning_health_high_tba(self) -> None:
        # 5 TBA, 0 other → tba_ratio = 1.0 → healthy.
        movements: List[ynab.MoneyMovement] = []
        for i in range(5):
            movements.append(
                _make_movement(
                    -1000,
                    date(2024, 1, 1 + i),
                    from_category_id=None,
                    to_category_id=str(uuid4()),
                )
            )
        result = build_money_movement_insights(
            movements, date(2024, 1, 1), date(2024, 2, 1), _identity_lookup
        )
        assert result.planning_health == "healthy"

    def test_multi_month_trend_increasing(self) -> None:
        # Total moved grows month over month.
        movements = [
            _make_movement(
                -10000,
                date(2024, 1, 5),
                from_category_id=None,
                to_category_id=str(uuid4()),
            ),
            _make_movement(
                -20000,
                date(2024, 2, 5),
                from_category_id=None,
                to_category_id=str(uuid4()),
            ),
            _make_movement(
                -30000,
                date(2024, 3, 5),
                from_category_id=None,
                to_category_id=str(uuid4()),
            ),
        ]
        result = build_money_movement_insights(
            movements, date(2024, 1, 1), date(2024, 4, 1), _identity_lookup
        )
        assert result.movement_trend == "increasing"
        # monthly totals are abs amounts: 10, 20, 30
        assert result.monthly_buckets[0].movement_count == 1
        assert result.monthly_buckets[1].movement_count == 1
        assert result.monthly_buckets[2].movement_count == 1

    def test_multi_month_trend_decreasing(self) -> None:
        movements = [
            _make_movement(
                -30000,
                date(2024, 1, 5),
                from_category_id=None,
                to_category_id=str(uuid4()),
            ),
            _make_movement(
                -20000,
                date(2024, 2, 5),
                from_category_id=None,
                to_category_id=str(uuid4()),
            ),
            _make_movement(
                -10000,
                date(2024, 3, 5),
                from_category_id=None,
                to_category_id=str(uuid4()),
            ),
        ]
        result = build_money_movement_insights(
            movements, date(2024, 1, 1), date(2024, 4, 1), _identity_lookup
        )
        assert result.movement_trend == "decreasing"

    def test_multi_month_trend_stable(self) -> None:
        movements = [
            _make_movement(
                -20000,
                date(2024, 1, 5),
                from_category_id=None,
                to_category_id=str(uuid4()),
            ),
            _make_movement(
                -20000,
                date(2024, 2, 5),
                from_category_id=None,
                to_category_id=str(uuid4()),
            ),
            _make_movement(
                -20000,
                date(2024, 3, 5),
                from_category_id=None,
                to_category_id=str(uuid4()),
            ),
        ]
        result = build_money_movement_insights(
            movements, date(2024, 1, 1), date(2024, 4, 1), _identity_lookup
        )
        assert result.movement_trend == "stable"

    def test_zero_fill_for_empty_months(self) -> None:
        # Only January has movements; Feb / Mar are zero-filled.
        movement = _make_movement(
            -10000,
            date(2024, 1, 15),
            from_category_id=None,
            to_category_id=str(uuid4()),
        )
        result = build_money_movement_insights(
            [movement], date(2024, 1, 1), date(2024, 4, 1), _identity_lookup
        )
        assert len(result.monthly_buckets) == 3
        assert result.monthly_buckets[0].movement_count == 1
        assert result.monthly_buckets[1].movement_count == 0
        assert result.monthly_buckets[2].movement_count == 0
        assert result.monthly_buckets[1].from_tba_total_formatted == "$0.00"
        assert result.monthly_buckets[1].average_moved_day_of_month is None

    def test_unknown_category_lookup_falls_back(self) -> None:
        # Lookup that returns "Unknown" for any non-TBA id.
        def lookup(cid: Optional[str]) -> str:
            if cid is None:
                return "Ready to Assign"
            return "Unknown"

        result = build_money_movement_insights(
            [
                _make_movement(
                    -1000,
                    date(2024, 1, 5),
                    from_category_id=str(uuid4()),
                    to_category_id=str(uuid4()),
                )
            ],
            date(2024, 1, 1),
            date(2024, 2, 1),
            lookup,
        )
        assert result.top_source_categories[0].category_name == "Unknown"
        assert result.top_destination_categories[0].category_name == "Unknown"

    def test_average_movement_day_of_month(self) -> None:
        to_cat = str(uuid4())
        movements = [
            _make_movement(
                -1000,
                date(2024, 1, 3),
                from_category_id=None,
                to_category_id=to_cat,
                moved_at=datetime(2024, 1, 3, 0, 0),
            ),
            _make_movement(
                -1000,
                date(2024, 1, 17),
                from_category_id=None,
                to_category_id=to_cat,
                moved_at=datetime(2024, 1, 17, 0, 0),
            ),
        ]
        result = build_money_movement_insights(
            movements, date(2024, 1, 1), date(2024, 2, 1), _identity_lookup
        )
        assert result.monthly_buckets[0].average_moved_day_of_month == 10.0


# ---------------------------------------------------------------------------
# Public schema surface
# ---------------------------------------------------------------------------


class TestPublicSchemaSurface:
    def test_models_are_exported(self) -> None:
        from ynab_http_mcp.schemas import (  # noqa: F401
            MonthlyMoneyMovementBucket,
            SourceCategoryAggregate,
            DestinationCategoryAggregate,
            RecurringMovementPair,
            MoneyMovementInsightsResponse,
        )

    def test_response_serialization_omits_none(self) -> None:
        # Build a zero-window response and confirm the JSON drops
        # ``error`` (None) but keeps the rest of the shape.
        result = build_money_movement_insights(
            [], date(2024, 1, 1), date(2024, 2, 1), _identity_lookup
        )
        # error is None on a clean run → must be omitted from the JSON.
        result.error = None
        rendered = result.model_dump_json(exclude_none=True)
        assert '"error"' not in rendered
        # Required fields remain present.
        assert '"period_start"' in rendered
        assert '"monthly_buckets"' in rendered
