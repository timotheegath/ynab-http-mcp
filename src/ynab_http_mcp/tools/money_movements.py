"""
Money movement insight tools for YNAB HTTP MCP.

Exposes two read-only tools that compute planning-quality insights over
a window of money movements:

- ``get_money_movement_insights(since_date, until_date)`` — window view
  (default: last 3 calendar months).
- ``get_money_movement_insights_for_month(month_date)`` — single month
  drill-in.

Both tools return a ``MoneyMovementInsightsResponse`` Pydantic model.
Any ``ValueError`` or SDK failure produces a fully zeroed response with
``error`` populated so the caller can pattern-match on
``response.error`` without dealing with partial data.
"""

from __future__ import annotations

from datetime import date
from typing import Annotated, Callable, Dict, List, Optional

from mcp.types import ToolAnnotations

from ynab_http_mcp.ynab_service import YnabService
from ynab_http_mcp.schemas.money_movement_aggregate import (
    MoneyMovementInsightsResponse,
    build_money_movement_insights,
)
from ynab_http_mcp.schemas.transaction_aggregate import _default_window
from ynab_http_mcp.utils.dates import parse_date, parse_month_date


def _empty_response(
    period_start: str = "",
    period_end: str = "",
    buckets: Optional[List] = None,
    error: str = "",
) -> MoneyMovementInsightsResponse:
    """Build a fully zeroed ``MoneyMovementInsightsResponse`` with
    ``error`` populated. ``buckets`` defaults to ``[]``."""
    return MoneyMovementInsightsResponse(
        period_start=period_start,
        period_end=period_end,
        monthly_buckets=buckets if buckets is not None else [],
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
        error=error or None,
    )


def _zero_buckets(since: date, until: date) -> List:
    """One zero-filled bucket per month in ``[since, until)``."""
    from ynab_http_mcp.schemas.money_movement_aggregate import (
        MonthlyMoneyMovementBucket,
    )

    out: List[MonthlyMoneyMovementBucket] = []
    y, m = since.year, since.month
    while True:
        cur = date(y, m, 1)
        if cur >= until:
            break
        key = cur.strftime("%Y-%m")
        out.append(
            MonthlyMoneyMovementBucket(
                month=key,
                movement_count=0,
                from_tba_count=0,
                from_other_count=0,
                from_tba_total_formatted="$0.00",
                from_other_total_formatted="$0.00",
                average_moved_day_of_month=None,
            )
        )
        m += 1
        if m > 12:
            m = 1
            y += 1
    return out


def _build_category_lookup(ynab_service: YnabService) -> Callable[[Optional[str]], str]:
    """Return a callable that maps a category_id to its name.

    Calls ``ynab_service.get_categories()`` once per call. Falls back to
    ``"Unknown"`` for any unresolved id (and ``"Ready to Assign"`` for
    the sentinel ``None`` id) when the categories call fails or the id
    is not present.
    """
    try:
        raw = ynab_service.get_categories()
    except Exception:
        # Categories endpoint failure — soft fallback per design.md.
        lookup: Dict[str, str] = {}
    else:
        lookup = {}
        for group in raw.data.category_groups or []:
            for cat in group.categories or []:
                if cat is not None and cat.id is not None:
                    lookup[str(cat.id)] = cat.name or "Unknown"

    def resolver(cid: Optional[str]) -> str:
        if cid is None:
            return "Ready to Assign"
        return lookup.get(cid, "Unknown")

    return resolver


def register(mcp, ynab_service: YnabService):

    @mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
    def get_money_movement_insights(
        since_date: Annotated[
            Optional[str],
            "ISO date YYYY-MM-DD. Defaults to first day of (current month - 2 months).",
        ] = None,
        until_date: Annotated[
            Optional[str],
            "ISO date YYYY-MM-DD (exclusive). Defaults to first day of month after current.",
        ] = None,
    ) -> MoneyMovementInsightsResponse:
        """Get pre-computed money-movement insights over a window:
        monthly buckets, TBA vs other-category split, top-5 source /
        destination categories, recurring pairs, monthly trend,
        proactive_pct, and a planning_health summary. Default window is
        the last 3 calendar months."""
        try:
            if since_date is None and until_date is None:
                since, until = _default_window()
            else:
                if since_date is None:
                    since, _ = _default_window()
                else:
                    since = parse_date(since_date).date()
                if until_date is None:
                    _, until = _default_window()
                else:
                    until = parse_date(until_date).date()
        except ValueError as exc:
            return _empty_response(error=f"Invalid date: {exc}")

        if until <= since:
            return _empty_response(
                period_start=since.isoformat(),
                period_end=until.isoformat(),
                error="period_end must be strictly after period_start",
            )

        category_name_lookup = _build_category_lookup(ynab_service)

        try:
            movements = ynab_service.get_money_movements(
                since_date=since.isoformat(),
                until_date=until.isoformat(),
            )
        except ValueError as exc:
            return _empty_response(
                period_start=since.isoformat(),
                period_end=until.isoformat(),
                buckets=_zero_buckets(since, until),
                error=f"Invalid parameter: {exc}",
            )
        except Exception as exc:
            return _empty_response(
                period_start=since.isoformat(),
                period_end=until.isoformat(),
                buckets=_zero_buckets(since, until),
                error=f"YNAB API failure: {exc}",
            )

        try:
            return build_money_movement_insights(
                movements, since, until, category_name_lookup
            )
        except Exception as exc:
            return _empty_response(
                period_start=since.isoformat(),
                period_end=until.isoformat(),
                buckets=_zero_buckets(since, until),
                error=f"Aggregate computation failed: {exc}",
            )

    @mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
    def get_money_movement_insights_for_month(
        month_date: Annotated[
            str,
            "Month YYYY-MM or full ISO date YYYY-MM-DD. Day is ignored.",
        ],
    ) -> MoneyMovementInsightsResponse:
        """Get pre-computed money-movement insights for a single month.
        One SDK call per request. Use to drill in from a window
        response."""
        try:
            parsed = parse_month_date(month_date)
        except ValueError as exc:
            return _empty_response(error=f"Invalid month_date: {exc}")

        since = parsed.date().replace(day=1)
        # First day of next month
        nm_year = since.year
        nm_month = since.month + 1
        if nm_month > 12:
            nm_month = 1
            nm_year += 1
        until = date(nm_year, nm_month, 1)

        category_name_lookup = _build_category_lookup(ynab_service)

        try:
            movements = ynab_service.get_money_movements(
                since_date=since.isoformat(),
                until_date=until.isoformat(),
            )
        except ValueError as exc:
            return _empty_response(
                period_start=since.isoformat(),
                period_end=until.isoformat(),
                buckets=_zero_buckets(since, until),
                error=f"Invalid parameter: {exc}",
            )
        except Exception as exc:
            return _empty_response(
                period_start=since.isoformat(),
                period_end=until.isoformat(),
                buckets=_zero_buckets(since, until),
                error=f"YNAB API failure: {exc}",
            )

        try:
            return build_money_movement_insights(
                movements, since, until, category_name_lookup
            )
        except Exception as exc:
            return _empty_response(
                period_start=since.isoformat(),
                period_end=until.isoformat(),
                buckets=_zero_buckets(since, until),
                error=f"Aggregate computation failed: {exc}",
            )
