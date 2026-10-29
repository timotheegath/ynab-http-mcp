"""
Planning insights tool for YNAB HTTP MCP.

Exposes the read-only ``get_plan_insights`` tool that reports plan state over
a multi-month window, wired to the planning-aggregate builder.

- Parameters are month-granular (``YYYY-MM`` or ``YYYY-MM-DD``, day ignored,
  until-month inclusive). Default window: last 3 calendar months plus any
  existing future plan months.
- Future months are discovered from ``get_all_plan_months`` and fetched via
  ``get_plan_month`` fan-out, never fabricated. When YNAB refuses a further
  future month, the walk stops and ``plan_horizon_reached`` is set.
- An in-process TTL cache keyed by the resolved window dedupes repeated
  reads (design D5).

Any invalid parameter or upstream YNAB failure produces a fully zeroed
response with ``error`` populated, so callers can pattern-match on
``response.error`` without handling partial data.

History: this was originally a ``data://months/insights`` resource. That URI
was shadowed by the ``data://months/{month_date}`` template in
``tools/planning.py`` — FastMCP matched the shorter template first and parsed
the literal ``insights`` as a month, so every read failed with
"Invalid month_date format: 'insights'". The tool form is the primary
interface; the resource is kept under a non-colliding URI for compatibility.
"""

from __future__ import annotations

import time
from typing import Annotated, Dict, Optional, Tuple

from mcp.types import ToolAnnotations

from ynab_http_mcp.ynab_service import YnabService, PlanMonthNotFoundError
from ynab_http_mcp.schemas.planning_aggregate import (
    PlanInsightsResponse,
    build_planning_insights_from_months,
    discover_forward_months,
    months_inclusive,
    resolve_month_window,
    zero_response,
)

#: Cache entry TTL, in seconds (design D5: short, session-scoped).
_TTL_SECONDS = 60.0

#: In-process cache keyed by the resolved ``(since_iso, until_iso)`` window.
_CACHE: Dict[Tuple[str, str], Tuple[float, str]] = {}


def _cache_get(key: Tuple[str, str]) -> Optional[str]:
    entry = _CACHE.get(key)
    if entry is None:
        return None
    timestamp, payload = entry
    if time.monotonic() - timestamp > _TTL_SECONDS:
        _CACHE.pop(key, None)
        return None
    return payload


def _cache_set(key: Tuple[str, str], payload: str) -> None:
    _CACHE[key] = (time.monotonic(), payload)


def _cache_clear() -> None:
    _CACHE.clear()


def _fan_out_and_assemble(
    ynab_service: YnabService, since, until
) -> PlanInsightsResponse:
    """Fan out ``get_plan_month`` over the window plus forward months.

    Forward months come from ``get_all_plan_months``; a ``get_plan_month``
    failure on a future month signals the horizon and stops the walk
    (flagging ``plan_horizon_reached``), whereas a failure on a window month
    propagates as an upstream failure.

    A month with no plan yet (``PlanMonthNotFoundError``) is not an upstream
    failure — YNAB simply has nothing for it. Whichever month it hits, the
    walk stops there and the horizon flag is set, so the aggregate reports
    the months that do exist instead of erroring out.
    """
    summaries = ynab_service.get_all_plan_months()
    summaries_data = getattr(summaries, "data", summaries)
    plan_months = getattr(summaries_data, "months", None) or []

    forward = discover_forward_months(plan_months, until)
    window = months_inclusive(since, until)
    window_set = set(window)

    month_details = []
    horizon = False
    window_fetched = 0
    for month in window + forward:
        try:
            response = ynab_service.get_plan_month(month.strftime("%Y-%m"))
        except PlanMonthNotFoundError:
            # No plan for this month yet — the plan does not extend this far.
            horizon = True
            break
        except Exception:
            if month in window_set:
                raise
            horizon = True
            break
        month_details.append(getattr(getattr(response, "data", response), "month"))
        if month in window_set:
            window_fetched += 1

    return build_planning_insights_from_months(
        month_details,
        plan_horizon_reached=horizon,
        window_month_count=window_fetched,
    )


def build_planning_insights(
    ynab_service: YnabService,
    since_date: Optional[str] = None,
    until_date: Optional[str] = None,
    now=None,
) -> PlanInsightsResponse:
    """Resolve the window, fan out months, and assemble the aggregate.

    Raises ``ValueError`` for unparseable month specifiers or an inverted
    window; upstream YNAB failures propagate to the caller.
    """
    since, until = resolve_month_window(since_date, until_date, now)
    if until < since:
        raise ValueError("until_date month must not be before since_date month")
    return _fan_out_and_assemble(ynab_service, since, until)


def _compute_insights_payload(
    since_date: Optional[str],
    until_date: Optional[str],
    ynab_service: YnabService,
) -> str:
    """Resolve the window, fan out months, and serialize the aggregate.

    Shared by the tool and the resource form so both return identical payloads
    (and share the same TTL cache). Any invalid parameter or upstream failure
    yields a fully zeroed response with ``error`` populated.
    """
    try:
        since, until = resolve_month_window(since_date, until_date)
    except ValueError as exc:
        return zero_response(f"Invalid date: {exc}").model_dump_json(exclude_none=True)

    if until < since:
        return zero_response(
            "until_date month must not be before since_date month"
        ).model_dump_json(exclude_none=True)

    key = (since.isoformat(), until.isoformat())
    cached = _cache_get(key)
    if cached is not None:
        return cached

    try:
        result = _fan_out_and_assemble(ynab_service, since, until)
    except Exception as exc:
        return zero_response(f"YNAB API failure: {exc}").model_dump_json(
            exclude_none=True
        )

    payload = result.model_dump_json(exclude_none=True)
    _cache_set(key, payload)
    return payload


def register(mcp, ynab_service: YnabService):

    @mcp.tool(annotations=ToolAnnotations(read_only_hint=True), output_schema=None)
    def get_plan_insights(
        since_date: Annotated[
            Optional[str],
            "Month YYYY-MM or YYYY-MM-DD (day ignored). Defaults to 2 months ago.",
        ] = None,
        until_date: Annotated[
            Optional[str],
            "Month YYYY-MM or YYYY-MM-DD (day ignored, inclusive). Defaults to current month.",
        ] = None,
    ) -> str:
        """Get pre-computed plan-state insights: month-level Ready-to-Assign,
        per-category budgeted/activity/balance series (milliunits + formatted),
        promoted goal blocks with a goal monthly rate, and derived arithmetic.
        Includes already-written future plan months; income is excluded."""
        return _compute_insights_payload(since_date, until_date, ynab_service)

    @mcp.resource(
        uri="data://plan-insights{?since_date,until_date}",
        mime_type="application/json",
        annotations={
            "title": "Read-only plan-state insights over a multi-month window.",
            "destructiveHint": False,
            "readOnlyHint": True,
            "idempotentHint": True,
        },
    )
    async def get_plan_insights_resource(
        since_date: Annotated[
            Optional[str],
            "Month YYYY-MM or YYYY-MM-DD (day ignored). Defaults to 2 months ago.",
        ] = None,
        until_date: Annotated[
            Optional[str],
            "Month YYYY-MM or YYYY-MM-DD (day ignored, inclusive). Defaults to current month.",
        ] = None,
    ) -> str:
        """Resource form of ``get_plan_insights``.

        Kept for callers that read resources directly. Prefer the
        ``get_plan_insights`` tool.
        """
        return _compute_insights_payload(since_date, until_date, ynab_service)
