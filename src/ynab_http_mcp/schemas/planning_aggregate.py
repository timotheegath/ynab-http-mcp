"""
Planning insights aggregate schemas for YNAB HTTP MCP.

This module defines the ``PlanInsightsResponse`` model and its supporting
types, plus the pure builders that assemble the aggregate from the month
fan-out and the window / forward-month resolution helpers used by the
``get_plan_insights`` tool.

The aggregate is the third "read" pillar (after transactions — what
happened, and money movements — how the user re-plans): it reports the
user's *intended* plan state across a multi-month window, so a client agent
can ground an expense-affordability conversation in declared goals,
demonstrated assignment behavior, and already-written future assignments.

Three forecasting ingredients ship separately, never merged:

1. Declared schedule — a promoted goal block (type, target amount, target
   date, cadence / cadence frequency, under-funded / overall-left / months-
   to-budget integers, percentage complete, snoozed state, prose summaries)
   plus a server-computed ``goal_monthly_rate``.
2. Demonstrated behavior — per-month budgeted / activity / balance series
   (integer milliunits *and* formatted strings) plus derived arithmetic
   (averages, funding ratio, balance runway, overfunded vs target).
3. Already-written future months — every future month already present in
   the plan, with the same per-category series and month-level
   Ready-to-Assign, plus a ``plan_horizon_reached`` flag when YNAB's
   future-planning horizon truncates the walk.

Ready-to-Assign is reported month-level (shared across categories). Income
is deliberately excluded, and the payload never asserts any expected or
projected future balance — rolling the goal monthly rate forward is the
client agent's composition.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

import ynab

from ynab_http_mcp.schemas.categories import (
    _explain_goal_funding_status,
    _explain_goal_type,
)
from ynab_http_mcp.schemas.transaction_aggregate import _ynab_format
from ynab_http_mcp.utils.dates import parse_month_date


# ---------------------------------------------------------------------------
# Supporting models
# ---------------------------------------------------------------------------


class PlanInsightsMonth(BaseModel):
    """Month-level fields shared across every category for one month.

    ``ready_to_assign`` is YNAB's "Ready to Assign" (to-be-budgeted) amount.
    Income is deliberately excluded — unearned income is no planning basis.
    """

    month: str = Field(..., description="Month in YYYY-MM format")
    ready_to_assign: int = Field(
        ..., description="Ready-to-Assign (to-be-budgeted) in milliunits"
    )
    ready_to_assign_formatted: str = Field(
        ..., description="Same value formatted in the plan's currency"
    )


class PlanInsightsCategoryMonth(BaseModel):
    """One category's budgeted / activity / balance in a single month.

    Each amount ships as an integer milliunit value *and* its formatted
    twin so the consumer can do arithmetic without string parsing.
    """

    month: str = Field(..., description="Month in YYYY-MM format")
    budgeted: int = Field(..., description="Assigned (budgeted) amount in milliunits")
    budgeted_formatted: str = Field(
        ..., description="Assigned amount formatted in the plan's currency"
    )
    activity: int = Field(..., description="Activity amount in milliunits")
    activity_formatted: str = Field(
        ..., description="Activity amount formatted in the plan's currency"
    )
    balance: int = Field(..., description="Available balance in milliunits")
    balance_formatted: str = Field(
        ..., description="Available balance formatted in the plan's currency"
    )


class PlanInsightsGoal(BaseModel):
    """Promoted goal block exposing the raw integers needed for arithmetic.

    Every field is optional so ``exclude_none`` drops absent values: a
    goal-backed category carries all its integers, while fields that do not
    apply to a given goal type (e.g. no target date on a TB goal) are
    omitted. ``goal_monthly_rate`` is the server-computed contribution per
    month; it is omitted for unscheduled (TB / NEED) or snoozed goals.
    """

    goal_type: Optional[str] = Field(None, description="TB / TBD / MF / NEED / DEBT")
    goal_target: Optional[int] = Field(None, description="Target amount in milliunits")
    goal_target_formatted: Optional[str] = Field(
        None, description="Target amount formatted in the plan's currency"
    )
    goal_target_date: Optional[str] = Field(
        None, description="Target date (YYYY-MM-DD)"
    )
    goal_cadence: Optional[int] = Field(None, description="Goal cadence (0-14)")
    goal_cadence_frequency: Optional[int] = Field(
        None, description="Cadence frequency multiplier"
    )
    under_funded: Optional[int] = Field(
        None, description="Funding still needed this month, in milliunits"
    )
    under_funded_formatted: Optional[str] = Field(
        None, description="Under-funded amount formatted in the plan's currency"
    )
    overall_left: Optional[int] = Field(
        None, description="Funding still needed this goal period, in milliunits"
    )
    overall_left_formatted: Optional[str] = Field(
        None, description="Overall-left amount formatted in the plan's currency"
    )
    months_to_budget: Optional[int] = Field(
        None, description="Months (incl. current) left in the goal period"
    )
    percentage_complete: Optional[int] = Field(
        None, description="Goal completion percentage"
    )
    snoozed_at: Optional[str] = Field(None, description="When the goal was snoozed")
    goal_monthly_rate: Optional[int] = Field(
        None,
        description=(
            "Server-computed contribution the schedule demands per month, in "
            "milliunits (TBD: overall_left ÷ months_to_budget; MF: target "
            "normalized by cadence/frequency). Omitted for TB/NEED/snoozed."
        ),
    )
    goal_summary: Optional[str] = Field(
        None, description="Plain-English goal description"
    )
    goal_status: Optional[str] = Field(
        None, description="Plain-English funding progress sentence"
    )


class PlanInsightsDerived(BaseModel):
    """Server-computed derived arithmetic for one category.

    Derivations that are undefined (e.g. a funding ratio when the average
    budget is zero, or an overfunded amount when there is no balance target)
    are omitted rather than fabricated.
    """

    average_monthly_budgeted: Optional[int] = Field(
        None, description="Average monthly assigned amount, in milliunits"
    )
    average_monthly_activity: Optional[int] = Field(
        None, description="Average monthly activity, in milliunits"
    )
    funding_ratio: Optional[float] = Field(
        None,
        description=(
            "|average activity| ÷ |average budgeted|. Below 1.0 is chronically "
            "overfunded; above 1.0 is chronically underfunded."
        ),
    )
    balance_runway_months: Optional[float] = Field(
        None, description="Months the current balance covers at the activity rate"
    )
    overfunded: Optional[int] = Field(
        None, description="Balance minus goal target (TB/TBD only), in milliunits"
    )


class PlanInsightsCategory(BaseModel):
    """One category's series, goal, and derived stats across the window."""

    category_id: str = Field(..., description="Category UUID")
    category_name: str = Field(..., description="Category name")
    hidden: bool = Field(..., description="Whether the category is hidden")
    months: List[PlanInsightsCategoryMonth] = Field(
        ..., description="Per-month budgeted / activity / balance series"
    )
    goal: Optional[PlanInsightsGoal] = Field(
        None, description="Promoted goal block; omitted when the category has no goal"
    )
    derived: PlanInsightsDerived = Field(
        ..., description="Derived planning arithmetic for the category"
    )


