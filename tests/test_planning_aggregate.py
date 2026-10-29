"""
Unit tests for the planning insights aggregate.

Covers the response model serialization (1.1), window resolution and the
month fan-out including forward months and the horizon flag (1.2), the
per-category series / goal promotion / goal monthly rate / derived
arithmetic (1.3), zeroed error responses (1.4), and the in-process TTL
cache deduping repeated reads (2.2).
"""

from __future__ import annotations

import asyncio
import json
from datetime import date, datetime
from types import SimpleNamespace
from typing import Any, Dict, List, Optional
from uuid import UUID

import pytest
import ynab
from fastmcp import FastMCP
from fastmcp.client import Client

from ynab_http_mcp.schemas.planning_aggregate import (
    build_planning_insights_from_months,
    default_window_months,
    discover_forward_months,
    months_inclusive,
    parse_month_bound,
    resolve_month_window,
    zero_response,
)
from ynab_http_mcp.ynab_service import YnabService, PlanMonthNotFoundError
from ynab_http_mcp.tools.planning_insights import (
    _cache_clear,
    _cache_set,
    _TTL_SECONDS,
    build_planning_insights,
    register,
)

CAT_UUID = UUID("00000000-0000-0000-0000-000000000001")
GRP_UUID = UUID("11111111-1111-1111-1111-111111111111")


# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------


def _make_category(
    *,
    cid: UUID = CAT_UUID,
    name: str = "Groceries",
    hidden: bool = False,
    deleted: bool = False,
    budgeted: int = 0,
    activity: int = 0,
    balance: int = 0,
    budgeted_formatted: Optional[str] = None,
    activity_formatted: Optional[str] = None,
    balance_formatted: Optional[str] = None,
    goal_type: Optional[str] = None,
    goal_target: Optional[int] = None,
    goal_target_formatted: Optional[str] = None,
    goal_target_date: Optional[date] = None,
    goal_cadence: Optional[int] = None,
    goal_cadence_frequency: Optional[int] = None,
    goal_under_funded: Optional[int] = None,
    goal_under_funded_formatted: Optional[str] = None,
    goal_overall_left: Optional[int] = None,
    goal_overall_left_formatted: Optional[str] = None,
    goal_months_to_budget: Optional[int] = None,
    goal_percentage_complete: Optional[int] = None,
    goal_snoozed_at: Optional[datetime] = None,
) -> ynab.Category:
    return ynab.Category(
        id=cid,
        category_group_id=GRP_UUID,
        name=name,
        hidden=hidden,
        internal=False,
        deleted=deleted,
        budgeted=budgeted,
        activity=activity,
        balance=balance,
        budgeted_formatted=budgeted_formatted,
        activity_formatted=activity_formatted,
        balance_formatted=balance_formatted,
        goal_type=goal_type,
        goal_target=goal_target,
        goal_target_formatted=goal_target_formatted,
        goal_target_date=goal_target_date,
        goal_cadence=goal_cadence,
        goal_cadence_frequency=goal_cadence_frequency,
        goal_under_funded=goal_under_funded,
        goal_under_funded_formatted=goal_under_funded_formatted,
        goal_overall_left=goal_overall_left,
        goal_overall_left_formatted=goal_overall_left_formatted,
        goal_months_to_budget=goal_months_to_budget,
        goal_percentage_complete=goal_percentage_complete,
        goal_snoozed_at=goal_snoozed_at,
    )


def _make_month_detail(
    month: date,
    categories: List[ynab.Category],
    to_be_budgeted: int = 0,
    to_be_budgeted_formatted: Optional[str] = None,
) -> ynab.MonthDetail:
    return ynab.MonthDetail(
        month=month,
        income=0,
        budgeted=0,
        activity=0,
        to_be_budgeted=to_be_budgeted,
        age_of_money=None,
        deleted=False,
        categories=categories,
        to_be_budgeted_formatted=to_be_budgeted_formatted,
    )


