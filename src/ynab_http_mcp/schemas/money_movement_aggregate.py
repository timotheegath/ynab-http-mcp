"""
Money movement aggregate schemas for YNAB HTTP MCP.

This module defines the ``MoneyMovementInsightsResponse`` model and its
supporting types. The aggregate is a pre-computed view of the money
movement collection over a configurable time window:

- monthly buckets (zero-filled across the requested window)
- absolute total moved (YNAB-formatted currency strings)
- TBA (Ready to Assign) vs other-category source split
- top-5 source categories and top-5 destination categories by absolute
  amount
- recurring ``(from_category, to_category)`` pairs appearing at least
  twice in the window
- ``movement_trend`` — a directional label (``"increasing"``,
  ``"decreasing"``, ``"stable"``) computed from the monthly totals
- ``proactive_pct`` — fraction of movements made on day ≤ 7 of the month
- ``planning_health`` — a derived label (``"excellent"`` / ``"healthy"``
  / ``"mixed"`` / ``"reactive"``) summarising planning quality

Per the Lean / Full / Aggregate convention, this is the Aggregate
layer. It is exposed at ``data://money-movements/insights`` and
``data://months/{month_date}/money-movements/insights`` and never
embedded in lean resources.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Any, Callable, Dict, List, Literal, Optional, Tuple

from pydantic import BaseModel, Field

import ynab

from ynab_http_mcp.schemas.transaction_aggregate import (
    _classify_trend,
    _months_in_window,
    _ynab_format,
)


# Movement trend: a directional label computed from the monthly totals
# series. Mirrors the spending_trend classification.
MovementTrend = Literal["increasing", "decreasing", "stable"]

# Planning health: a derived summary of how the budget diverged from
# the plan. The classification rules are documented in
# ``_classify_planning_health``.
PlanningHealth = Literal["excellent", "healthy", "mixed", "reactive"]


# ---------------------------------------------------------------------------
# Module constants
# ---------------------------------------------------------------------------

#: Movements made on or before this day of the month count as proactive.
PROACTIVE_DAY_THRESHOLD = 7

#: From-TBA ratio at/above which a window is "healthy" (when no
#: recurring pairs are present).
_PLANNING_HEALTH_TBA_HEALTHY = 0.80

#: From-TBA ratio below which a window is "reactive".
_PLANNING_HEALTH_TBA_MIXED = 0.50

#: Recurring-pair count at/above which "healthy" can no longer apply.
_PLANNING_HEALTH_RECURRING_HEALTHY_MAX = 0

#: Recurring-pair count at/above which a window is "reactive".
_PLANNING_HEALTH_RECURRING_REACTIVE_MIN = 3


# ---------------------------------------------------------------------------
# Supporting models
# ---------------------------------------------------------------------------


class MonthlyMoneyMovementBucket(BaseModel):
    """One calendar month's worth of money-movement aggregates.

    The list of ``MonthlyMoneyMovementBucket`` is zero-filled — every
    month in the requested window has an entry, even months with no
    movements (with ``movement_count == 0`` and zero formatted
    amounts).
    """

    month: str = Field(..., description="Month in YYYY-MM format")
    movement_count: int = Field(
        ..., description="Number of money movements in the month"
    )
    from_tba_count: int = Field(
        ..., description="Movements sourced from Ready to Assign"
    )
    from_other_count: int = Field(
        ..., description="Movements sourced from another category"
    )
    from_tba_total_formatted: str = Field(
        ..., description="TBA-sourced total, YNAB-formatted"
    )
    from_other_total_formatted: str = Field(
        ..., description="Other-category-sourced total, YNAB-formatted"
    )
    average_moved_day_of_month: Optional[float] = Field(
        None,
        description=(
            "Average day-of-month of ``moved_at`` across the month's "
            "movements; None when ``movement_count == 0``"
        ),
    )


class SourceCategoryAggregate(BaseModel):
    """Top-N aggregate row for a single source category (donor).

    TBA (when ``from_category_id is None``) is reported as a single
    aggregate row with ``category_name == "Ready to Assign"``.
    """

    category_id: Optional[str] = Field(
        None,
        description=(
            "Source category UUID; None for the TBA aggregate ('Ready to Assign')"
        ),
    )
    category_name: str = Field(
        ...,
        description="Source category name; 'Ready to Assign' for the TBA aggregate",
    )
    movement_count: int = Field(
        ..., description="Number of movements sourced from this category"
    )
    total_milliunits: int = Field(
        ...,
        description=(
            "Sum of moved amounts in milliunits (negative for outflows "
            "from the source); sort key for top_source_categories"
        ),
    )
    total_formatted: str = Field(
        ..., description="Same value formatted in the plan's currency"
    )
    average_milliunits: int = Field(
        ..., description="total_milliunits / movement_count, rounded toward zero"
    )


class DestinationCategoryAggregate(BaseModel):
    """Top-N aggregate row for a single destination category (recipient)."""

    category_id: str = Field(..., description="Destination category UUID")
    category_name: str = Field(
        ..., description="Destination category name; 'Unknown' if unresolved"
    )
    movement_count: int = Field(
        ..., description="Number of movements into this category"
    )
    total_milliunits: int = Field(
        ...,
        description=(
            "Sum of moved amounts in milliunits (positive for inflows "
            "into the destination); sort key for top_destination_categories"
        ),
    )
    total_formatted: str = Field(
        ..., description="Same value formatted in the plan's currency"
    )
    average_milliunits: int = Field(
        ..., description="total_milliunits / movement_count, rounded toward zero"
    )


class RecurringMovementPair(BaseModel):
    """A ``(from_category, to_category)`` pair that appears at least twice
    in the window."""

    from_category_id: Optional[str] = Field(
        None,
        description="Source category UUID; None for Ready to Assign",
    )
    from_category_name: str = Field(
        ...,
        description="Source category name; 'Ready to Assign' for None IDs",
    )
    to_category_id: str = Field(..., description="Destination category UUID")
    to_category_name: str = Field(
        ..., description="Destination category name; 'Unknown' if unresolved"
    )
    movement_count: int = Field(
        ..., description="Number of times this pair appears in the window"
    )
    total_formatted: str = Field(
        ..., description="Sum of moved amounts, YNAB-formatted"
    )


class MoneyMovementInsightsResponse(BaseModel):
    """Pre-computed insights over a window of money movements.

    See the ``money-movement-aggregate-resource`` capability spec for
    the full contract.
    """

    period_start: str = Field(
        ..., description="ISO date of the first day of the analysis window"
    )
    period_end: str = Field(
        ...,
        description="ISO date of the day after the last day of the analysis window",
    )
    monthly_buckets: List[MonthlyMoneyMovementBucket] = Field(
        ..., description="One bucket per calendar month in the window (zero-filled)"
    )
    total_movement_count: int = Field(
        ..., description="Number of money-movement rows in the window"
    )
    total_moved_formatted: str = Field(
        ..., description="Absolute sum of amount over the window, YNAB-formatted"
    )
    average_movement_formatted: str = Field(
        ...,
        description=(
            "total_moved / total_movement_count, YNAB-formatted; "
            "'$0.00' if no movements"
        ),
    )
    from_ready_to_assign_count: int = Field(
        ...,
        description="Count of movements where from_category_id is None",
    )
    from_ready_to_assign_total_formatted: str = Field(
        ...,
        description="Sum of amount over TBA-sourced movements, YNAB-formatted",
    )
    from_other_categories_count: int = Field(
        ...,
        description="Count of movements where from_category_id is set",
    )
    from_other_categories_total_formatted: str = Field(
        ...,
        description="Sum of amount over non-TBA-sourced movements, YNAB-formatted",
    )
    top_source_categories: List[SourceCategoryAggregate] = Field(
        ...,
        description=(
            "Top 5 donor categories by absolute total_milliunits "
            "descending; TBA is included as the 'Ready to Assign' "
            "aggregate when it ranks in the top 5"
        ),
    )
    top_destination_categories: List[DestinationCategoryAggregate] = Field(
        ...,
        description="Top 5 recipient categories by absolute total_milliunits descending",
    )
    recurring_pairs: List[RecurringMovementPair] = Field(
        ...,
        description=(
            "Pairs of (from_category_id, to_category_id) appearing at "
            "least twice in the window"
        ),
    )
    movement_trend: MovementTrend = Field(
        ..., description="Directional read of monthly totals over monthly_buckets"
    )
    proactive_pct: Optional[float] = Field(
        None,
        description=(
            "Fraction of movements whose moved_at day-of-month is "
            "<= PROACTIVE_DAY_THRESHOLD; None when total_movement_count == 0"
        ),
    )
    planning_health: PlanningHealth = Field(
        ..., description="Derived summary of planning quality"
    )
    error: Optional[str] = Field(None, description="Populated when computation fails")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _classify_planning_health(
    total_count: int,
    from_tba_ratio: float,
    recurring_pair_count: int,
) -> PlanningHealth:
    """Return the ``planning_health`` label for a window.

    Rules (applied in order):

    - ``total_count == 0``                       → ``"excellent"``
    - ``from_tba_ratio < 0.50``                  → ``"reactive"``
    - ``recurring_pair_count >= 3``              → ``"reactive"``
    - ``from_tba_ratio >= 0.80 and pairs == 0``  → ``"healthy"``
    - otherwise                                 → ``"mixed"``
    """
    if total_count == 0:
        return "excellent"
    if from_tba_ratio < _PLANNING_HEALTH_TBA_MIXED:
        return "reactive"
    if recurring_pair_count >= _PLANNING_HEALTH_RECURRING_REACTIVE_MIN:
        return "reactive"
    if (
        from_tba_ratio >= _PLANNING_HEALTH_TBA_HEALTHY
        and recurring_pair_count <= _PLANNING_HEALTH_RECURRING_HEALTHY_MAX
    ):
        return "healthy"
    return "mixed"


def _movement_month(mv: ynab.MoneyMovement) -> Optional[date]:
    """Return ``mv.month`` as a ``date`` (or ``None`` when unparseable)."""
    month_value = mv.month
    if isinstance(month_value, datetime):
        return month_value.date()
    if isinstance(month_value, date):
        return month_value
    return None


def _movement_day_of_month(mv: ynab.MoneyMovement) -> Optional[int]:
    """Return ``mv.moved_at`` day-of-month, or ``None`` when missing."""
    moved_at = mv.moved_at
    if moved_at is None:
        return None
    return moved_at.day


# ---------------------------------------------------------------------------
# Top-level builder
# ---------------------------------------------------------------------------


def build_money_movement_insights(
    movements: List[ynab.MoneyMovement],
    period_start: date,
    period_end: date,
    category_name_lookup: Callable[[Optional[str]], str],
) -> MoneyMovementInsightsResponse:
    """Compute a ``MoneyMovementInsightsResponse`` from a flat list of
    ``ynab.MoneyMovement`` rows.

    The window is the half-open interval ``[period_start, period_end)``.
    ``category_name_lookup`` maps a category_id to a human-readable
    name; passing ``None`` returns the ``"Ready to Assign"`` sentinel
    for TBA, and any unresolved id should return ``"Unknown"`` (the
    caller is responsible for this fallback so the builder can stay
    deterministic).

    The result is zero-filled across every calendar month in the
    window. An inverted window produces an error response with all
    numeric fields zeroed.
    """
    if period_end <= period_start:
        return MoneyMovementInsightsResponse(
            period_start=period_start.isoformat(),
            period_end=period_end.isoformat(),
            monthly_buckets=[],
            total_movement_count=0,
            total_moved_formatted="$0.00",
            average_movement_formatted="$0.00",
            from_ready_to_assign_count=0,
            from_ready_to_assign_total_formatted="$0.00",
            from_other_categories_count=0,
            from_other_categories_total_formatted="$0.00",
            top_source_categories=[],
            top_destination_categories=[],
            recurring_pairs=[],
            movement_trend="stable",
            proactive_pct=None,
            planning_health="excellent",
            error="period_end must be strictly after period_start",
        )

    months = _months_in_window(period_start, period_end)
    buckets: Dict[str, MonthlyMoneyMovementBucket] = {
        m.strftime("%Y-%m"): MonthlyMoneyMovementBucket(
            month=m.strftime("%Y-%m"),
            movement_count=0,
            from_tba_count=0,
            from_other_count=0,
            from_tba_total_formatted="$0.00",
            from_other_total_formatted="$0.00",
            average_moved_day_of_month=None,
        )
        for m in months
    }

    # Pick a currency template from the first movement that has one.
    template: Optional[str] = None
    for mv in movements:
        if getattr(mv, "amount_formatted", None):
            template = mv.amount_formatted
            break

    # Aggregate accumulators
    total_count = 0
    total_moved_abs = 0
    from_tba_count = 0
    from_tba_total = 0
    from_other_count = 0
    from_other_total = 0
    proactive_hits = 0
    source_sums: Dict[Optional[str], Dict[str, Any]] = {}
    dest_sums: Dict[str, Dict[str, Any]] = {}
    pair_sums: Dict[Tuple[Optional[str], str], Dict[str, Any]] = {}
    monthly_totals: Dict[str, int] = {m.strftime("%Y-%m"): 0 for m in months}
    monthly_day_sums: Dict[str, int] = {m.strftime("%Y-%m"): 0 for m in months}
    monthly_day_counts: Dict[str, int] = {m.strftime("%Y-%m"): 0 for m in months}

    for mv in movements:
        month_value = _movement_month(mv)
        if month_value is None:
            continue
        if month_value < period_start or month_value >= period_end:
            continue
        month_key = month_value.strftime("%Y-%m")
        bucket = buckets.get(month_key)
        if bucket is None:
            # Movement fell outside the months we pre-allocated; skip
            # but keep the totals consistent. This shouldn't happen
            # given the window check above, but be defensive.
            continue

        amount = int(mv.amount or 0)
        from_id: Optional[str] = (
            str(mv.from_category_id) if mv.from_category_id is not None else None
        )
        to_id: str = (
            str(mv.to_category_id) if mv.to_category_id is not None else "Unknown"
        )

        total_count += 1
        total_moved_abs += abs(amount)
        monthly_totals[month_key] += abs(amount)

        day = _movement_day_of_month(mv)
        if day is not None:
            monthly_day_sums[month_key] += day
            monthly_day_counts[month_key] += 1
            if day <= PROACTIVE_DAY_THRESHOLD:
                proactive_hits += 1

        if from_id is None:
            from_tba_count += 1
            from_tba_total += amount
            bucket.from_tba_count += 1
        else:
            from_other_count += 1
            from_other_total += amount
            bucket.from_other_count += 1

        bucket.movement_count = bucket.from_tba_count + bucket.from_other_count

        # Source aggregates (TBA is a synthetic entry with id=None)
        entry = source_sums.setdefault(
            from_id,
            {"count": 0, "total": 0},
        )
        entry["count"] += 1
        entry["total"] += amount

        # Destination aggregates
        dest = dest_sums.setdefault(
            to_id,
            {"count": 0, "total": 0},
        )
        dest["count"] += 1
        dest["total"] += amount

        # Pair aggregates
        pair_entry = pair_sums.setdefault(
            (from_id, to_id),
            {"count": 0, "total": 0},
        )
        pair_entry["count"] += 1
        pair_entry["total"] += amount

    # Finalize per-month formatted totals and average_moved_day_of_month
    for month_key, bucket in buckets.items():
        tba_amount = _bucket_amount(movements, month_key, from_id=None)
        other_amount = _bucket_amount(movements, month_key, from_id__not_none=True)
        bucket.from_tba_total_formatted = _ynab_format(tba_amount, template)
        bucket.from_other_total_formatted = _ynab_format(other_amount, template)
        day_count = monthly_day_counts[month_key]
        if day_count > 0:
            bucket.average_moved_day_of_month = monthly_day_sums[month_key] / day_count
        else:
            bucket.average_moved_day_of_month = None

    # Recompute per-month totals for trend (use abs, sign-positive for trend)
    monthly_total_list: List[int] = [
        monthly_totals.get(m.strftime("%Y-%m"), 0) for m in months
    ]
    trend = _classify_trend([-v for v in monthly_total_list])

    # Top-N source categories (sorted by abs(total) descending)
    source_entries: List[SourceCategoryAggregate] = []
    for source_id, v in source_sums.items():
        if source_id is None:
            name = "Ready to Assign"
        else:
            name = category_name_lookup(source_id) or "Unknown"
        source_entries.append(
            SourceCategoryAggregate(
                category_id=source_id,
                category_name=name,
                movement_count=v["count"],
                total_milliunits=v["total"],
                total_formatted=_ynab_format(v["total"], template),
                average_milliunits=v["total"] // v["count"] if v["count"] else 0,
            )
        )
    source_entries.sort(key=lambda p: abs(p.total_milliunits), reverse=True)
    top_source_categories = source_entries[:5]

    # Top-N destination categories (sorted by abs(total) descending)
    dest_entries: List[DestinationCategoryAggregate] = []
    for dest_id, v in dest_sums.items():
        name = category_name_lookup(dest_id) or "Unknown"
        dest_entries.append(
            DestinationCategoryAggregate(
                category_id=dest_id,
                category_name=name,
                movement_count=v["count"],
                total_milliunits=v["total"],
                total_formatted=_ynab_format(v["total"], template),
                average_milliunits=v["total"] // v["count"] if v["count"] else 0,
            )
        )
    dest_entries.sort(key=lambda p: abs(p.total_milliunits), reverse=True)
    top_destination_categories = dest_entries[:5]

    # Recurring pairs (count >= 2)
    recurring_pairs: List[RecurringMovementPair] = []
    for (from_id, to_id), v in pair_sums.items():
        if v["count"] < 2:
            continue
        from_name = (
            "Ready to Assign"
            if from_id is None
            else (category_name_lookup(from_id) or "Unknown")
        )
        to_name = category_name_lookup(to_id) or "Unknown"
        recurring_pairs.append(
            RecurringMovementPair(
                from_category_id=from_id,
                from_category_name=from_name,
                to_category_id=to_id,
                to_category_name=to_name,
                movement_count=v["count"],
                total_formatted=_ynab_format(v["total"], template),
            )
        )
    recurring_pairs.sort(key=lambda p: p.movement_count, reverse=True)

    # Proactive percentage
    proactive_pct: Optional[float] = (
        round(proactive_hits / total_count, 4) if total_count > 0 else None
    )

    # Planning health
    from_tba_ratio = from_tba_count / total_count if total_count > 0 else 0.0
    planning_health = _classify_planning_health(
        total_count, from_tba_ratio, len(recurring_pairs)
    )

    average_movement = total_moved_abs // total_count if total_count > 0 else 0

    return MoneyMovementInsightsResponse(
        period_start=period_start.isoformat(),
        period_end=period_end.isoformat(),
        monthly_buckets=[buckets[m.strftime("%Y-%m")] for m in months],
        total_movement_count=total_count,
        total_moved_formatted=_ynab_format(total_moved_abs, template),
        average_movement_formatted=_ynab_format(average_movement, template),
        from_ready_to_assign_count=from_tba_count,
        from_ready_to_assign_total_formatted=_ynab_format(from_tba_total, template),
        from_other_categories_count=from_other_count,
        from_other_categories_total_formatted=_ynab_format(from_other_total, template),
        top_source_categories=top_source_categories,
        top_destination_categories=top_destination_categories,
        recurring_pairs=recurring_pairs,
        movement_trend=trend,
        proactive_pct=proactive_pct,
        planning_health=planning_health,
        error=None,
    )


# ---------------------------------------------------------------------------
# Private helpers (used by build_money_movement_insights)
# ---------------------------------------------------------------------------


def _bucket_amount(
    movements: List[ynab.MoneyMovement],
    month_key: str,
    *,
    from_id: Optional[str] = None,
    from_id__not_none: bool = False,
) -> int:
    """Sum of ``amount`` values for one bucket, filtered by source.

    The two flags are mutually exclusive: pass ``from_id=None`` to sum
    only movements where ``from_category_id is None`` (TBA), or
    ``from_id__not_none=True`` to sum all non-TBA movements in the
    month. If neither flag is set, the sum is unfiltered.
    """
    total = 0
    for mv in movements:
        month_value = _movement_month(mv)
        if month_value is None or month_value.strftime("%Y-%m") != month_key:
            continue
        mv_from_id = (
            str(mv.from_category_id) if mv.from_category_id is not None else None
        )
        if from_id__not_none:
            if mv_from_id is None:
                continue
        elif from_id is None and not from_id__not_none:
            # Caller passed from_id=None explicitly → match TBA only
            if mv_from_id is not None:
                continue
        else:
            if mv_from_id != from_id:
                continue
        total += int(mv.amount or 0)
    return total