class PlanInsightsResponse(BaseModel):
    """Read-only aggregate of plan state over a multi-month window.

    See the ``planning-insights`` capability spec for the full contract.
    """

    months: List[PlanInsightsMonth] = Field(
        ..., description="Month-level Ready-to-Assign for every month in scope"
    )
    categories: List[PlanInsightsCategory] = Field(
        ..., description="Per-category series, goal, and derived stats"
    )
    plan_horizon_reached: bool = Field(
        ...,
        description=(
            "True when YNAB refused a further future month and the walk stopped "
            "at the plan's future-planning horizon"
        ),
    )
    error: Optional[str] = Field(None, description="Populated when the read fails")


# ---------------------------------------------------------------------------
# Window and forward-month resolution
# ---------------------------------------------------------------------------


def _add_months(first_of_month: date, months: int) -> date:
    """Add ``months`` to a first-of-month ``date``, clamping to day 1."""
    year = first_of_month.year
    month = first_of_month.month + months
    while month <= 0:
        month += 12
        year -= 1
    while month > 12:
        month -= 12
        year += 1
    return date(year, month, 1)


def default_window_months(now: Optional[date] = None) -> tuple[date, date]:
    """Return ``(since, until)`` as first-of-month ``date``s for the last 3
    calendar months including the current month (both inclusive)."""
    today = now or date.today()
    this_month = today.replace(day=1)
    return _add_months(this_month, -2), this_month