class MockYnabService(YnabService):
    """Subclassed ``YnabService`` that skips the network constructor and serves
    canned month data for the fan-out and error/cache tests.

    ``refuse`` months raise ``PlanMonthNotFoundError`` — YNAB has no plan
    for them yet. ``fail`` months raise a generic error — an upstream
    failure that must not be mistaken for a missing plan.
    """

    def __init__(
        self,
        summaries: Optional[List[Any]] = None,
        months: Optional[Dict[str, ynab.MonthDetail]] = None,
        refuse: Optional[set] = None,
        fail: Optional[set] = None,
    ) -> None:
        self._summaries = summaries or []
        self._months = months or {}
        self._refuse = refuse or set()
        self._fail = fail or set()
        self.get_plan_month_calls: List[str] = []

    def get_all_plan_months(self) -> Any:
        return SimpleNamespace(data=SimpleNamespace(months=self._summaries))

    def get_plan_month(self, month_str: str) -> Any:  # type: ignore[override]
        self.get_plan_month_calls.append(month_str)
        if month_str in self._fail:
            raise RuntimeError("YNAB upstream failure")
        if month_str in self._refuse:
            raise PlanMonthNotFoundError(month_str)
        return SimpleNamespace(data=SimpleNamespace(month=self._months[month_str]))


def _summary(month: date) -> Any:
    return SimpleNamespace(month=month, deleted=False)


def _all_keys(obj: Any) -> set:
    keys = set()
    if isinstance(obj, dict):
        for key, value in obj.items():
            keys.add(key)
            keys.update(_all_keys(value))
    elif isinstance(obj, list):
        for item in obj:
            keys.update(_all_keys(item))
    return keys


# ---------------------------------------------------------------------------
# 1.1 Response model serialization
# ---------------------------------------------------------------------------


class TestModelSerialization:
    def _build(self) -> Any:
        cat = _make_category(
            budgeted=100000,
            activity=-30000,
            balance=70000,
            budgeted_formatted="$100.00",
            activity_formatted="-$30.00",
            balance_formatted="$70.00",
            goal_type="TBD",
            goal_target=500000,
            goal_target_formatted="$500.00",
            goal_target_date=date(2026, 12, 1),
            goal_overall_left=2250000,
            goal_overall_left_formatted="$2,250.00",
            goal_months_to_budget=3,
            goal_percentage_complete=40,
        )
        return build_planning_insights_from_months(
            [
                _make_month_detail(date(2026, 1, 1), [cat], 100000, "$100.00"),
                _make_month_detail(date(2026, 2, 1), [cat], 100000, "$100.00"),
                _make_month_detail(date(2026, 3, 1), [cat], 100000, "$100.00"),
            ]
        )

    def test_milliunit_and_formatted_twins(self) -> None:
        result = self._build()
        dumped = json.loads(result.model_dump_json(exclude_none=True))
        entry = dumped["categories"][0]["months"][0]
        assert entry["budgeted"] == 100000
        assert entry["budgeted_formatted"] == "$100.00"
        assert entry["activity"] == -30000
        assert entry["activity_formatted"] == "-$30.00"
        assert entry["balance"] == 70000
        assert entry["balance_formatted"] == "$70.00"

    def test_goal_monthly_rate_serialized(self) -> None:
        result = self._build()
        goal = result.categories[0].goal
        assert goal is not None
        assert goal.goal_monthly_rate == 2250000 // 3  # 750000

    def test_goal_block_omitted_when_no_goal(self) -> None:
        cat = _make_category(budgeted=0, balance=0)
        result = build_planning_insights_from_months(
            [_make_month_detail(date(2026, 1, 1), [cat])]
        )
        dumped = result.model_dump_json(exclude_none=True)
        assert '"goal"' not in dumped

    def test_exclude_none_omits_absent_goal_fields(self) -> None:
        cat = _make_category(
            budgeted=0,
            balance=0,
            goal_type="TB",
            goal_target=100000,
            goal_target_formatted="$100.00",
        )
        result = build_planning_insights_from_months(
            [_make_month_detail(date(2026, 1, 1), [cat])]
        )
        dumped = json.loads(result.model_dump_json(exclude_none=True))
        goal = dumped["categories"][0]["goal"]
        assert goal["goal_type"] == "TB"
        # TB has no target date nor cadence → those keys are absent
        assert "goal_target_date" not in goal
        assert "goal_cadence" not in goal
        assert "goal_monthly_rate" not in goal

    def test_no_income_or_expected_balance_field_anywhere(self) -> None:
        result = self._build()
        rendered = result.model_dump_json(exclude_none=True)
        assert '"income"' not in rendered
        keys = _all_keys(json.loads(rendered))
        assert "income" not in keys
        assert not any("balance" in k and "expect" in k for k in keys)
        assert not any("expected" in k for k in keys)

    def test_error_none_omitted_on_clean_run(self) -> None:
        result = self._build()
        rendered = result.model_dump_json(exclude_none=True)
        assert '"error"' not in rendered


# ---------------------------------------------------------------------------
# 1.2 Window resolution and fan-out
# ---------------------------------------------------------------------------


class TestWindowResolution:
    def test_default_window_is_last_three_months(self) -> None:
        since, until = default_window_months(date(2026, 2, 15))
        assert since == date(2025, 12, 1)
        assert until == date(2026, 2, 1)

    def test_default_window_crosses_year_boundary(self) -> None:
        since, until = default_window_months(date(2026, 1, 10))
        assert since == date(2025, 11, 1)
        assert until == date(2026, 1, 1)

    def test_parse_month_bound_floors_day(self) -> None:
        assert parse_month_bound("2026-01-15") == date(2026, 1, 1)
        assert parse_month_bound("2026-01") == date(2026, 1, 1)

    def test_day_components_ignored_yields_jan_to_mar(self) -> None:
        since, until = resolve_month_window(
            "2026-01-15", "2026-03-21", date(2026, 1, 1)
        )
        assert since == date(2026, 1, 1)
        assert until == date(2026, 3, 1)

    def test_months_inclusive(self) -> None:
        assert months_inclusive(date(2026, 1, 1), date(2026, 3, 1)) == [
            date(2026, 1, 1),
            date(2026, 2, 1),
            date(2026, 3, 1),
        ]

    def test_discover_forward_months(self) -> None:
        summaries = [
            _summary(date(2026, 1, 1)),
            _summary(date(2026, 4, 1)),
            _summary(date(2026, 5, 1)),
            _summary(date(2026, 3, 1)),
        ]
        forward = discover_forward_months(summaries, date(2026, 3, 1))
        assert forward == [date(2026, 4, 1), date(2026, 5, 1)]

    def test_discover_forward_months_skips_deleted(self) -> None:
        summaries = [
            _summary(date(2026, 4, 1)),
            SimpleNamespace(month=date(2026, 5, 1), deleted=True),
        ]
        forward = discover_forward_months(summaries, date(2026, 3, 1))
        assert forward == [date(2026, 4, 1)]

    def test_unparseable_month_raises(self) -> None:
        with pytest.raises(ValueError):
            resolve_month_window("not-a-date", None)


def _fan_out_mock(now: date, summaries, months, refuse=None) -> MockYnabService:
    return MockYnabService(summaries=summaries, months=months, refuse=refuse)