def parse_month_bound(value: str) -> date:
    """Parse a month spec (``YYYY-MM`` or ``YYYY-MM-DD``) and floor to the
    first day of that month. Raises ``ValueError`` on unparseable input."""
    return parse_month_date(value).replace(day=1).date()


def resolve_month_window(
    since_date: Optional[str] = None,
    until_date: Optional[str] = None,
    now: Optional[date] = None,
) -> tuple[date, date]:
    """Resolve ``(since, until)`` first-of-month bounds, both inclusive.

    A missing side defaults to the default 3-month window. Day components
    are floored; ``until_date`` is the last whole month included. Raises
    ``ValueError`` for unparseable month specifiers.
    """
    if since_date is None and until_date is None:
        return default_window_months(now)

    default_since, default_until = default_window_months(now)
    since = parse_month_bound(since_date) if since_date is not None else default_since
    until = parse_month_bound(until_date) if until_date is not None else default_until
    return since, until


def months_inclusive(since: date, until: date) -> List[date]:
    """Return the first day of every month in ``[since, until]`` inclusive."""
    out: List[date] = []
    year, month = since.year, since.month
    while True:
        cur = date(year, month, 1)
        if cur > until:
            break
        out.append(cur)
        month += 1
        if month > 12:
            month = 1
            year += 1
    return out


def _to_month_date(value: Any) -> Optional[date]:
    """Normalize a month specifier (``date`` / ``datetime`` / ``str``) to a
    first-of-month ``date``, or ``None`` when it cannot be normalized."""
    if isinstance(value, datetime):
        return value.replace(day=1).date()
    if isinstance(value, date):
        return value.replace(day=1)
    if isinstance(value, str):
        try:
            return parse_month_date(value).replace(day=1).date()
        except ValueError:
            return None
    return None


def discover_forward_months(plan_months: Any, until: date) -> List[date]:
    """Return future months (strictly after ``until``) present in the plan.

    ``plan_months`` is a list of ``ynab.MonthSummary`` (or duck-typed
    objects with a ``.month`` attribute / bare month specifiers). Deleted
    months are skipped. The result is de-duplicated and ascending.
    """
    out: List[date] = []
    for summary in plan_months or []:
        if getattr(summary, "deleted", False):
            continue
        month_spec = getattr(summary, "month", summary)
        month_value = _to_month_date(month_spec)
        if month_value is not None and month_value > until:
            out.append(month_value)
    return sorted(set(out))


# ---------------------------------------------------------------------------
# Goal-block and derived-stat helpers
# ---------------------------------------------------------------------------


def _iso_str(value: Any) -> Optional[str]:
    """Return ``value`` as an ISO date/datetime string, or ``None``."""
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, date):
        return value.isoformat()
    return str(value)


def _goal_monthly_rate(raw: ynab.Category) -> Optional[int]:
    """Return the goal's contribution per month in milliunits, or ``None``.

    Scheduled goals only: TBD uses ``overall_left ÷ months_to_budget``; MF
    normalizes the target by cadence / frequency. Unscheduled (TB / NEED),
    snoozed, or one-time (MF cadence 0) goals return ``None``.
    """
    if raw.goal_snoozed_at is not None:
        return None

    goal_type = raw.goal_type
    if goal_type == "TBD":
        overall_left = raw.goal_overall_left
        months = raw.goal_months_to_budget
        if overall_left is None or not months:
            return None
        return overall_left // months

    if goal_type == "MF":
        target = raw.goal_target
        if target is None:
            return None
        cadence = raw.goal_cadence
        frequency = raw.goal_cadence_frequency

        if cadence is None or cadence == 0:
            return None  # one-time, no repetition
        if cadence == 1:  # monthly, frequency months
            if not frequency:
                return None
            return target // frequency
        if cadence == 2:  # weekly, frequency weeks (52/12 weeks per month)
            if not frequency:
                return None
            return round(target * 52 / (12 * frequency))
        if 3 <= cadence <= 12:  # every (cadence - 1) months
            return target // (cadence - 1)
        if cadence == 13:  # yearly, frequency years
            if not frequency:
                return None
            return target // (frequency * 12)
        if cadence == 14:  # every 2 years
            return target // 24
        return None

    return None