class TestFanOut:
    def test_default_window(self) -> None:
        months = {
            "2025-12": _make_month_detail(date(2025, 12, 1), []),
            "2026-01": _make_month_detail(date(2026, 1, 1), []),
            "2026-02": _make_month_detail(date(2026, 2, 1), []),
        }
        mock = _fan_out_mock(date(2026, 2, 15), [], months)
        build_planning_insights(mock, now=date(2026, 2, 15))
        assert mock.get_plan_month_calls == ["2025-12", "2026-01", "2026-02"]

    def test_day_flooring(self) -> None:
        months = {
            "2026-01": _make_month_detail(date(2026, 1, 1), []),
            "2026-02": _make_month_detail(date(2026, 2, 1), []),
            "2026-03": _make_month_detail(date(2026, 3, 1), []),
        }
        mock = _fan_out_mock(date(2026, 1, 1), [], months)
        build_planning_insights(mock, since_date="2026-01-15", until_date="2026-03-21")
        assert mock.get_plan_month_calls == ["2026-01", "2026-02", "2026-03"]

    def test_user_assigned_ahead_still_in_walk(self) -> None:
        summaries = [_summary(date(2026, 4, 1)), _summary(date(2026, 5, 1))]
        months = {
            "2026-01": _make_month_detail(date(2026, 1, 1), []),
            "2026-02": _make_month_detail(date(2026, 2, 1), []),
            "2026-03": _make_month_detail(date(2026, 3, 1), []),
            "2026-04": _make_month_detail(date(2026, 4, 1), []),
            "2026-05": _make_month_detail(date(2026, 5, 1), []),
        }
        mock = _fan_out_mock(date(2026, 1, 1), summaries, months)
        result = build_planning_insights(
            mock, since_date="2026-01", until_date="2026-03"
        )
        assert mock.get_plan_month_calls == [
            "2026-01",
            "2026-02",
            "2026-03",
            "2026-04",
            "2026-05",
        ]
        assert [m.month for m in result.months] == [
            "2026-01",
            "2026-02",
            "2026-03",
            "2026-04",
            "2026-05",
        ]
        assert result.plan_horizon_reached is False

    def test_no_future_months(self) -> None:
        summaries = [
            _summary(date(2026, 1, 1)),
            _summary(date(2026, 2, 1)),
            _summary(date(2026, 3, 1)),
        ]
        months = {
            "2026-01": _make_month_detail(date(2026, 1, 1), []),
            "2026-02": _make_month_detail(date(2026, 2, 1), []),
            "2026-03": _make_month_detail(date(2026, 3, 1), []),
        }
        mock = _fan_out_mock(date(2026, 1, 1), summaries, months)
        result = build_planning_insights(
            mock, since_date="2026-01", until_date="2026-03"
        )
        assert [m.month for m in result.months] == ["2026-01", "2026-02", "2026-03"]

    def test_horizon_truncation(self) -> None:
        summaries = [
            _summary(date(2026, 4, 1)),
            _summary(date(2026, 5, 1)),
            _summary(date(2026, 6, 1)),
        ]
        months = {
            "2026-01": _make_month_detail(date(2026, 1, 1), []),
            "2026-02": _make_month_detail(date(2026, 2, 1), []),
            "2026-03": _make_month_detail(date(2026, 3, 1), []),
            "2026-04": _make_month_detail(date(2026, 4, 1), []),
        }
        mock = _fan_out_mock(date(2026, 1, 1), summaries, months, refuse={"2026-05"})
        result = build_planning_insights(
            mock, since_date="2026-01", until_date="2026-03"
        )
        assert result.plan_horizon_reached is True
        assert [m.month for m in result.months] == [
            "2026-01",
            "2026-02",
            "2026-03",
            "2026-04",
        ]
        # The refused month was never fetched successfully past the horizon.
        assert mock.get_plan_month_calls[-1] == "2026-05"

    def test_inverted_window_raises(self) -> None:
        mock = _fan_out_mock(date(2026, 1, 1), [], {})
        with pytest.raises(ValueError):
            build_planning_insights(mock, since_date="2026-03", until_date="2026-01")

    def test_missing_plan_month_truncates_and_flags_horizon(self) -> None:
        """A month with no plan yet (404) is not an error — the walk stops
        there and the horizon flag is set."""
        months = {
            "2026-01": _make_month_detail(date(2026, 1, 1), []),
            "2026-02": _make_month_detail(date(2026, 2, 1), []),
        }
        mock = _fan_out_mock(date(2026, 1, 1), [], months, refuse={"2026-03"})
        result = build_planning_insights(
            mock, since_date="2026-01", until_date="2026-03"
        )
        assert result.plan_horizon_reached is True
        assert [m.month for m in result.months] == ["2026-01", "2026-02"]
        assert result.error is None

    def test_missing_plan_month_on_window_does_not_raise(self) -> None:
        """The same 404 inside the requested window truncates the walk
        instead of surfacing an upstream failure."""
        months = {"2026-01": _make_month_detail(date(2026, 1, 1), [])}
        mock = _fan_out_mock(date(2026, 1, 1), [], months, refuse={"2026-02"})
        result = build_planning_insights(
            mock, since_date="2026-01", until_date="2026-02"
        )
        assert result.plan_horizon_reached is True
        assert [m.month for m in result.months] == ["2026-01"]
        assert result.error is None

    def test_missing_plan_month_on_forward_month_stops_walk(self) -> None:
        """A 404 on a forward month stops the walk before later months."""
        summaries = [_summary(date(2026, 4, 1)), _summary(date(2026, 5, 1))]
        months = {
            "2026-01": _make_month_detail(date(2026, 1, 1), []),
            "2026-02": _make_month_detail(date(2026, 2, 1), []),
            "2026-03": _make_month_detail(date(2026, 3, 1), []),
        }
        mock = _fan_out_mock(date(2026, 1, 1), summaries, months, refuse={"2026-04"})
        result = build_planning_insights(
            mock, since_date="2026-01", until_date="2026-03"
        )
        assert result.plan_horizon_reached is True
        assert [m.month for m in result.months] == [
            "2026-01",
            "2026-02",
            "2026-03",
        ]
        # The walk stopped at the refused month; later ones were not fetched.
        assert mock.get_plan_month_calls[-1] == "2026-04"

    def test_generic_failure_on_window_month_still_raises(self) -> None:
        """A non-404 failure inside the window is a real upstream failure
        and must not be swallowed as a missing plan."""
        months = {"2026-01": _make_month_detail(date(2026, 1, 1), [])}
        mock = MockYnabService(
            summaries=[],
            months=months,
            fail={"2026-02"},
        )
        with pytest.raises(RuntimeError):
            build_planning_insights(mock, since_date="2026-01", until_date="2026-02")

    def test_window_month_count_tracks_fetched_months(self) -> None:
        """When the walk truncates, only the months actually fetched count
        as window months for the derived statistics."""
        months = {
            "2026-01": _make_month_detail(date(2026, 1, 1), []),
            "2026-02": _make_month_detail(date(2026, 2, 1), []),
        }
        mock = _fan_out_mock(date(2026, 1, 1), [], months, refuse={"2026-03"})
        result = build_planning_insights(
            mock, since_date="2026-01", until_date="2026-03"
        )
        assert len(result.months) == 2
        assert result.plan_horizon_reached is True


# ---------------------------------------------------------------------------
# 1.3 Per-category series, goal promotion, rate, derived stats
# ---------------------------------------------------------------------------


class TestPerCategorySeries:
    def test_series_completeness_three_months(self) -> None:
        cat = _make_category(budgeted=1000, activity=-500, balance=500)
        result = build_planning_insights_from_months(
            [
                _make_month_detail(date(2026, 1, 1), [cat]),
                _make_month_detail(date(2026, 2, 1), [cat]),
                _make_month_detail(date(2026, 3, 1), [cat]),
            ]
        )
        assert len(result.categories) == 1
        assert len(result.categories[0].months) == 3

    def test_deleted_categories_excluded(self) -> None:
        active = _make_category(cid=CAT_UUID, name="Active")
        gone = _make_category(
            cid=UUID("22222222-2222-2222-2222-222222222222"), name="Gone", deleted=True
        )
        result = build_planning_insights_from_months(
            [_make_month_detail(date(2026, 1, 1), [active, gone])]
        )
        assert [c.category_name for c in result.categories] == ["Active"]

    def test_hidden_category_flagged(self) -> None:
        hidden = _make_category(name="Hidden", hidden=True)
        result = build_planning_insights_from_months(
            [_make_month_detail(date(2026, 1, 1), [hidden])]
        )
        assert result.categories[0].hidden is True

    def test_goal_promotion_includes_integers_and_prose(self) -> None:
        cat = _make_category(
            budgeted=0,
            balance=0,
            goal_type="TBD",
            goal_target=500000,
            goal_target_formatted="$500.00",
            goal_target_date=date(2026, 12, 1),
            goal_under_funded=10000,
            goal_under_funded_formatted="$10.00",
            goal_overall_left=2250000,
            goal_overall_left_formatted="$2,250.00",
            goal_months_to_budget=3,
            goal_percentage_complete=40,
        )
        result = build_planning_insights_from_months(
            [_make_month_detail(date(2026, 1, 1), [cat])]
        )
        goal = result.categories[0].goal
        assert goal is not None
        assert goal.goal_type == "TBD"
        assert goal.goal_target == 500000
        assert goal.goal_target_date == "2026-12-01"
        assert goal.under_funded == 10000
        assert goal.overall_left == 2250000
        assert goal.months_to_budget == 3
        assert goal.goal_summary is not None
        assert goal.goal_status is not None