def _safe_prose(fn: Any, raw: ynab.Category) -> Optional[str]:
    """Run a prose helper, degrading to ``None`` on any malformed goal."""
    try:
        return fn(raw)
    except Exception:
        return None


def _promote_goal(raw: ynab.Category) -> Optional[PlanInsightsGoal]:
    """Build the promoted goal block for a category, or ``None`` if goal-less."""
    if raw.goal_type is None:
        return None
    return PlanInsightsGoal(
        goal_type=raw.goal_type,
        goal_target=raw.goal_target,
        goal_target_formatted=raw.goal_target_formatted,
        goal_target_date=_iso_str(raw.goal_target_date),
        goal_cadence=raw.goal_cadence,
        goal_cadence_frequency=raw.goal_cadence_frequency,
        under_funded=raw.goal_under_funded,
        under_funded_formatted=raw.goal_under_funded_formatted,
        overall_left=raw.goal_overall_left,
        overall_left_formatted=raw.goal_overall_left_formatted,
        months_to_budget=raw.goal_months_to_budget,
        percentage_complete=raw.goal_percentage_complete,
        snoozed_at=_iso_str(raw.goal_snoozed_at),
        goal_monthly_rate=_goal_monthly_rate(raw),
        goal_summary=_safe_prose(_explain_goal_type, raw),
        goal_status=_safe_prose(_explain_goal_funding_status, raw),
    )


def _derive_stats(
    series: List[PlanInsightsCategoryMonth],
    goal: Optional[PlanInsightsGoal],
    window_month_count: int,
) -> PlanInsightsDerived:
    """Compute derived arithmetic over the window slice of ``series``.

    ``series`` includes window months followed by forward months; only the
    first ``window_month_count`` entries are demonstrated behavior.
    """
    window = series[:window_month_count]
    n = len(window)

    average_monthly_budgeted: Optional[int] = None
    average_monthly_activity: Optional[int] = None
    funding_ratio: Optional[float] = None
    balance_runway_months: Optional[float] = None
    overfunded: Optional[int] = None

    if n > 0:
        sum_budgeted = sum(m.budgeted for m in window)
        sum_activity = sum(m.activity for m in window)
        last_balance = window[-1].balance

        average_monthly_budgeted = sum_budgeted // n
        average_monthly_activity = sum_activity // n

        if sum_budgeted != 0:
            funding_ratio = round(abs(sum_activity) / abs(sum_budgeted), 4)
        if sum_activity != 0:
            balance_runway_months = round(last_balance * n / abs(sum_activity), 2)

    if (
        goal is not None
        and goal.goal_type in ("TB", "TBD")
        and goal.goal_target is not None
    ):
        if n > 0:
            overfunded = window[-1].balance - goal.goal_target

    return PlanInsightsDerived(
        average_monthly_budgeted=average_monthly_budgeted,
        average_monthly_activity=average_monthly_activity,
        funding_ratio=funding_ratio,
        balance_runway_months=balance_runway_months,
        overfunded=overfunded,
    )


# ---------------------------------------------------------------------------
# Pure assembly
# ---------------------------------------------------------------------------


def _month_key(value: Any) -> str:
    """Return the ``YYYY-MM`` key for a month value."""
    if isinstance(value, datetime):
        return value.strftime("%Y-%m")
    if isinstance(value, date):
        return value.strftime("%Y-%m")
    return str(value)[:7]


def _find_category(
    detail: ynab.MonthDetail, category_id: str
) -> Optional[ynab.Category]:
    for category in detail.categories or []:
        if str(category.id) == category_id:
            return category
    return None


def _fmt(value: int, sdk_formatted: Optional[str], template: Optional[str]) -> str:
    if sdk_formatted:
        return sdk_formatted
    return _ynab_format(value, template)


def build_planning_insights_from_months(
    month_details: List[ynab.MonthDetail],
    plan_horizon_reached: bool = False,
    window_month_count: Optional[int] = None,
) -> "PlanInsightsResponse":
    """Assemble a ``PlanInsightsResponse`` from ordered ``MonthDetail`` objects.

    ``month_details`` is ascending: window months then forward months.
    ``window_month_count`` separates demonstrated-behavior months (the window)
    from already-written future months for derived arithmetic; when omitted,
    every month is treated as part of the window.
    """
    if not month_details:
        return PlanInsightsResponse(
            months=[],
            categories=[],
            plan_horizon_reached=plan_horizon_reached,
            error=None,
        )

    wcount = (
        window_month_count if window_month_count is not None else len(month_details)
    )

    # Canonical category set ordered by first appearance; name / hidden /
    # deleted are taken from the latest appearance.
    latest_by_id: Dict[str, ynab.Category] = {}
    order: List[str] = []
    for detail in month_details:
        for category in detail.categories or []:
            cid = str(category.id)
            if cid not in latest_by_id:
                order.append(cid)
            latest_by_id[cid] = category

    # Currency template for fallback formatting.
    template: Optional[str] = None
    for detail in month_details:
        if detail.to_be_budgeted_formatted:
            template = detail.to_be_budgeted_formatted
            break
    if template is None:
        for cid in order:
            template_cat = latest_by_id[cid]
            candidate = (
                template_cat.budgeted_formatted
                or template_cat.activity_formatted
                or template_cat.balance_formatted
            )
            if candidate:
                template = candidate
                break

    month_keys = [_month_key(detail.month) for detail in month_details]

    months_out: List[PlanInsightsMonth] = []
    for detail in month_details:
        rta = int(detail.to_be_budgeted or 0)
        months_out.append(
            PlanInsightsMonth(
                month=_month_key(detail.month),
                ready_to_assign=rta,
                ready_to_assign_formatted=_fmt(
                    rta, detail.to_be_budgeted_formatted, template
                ),
            )
        )

    categories_out: List[PlanInsightsCategory] = []
    for cid in order:
        latest = latest_by_id[cid]
        if latest.deleted:
            continue

        series: List[PlanInsightsCategoryMonth] = []
        for detail, key in zip(month_details, month_keys):
            raw = _find_category(detail, cid)
            if raw is None:
                series.append(
                    PlanInsightsCategoryMonth(
                        month=key,
                        budgeted=0,
                        budgeted_formatted=_ynab_format(0, template),
                        activity=0,
                        activity_formatted=_ynab_format(0, template),
                        balance=0,
                        balance_formatted=_ynab_format(0, template),
                    )
                )
                continue
            budgeted = int(raw.budgeted or 0)
            activity = int(raw.activity or 0)
            balance = int(raw.balance or 0)
            series.append(
                PlanInsightsCategoryMonth(
                    month=key,
                    budgeted=budgeted,
                    budgeted_formatted=_fmt(budgeted, raw.budgeted_formatted, template),
                    activity=activity,
                    activity_formatted=_fmt(activity, raw.activity_formatted, template),
                    balance=balance,
                    balance_formatted=_fmt(balance, raw.balance_formatted, template),
                )
            )

        goal = _promote_goal(latest)
        categories_out.append(
            PlanInsightsCategory(
                category_id=cid,
                category_name=latest.name,
                hidden=bool(latest.hidden),
                months=series,
                goal=goal,
                derived=_derive_stats(series, goal, wcount),
            )
        )

    return PlanInsightsResponse(
        months=months_out,
        categories=categories_out,
        plan_horizon_reached=plan_horizon_reached,
        error=None,
    )


def zero_response(error: str) -> "PlanInsightsResponse":
    """Return a fully zeroed response with ``error`` populated."""
    return PlanInsightsResponse(
        months=[],
        categories=[],
        plan_horizon_reached=False,
        error=error,
    )