class TestGoalMonthlyRate:
    def test_tbd_division(self) -> None:
        cat = _make_category(
            budgeted=0,
            balance=0,
            goal_type="TBD",
            goal_overall_left=2250000,
            goal_months_to_budget=3,
        )
        result = build_planning_insights_from_months(
            [_make_month_detail(date(2026, 1, 1), [cat])]
        )
        goal = result.categories[0].goal
        assert goal is not None
        assert goal.goal_monthly_rate == 750000

    def test_mf_monthly_frequency(self) -> None:
        cat = _make_category(
            budgeted=0,
            balance=0,
            goal_type="MF",
            goal_target=100000,
            goal_cadence=1,
            goal_cadence_frequency=2,
        )
        result = build_planning_insights_from_months(
            [_make_month_detail(date(2026, 1, 1), [cat])]
        )
        goal = result.categories[0].goal
        assert goal is not None
        assert goal.goal_monthly_rate == 50000

    def test_mf_weekly_normalization(self) -> None:
        cat = _make_category(
            budgeted=0,
            balance=0,
            goal_type="MF",
            goal_target=100000,
            goal_cadence=2,
            goal_cadence_frequency=1,
        )
        result = build_planning_insights_from_months(
            [_make_month_detail(date(2026, 1, 1), [cat])]
        )
        goal = result.categories[0].goal
        assert goal is not None
        assert goal.goal_monthly_rate == round(100000 * 52 / 12)

    def test_mf_every_n_months_normalization(self) -> None:
        cat = _make_category(
            budgeted=0,
            balance=0,
            goal_type="MF",
            goal_target=200000,
            goal_cadence=4,  # every 3 months
        )
        result = build_planning_insights_from_months(
            [_make_month_detail(date(2026, 1, 1), [cat])]
        )
        goal = result.categories[0].goal
        assert goal is not None
        assert goal.goal_monthly_rate == 200000 // 3

    @pytest.mark.parametrize("goal_type", ["TB", "NEED", "DEBT", None])
    def test_rate_omitted_for_unscheduled(self, goal_type: Optional[str]) -> None:
        kwargs: Dict[str, Any] = {"budgeted": 0, "balance": 0}
        if goal_type is not None:
            kwargs["goal_type"] = goal_type
            kwargs["goal_target"] = 100000
        cat = _make_category(**kwargs)
        result = build_planning_insights_from_months(
            [_make_month_detail(date(2026, 1, 1), [cat])]
        )
        goal = result.categories[0].goal
        if goal_type is None:
            assert goal is None
        else:
            assert goal is not None
            assert goal.goal_monthly_rate is None

    def test_rate_omitted_when_snoozed(self) -> None:
        cat = _make_category(
            budgeted=0,
            balance=0,
            goal_type="TBD",
            goal_target=100000,
            goal_overall_left=2250000,
            goal_months_to_budget=3,
            goal_snoozed_at=datetime(2026, 1, 1, 12, 0, 0),
        )
        result = build_planning_insights_from_months(
            [_make_month_detail(date(2026, 1, 1), [cat])]
        )
        goal = result.categories[0].goal
        assert goal is not None
        assert goal.goal_monthly_rate is None


class TestDerivedStats:
    def test_funding_ratio_06_overfunded(self) -> None:
        cat = _make_category(budgeted=300000, activity=-180000, balance=540000)
        result = build_planning_insights_from_months(
            [
                _make_month_detail(date(2026, 1, 1), [cat]),
                _make_month_detail(date(2026, 2, 1), [cat]),
                _make_month_detail(date(2026, 3, 1), [cat]),
            ]
        )
        derived = result.categories[0].derived
        assert derived.average_monthly_budgeted == 300000
        assert derived.average_monthly_activity == -180000
        assert derived.funding_ratio == 0.6

    def test_funding_ratio_undefined_when_budgeted_zero(self) -> None:
        cat = _make_category(budgeted=0, activity=-10000, balance=0)
        result = build_planning_insights_from_months(
            [_make_month_detail(date(2026, 1, 1), [cat])]
        )
        assert result.categories[0].derived.funding_ratio is None

    def test_balance_runway_months(self) -> None:
        cat = _make_category(budgeted=200000, activity=-200000, balance=600000)
        result = build_planning_insights_from_months(
            [
                _make_month_detail(date(2026, 1, 1), [cat]),
                _make_month_detail(date(2026, 2, 1), [cat]),
                _make_month_detail(date(2026, 3, 1), [cat]),
            ]
        )
        # balance 600000 / (200000/month) = 3 months
        assert result.categories[0].derived.balance_runway_months == 3.0

    def test_balance_runway_undefined_when_no_activity(self) -> None:
        cat = _make_category(budgeted=1000, activity=0, balance=5000)
        result = build_planning_insights_from_months(
            [_make_month_detail(date(2026, 1, 1), [cat])]
        )
        assert result.categories[0].derived.balance_runway_months is None

    def test_overfunded_versus_target(self) -> None:
        cat = _make_category(
            budgeted=0,
            balance=150000,
            goal_type="TB",
            goal_target=100000,
            goal_target_formatted="$100.00",
        )
        result = build_planning_insights_from_months(
            [_make_month_detail(date(2026, 1, 1), [cat])]
        )
        assert result.categories[0].derived.overfunded == 50000

    def test_overfunded_omitted_without_balance_target(self) -> None:
        cat = _make_category(
            budgeted=0,
            balance=150000,
            goal_type="MF",
            goal_target=100000,
            goal_cadence=1,
        )
        result = build_planning_insights_from_months(
            [_make_month_detail(date(2026, 1, 1), [cat])]
        )
        assert result.categories[0].derived.overfunded is None

    def test_undefined_derivations_omitted_from_json(self) -> None:
        cat = _make_category(budgeted=0, activity=0, balance=0)
        result = build_planning_insights_from_months(
            [_make_month_detail(date(2026, 1, 1), [cat])]
        )
        dumped = json.loads(result.model_dump_json(exclude_none=True))
        derived = dumped["categories"][0]["derived"]
        assert "funding_ratio" not in derived
        assert "balance_runway_months" not in derived
        assert "overfunded" not in derived


# ---------------------------------------------------------------------------
# 1.4 Zeroed error responses (exercised via the resource handler)
# ---------------------------------------------------------------------------


async def _call_tool(
    since_date: Optional[str], until_date: Optional[str], mock: MockYnabService
) -> str:
    """Call the ``get_plan_insights`` tool and return its raw JSON text."""
    mcp = FastMCP("test")
    register(mcp, mock)
    async with Client(mcp) as client:
        result = await client.call_tool(
            "get_plan_insights",
            {"since_date": since_date, "until_date": until_date},
        )
        return result.content[0].text


class TestZeroedErrorResponses:
    def test_unparseable_date(self) -> None:
        mock = MockYnabService()
        data = json.loads(asyncio.run(_call_tool("not-a-date", None, mock)))
        assert data["error"]
        assert data["months"] == []
        assert data["categories"] == []
        assert data["plan_horizon_reached"] is False

    def test_inverted_window(self) -> None:
        mock = MockYnabService()
        data = json.loads(asyncio.run(_call_tool("2026-03", "2026-01", mock)))
        assert "before" in data["error"]
        assert data["months"] == []
        assert data["categories"] == []

    def test_upstream_failure(self) -> None:
        mock = MockYnabService(
            summaries=[],
            months={
                "2024-01": _make_month_detail(date(2024, 1, 1), []),
                "2024-02": _make_month_detail(date(2024, 2, 1), []),
                "2024-03": _make_month_detail(date(2024, 3, 1), []),
            },
        )
        # A generic (non-404) failure on a window month is an upstream
        # failure, not a missing plan — it must propagate.
        mock._fail = {"2024-02"}
        data = json.loads(asyncio.run(_call_tool("2024-01", "2024-03", mock)))
        assert "YNAB API failure" in data["error"]
        assert data["months"] == []
        assert data["categories"] == []

    def test_zero_response_shape(self) -> None:
        resp = zero_response("boom")
        assert resp.error == "boom"
        assert resp.months == []
        assert resp.categories == []
        assert resp.plan_horizon_reached is False


# ---------------------------------------------------------------------------
# 2.1 Resource registration catalog
# ---------------------------------------------------------------------------


class TestCatalogRegistration:
    def test_tool_listed(self) -> None:
        async def run() -> set:
            mcp = FastMCP("test")
            register(mcp, MockYnabService())
            async with Client(mcp) as client:
                tools = await client.list_tools()
                return {t.name for t in tools}

        names = asyncio.run(run())
        assert "get_plan_insights" in names

    def test_resource_template_listed(self) -> None:
        async def run() -> set:
            mcp = FastMCP("test")
            register(mcp, MockYnabService())
            async with Client(mcp) as client:
                templates = await client.list_resource_templates()
                return {t.uriTemplate for t in templates}

        uris = asyncio.run(run())
        assert "data://plan-insights{?since_date,until_date}" in uris

    def test_insights_uri_does_not_collide_with_months_template(self) -> None:
        """``data://months/insights`` was shadowed by ``data://months/{month_date}``.

        The plan-insights resource must use a URI no other template matches,
        otherwise reads fail with "Invalid month_date format".
        """

        async def run() -> List[str]:
            mcp = FastMCP("test")
            register(mcp, MockYnabService())
            async with Client(mcp) as client:
                templates = await client.list_resource_templates()
                return [t.uriTemplate for t in templates]

        uris = asyncio.run(run())
        assert "data://months/insights{?since_date,until_date}" not in uris
        assert "data://plan-insights{?since_date,until_date}" in uris


# ---------------------------------------------------------------------------
# 2.3 ResourcesAsTools exposes the tool form
# ---------------------------------------------------------------------------


def _texts_of(items: Any) -> List[str]:
    out: List[str] = []
    for item in items or []:
        if isinstance(item, dict) and "text" in item:
            out.append(item["text"])
        elif hasattr(item, "text"):
            out.append(item.text)
    return out


class TestResourcesAsTools:
    def test_plan_insights_tool_matches_resource_form(self) -> None:
        """The tool form and the resource form must return identical payloads."""
        from fastmcp.server.transforms import ResourcesAsTools

        cat = _make_category(budgeted=1000, activity=-500, balance=500)
        months = {
            "2026-01": _make_month_detail(date(2026, 1, 1), [cat]),
            "2026-02": _make_month_detail(date(2026, 2, 1), [cat]),
            "2026-03": _make_month_detail(date(2026, 3, 1), [cat]),
        }
        mock = MockYnabService(summaries=[], months=months)
        uri = "data://plan-insights?since_date=2026-01&until_date=2026-03"

        async def run() -> tuple:
            mcp = FastMCP("test")
            register(mcp, mock)
            mcp.add_transform(ResourcesAsTools(mcp))
            async with Client(mcp) as client:
                tools = {t.name for t in await client.list_tools()}
                resource = await client.read_resource(uri)
                tool_result = await client.call_tool(
                    "get_plan_insights",
                    {"since_date": "2026-01", "until_date": "2026-03"},
                )
                return tools, resource, tool_result

        tools, resource, tool_result = asyncio.run(run())

        assert "get_plan_insights" in tools
        assert "read_resource" in tools
        assert "list_resources" in tools

        resource_data = json.loads(_texts_of(resource)[0])
        tool_data = json.loads(_texts_of(tool_result.content)[0])
        assert tool_data == resource_data
        assert [m["month"] for m in tool_data["months"]] == [
            "2026-01",
            "2026-02",
            "2026-03",
        ]


# ---------------------------------------------------------------------------
# 2.2 In-process TTL cache
# ---------------------------------------------------------------------------


class TestCache:
    def teardown_method(self) -> None:
        _cache_clear()

    def test_repeated_reads_dedupe_fan_out(self) -> None:
        _cache_clear()
        cat = _make_category(budgeted=1000, activity=-500, balance=500)
        months = {
            "2026-01": _make_month_detail(date(2026, 1, 1), [cat]),
            "2026-02": _make_month_detail(date(2026, 2, 1), [cat]),
            "2026-03": _make_month_detail(date(2026, 3, 1), [cat]),
        }
        mock = MockYnabService(summaries=[], months=months)

        async def run() -> None:
            mcp = FastMCP("test")
            register(mcp, mock)
            async with Client(mcp) as client:
                await client.call_tool(
                    "get_plan_insights",
                    {"since_date": "2026-01", "until_date": "2026-03"},
                )
                await client.call_tool(
                    "get_plan_insights",
                    {"since_date": "2026-01", "until_date": "2026-03"},
                )

        asyncio.run(run())
        # Two reads, one underlying fan-out of 3 months.
        assert mock.get_plan_month_calls == ["2026-01", "2026-02", "2026-03"]

    def test_cache_clear_resets(self) -> None:
        _cache_set(("x", "y"), "payload")
        _cache_clear()
        from ynab_http_mcp.tools.planning_insights import _cache_get

        assert _cache_get(("x", "y")) is None

    def test_ttl_constant_set(self) -> None:
        assert _TTL_SECONDS > 0
