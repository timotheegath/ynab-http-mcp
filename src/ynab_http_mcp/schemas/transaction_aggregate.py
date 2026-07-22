"""
Transaction aggregate schemas for YNAB HTTP MCP.

This module defines the ``TransactionInsightsResponse`` model and its
supporting types. The aggregate is a pre-computed view of the
transactions collection over a configurable time window:

- monthly buckets (zero-filled across the requested window)
- inflow / outflow / net totals (YNAB-formatted currency strings)
- top-5 payees and top-5 categories by absolute amount
- cleared / uncleared / reconciled breakdown
- ``spending_trend`` — a directional label (``"increasing"``,
  ``"decreasing"``, ``"stable"``) computed by linear regression over
  the monthly outflow series.

Per the Lean / Full / Aggregate convention, this is the Aggregate
layer. It is exposed at ``data://transactions/insights`` and never
embedded in lean resources.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field

import ynab


# Spending trend: a directional label computed from the monthly outflow
# series. The classification threshold is documented in
# ``_classify_trend``.
SpendingTrend = Literal["increasing", "decreasing", "stable"]


# ---------------------------------------------------------------------------
# Currency formatting
# ---------------------------------------------------------------------------
#
# YNAB-formatted currency strings use the YNAB plan's locale. The SDK
# already returns ``amount_formatted`` on each transaction; we can derive
# inflow / outflow / net formatted strings by reusing the most-common
# currency format observed in the window, falling back to ``"$0.00"``
# when the window is empty.


def _extract_number(s: str) -> str:
    """Return the numeric portion of a YNAB-formatted string.

    YNAB formatted strings look like ``"-$45.00"`` or ``"$1,234.56"``.
    The numeric portion is the longest run of contiguous ``[0-9.,-]``
    characters; the leading sign and any currency symbol are skipped.
    """
    longest = ""
    cur_start: Optional[int] = None
    for i, ch in enumerate(s):
        if ch.isdigit() or ch in ".,-":
            if cur_start is None:
                cur_start = i
        else:
            # End of a run; check whether it's the longest so far
            if cur_start is not None:
                run = s[cur_start:i]
                if len(run) > len(longest):
                    longest = run
                cur_start = None
    # Tail run
    if cur_start is not None:
        run = s[cur_start:]
        if len(run) > len(longest):
            longest = run
    return longest


def _ynab_format(value_milli: int, template: Optional[str] = None) -> str:
    """Format ``value_milli`` (integer milliunits) as a YNAB currency string.

    YNAB's SDK encodes negative currency by prepending a literal ``-`` to
    the formatted string (e.g. ``"-$45.00"`` for -$45.00). The same template
    used for a positive value (e.g. ``"$45.00"``) omits the sign.

    We split the template into [sign] [prefix] [number] [suffix]. The sign
    is the first ``-`` character in the prefix; we replace it with the
    sign derived from ``value_milli`` (no sign for zero or positive,
    ``-`` for negative). The number and suffix structure is preserved.
    """
    if template is None:
        template = "$0.00"
    num = _extract_number(template)
    if not num:
        return template
    template_prefix = template[: template.index(num)] if num in template else ""
    template_suffix = (
        template[template.index(num) + len(num) :] if num in template else ""
    )
    abs_milli = abs(value_milli)
    whole = abs_milli // 1000
    cents = abs_milli % 1000
    whole_str = str(whole)
    whole_with_sep = ""
    for i, ch in enumerate(reversed(whole_str)):
        if i > 0 and i % 3 == 0:
            whole_with_sep = "," + whole_with_sep
        whole_with_sep = ch + whole_with_sep
    cents_str = f"{cents:03d}"[:2]
    sign = "-" if value_milli < 0 else ""
    # Strip a leading "-" from the template's prefix (we set the sign
    # ourselves from the value) and place it as the sign character.
    if template_prefix.startswith("-"):
        template_prefix = template_prefix[1:]
    return f"{sign}{template_prefix}{whole_with_sep}.{cents_str}{template_suffix}"


# ---------------------------------------------------------------------------
# Supporting models
# ---------------------------------------------------------------------------


class MonthlyTransactionBucket(BaseModel):
    """One calendar month's worth of transaction aggregates.

    The list of ``MonthlyTransactionBucket`` is zero-filled — every month
    in the requested window has an entry, even months with no
    transactions (with ``transaction_count == 0`` and zero formatted
    amounts).
    """

    month: str = Field(..., description="Month in YYYY-MM format")
    transaction_count: int = Field(
        ..., description="Number of transactions in the month"
    )
    inflow_formatted: str = Field(
        ..., description="Inflow formatted in the plan's currency"
    )
    outflow_formatted: str = Field(
        ..., description="Outflow formatted in the plan's currency (negative)"
    )
    net_formatted: str = Field(
        ..., description="Inflow + outflow formatted in the plan's currency"
    )
    average_transaction_formatted: str = Field(
        ...,
        description="Outflow / outflow_transaction_count, formatted; '$0.00' if no outflow",
    )


class PayeeAggregate(BaseModel):
    """Top-N aggregate row for a single payee."""

    payee_id: Optional[str] = Field(
        None, description="Payee UUID; None for unassigned transactions"
    )
    payee_name: str = Field(..., description="Payee name; 'Unassigned' for None IDs")
    transaction_count: int = Field(
        ..., description="Number of transactions for this payee"
    )
    total_milliunits: int = Field(
        ...,
        description=(
            "Sum of transaction amounts in milliunits (negative for outflow "
            "payees). Used as the sort key for top_payees."
        ),
    )
    total_formatted: str = Field(
        ..., description="Same value formatted in the plan's currency"
    )


class CategoryAggregate(BaseModel):
    """Top-N aggregate row for a single category."""

    category_id: Optional[str] = Field(
        None, description="Category UUID; None for uncategorized transactions"
    )
    category_name: str = Field(
        ..., description="Category name; 'Uncategorized' for None IDs"
    )
    transaction_count: int = Field(
        ..., description="Number of transactions for this category"
    )
    total_milliunits: int = Field(
        ...,
        description=(
            "Sum of transaction amounts in milliunits; used as the sort key "
            "for top_categories."
        ),
    )
    total_formatted: str = Field(
        ..., description="Same value formatted in the plan's currency"
    )


class ClearedBreakdown(BaseModel):
    """Transaction counts by cleared status."""

    cleared: int = Field(..., description="Number of cleared transactions")
    uncleared: int = Field(..., description="Number of uncleared transactions")
    reconciled: int = Field(..., description="Number of reconciled transactions")


class TransactionInsightsResponse(BaseModel):
    """Pre-computed insights over a window of transactions.

    See the ``transaction-aggregate-resource`` capability spec for the
    full contract.
    """

    period_start: str = Field(
        ..., description="ISO date of the first day of the analysis window"
    )
    period_end: str = Field(
        ..., description="ISO date of the day after the last day of the analysis window"
    )
    monthly_buckets: List[MonthlyTransactionBucket] = Field(
        ..., description="One bucket per calendar month in the window (zero-filled)"
    )
    total_inflow_formatted: str = Field(
        ..., description="Sum of positive amounts over the window, YNAB-formatted"
    )
    total_outflow_formatted: str = Field(
        ..., description="Sum of negative amounts over the window, YNAB-formatted"
    )
    net_formatted: str = Field(..., description="inflow + outflow, YNAB-formatted")
    average_monthly_spending_formatted: str = Field(
        ..., description="total_outflow / months_in_window, YNAB-formatted"
    )
    average_transaction_formatted: str = Field(
        ...,
        description="total_outflow / outflow_transaction_count, YNAB-formatted",
    )
    spending_trend: SpendingTrend = Field(
        ..., description="Directional read of outflow over monthly_buckets"
    )
    top_payees: List[PayeeAggregate] = Field(
        ..., description="Top 5 payees by absolute total_milliunits, descending"
    )
    top_categories: List[CategoryAggregate] = Field(
        ..., description="Top 5 categories by absolute total_milliunits, descending"
    )
    by_cleared_status: ClearedBreakdown = Field(
        ..., description="Transaction counts by cleared status"
    )
    transaction_count: int = Field(
        ..., description="Total number of transactions in the window"
    )
    error: Optional[str] = Field(None, description="Populated when computation fails")


# ---------------------------------------------------------------------------
# Helpers: window / trend / aggregate computation
# ---------------------------------------------------------------------------


def _default_window(now: Optional[date] = None) -> tuple[date, date]:
    """Return ``(since_date, until_date)`` for the last 3 calendar months.

    ``since_date`` is the first day of (current month − 2 months).
    ``until_date`` is the first day of the month after the current month.
    """
    today = now or date.today()
    first_of_this_month = today.replace(day=1)
    # Compute first_of_month_minus_2 by walking back
    year = first_of_this_month.year
    month = first_of_this_month.month - 2
    while month <= 0:
        month += 12
        year -= 1
    since = date(year, month, 1)
    # First day of next month
    nm_year = first_of_this_month.year
    nm_month = first_of_this_month.month + 1
    if nm_month > 12:
        nm_month = 1
        nm_year += 1
    until = date(nm_year, nm_month, 1)
    return since, until


def _months_in_window(since: date, until: date) -> List[date]:
    """Return the first day of every month in ``[since, until)``."""
    out: List[date] = []
    y, m = since.year, since.month
    while True:
        cur = date(y, m, 1)
        if cur >= until:
            break
        out.append(cur)
        m += 1
        if m > 12:
            m = 1
            y += 1
    return out


def _classify_trend(outflows_by_month: List[int]) -> SpendingTrend:
    """Compute a directional label for the monthly outflow series.

    Uses a simple least-squares linear regression slope. Classifies
    ``"stable"`` when the absolute change is below 5 % of the mean
    outflow, ``"increasing"`` when the slope is positive, and
    ``"decreasing"`` when negative.
    """
    if len(outflows_by_month) < 2:
        return "stable"
    n = len(outflows_by_month)
    # Use absolute values for the trend (outflows are negative)
    abs_series = [abs(v) for v in outflows_by_month]
    mean = sum(abs_series) / n
    # Linear regression slope: x is the month index 0..n-1
    x_mean = (n - 1) / 2
    num = sum((i - x_mean) * (abs_series[i] - mean) for i in range(n))
    den = sum((i - x_mean) ** 2 for i in range(n))
    if den == 0:
        return "stable"
    slope = num / den
    # Threshold: 5% of mean (or 0 if mean is 0)
    threshold = abs(mean) * 0.05
    if abs(slope) <= threshold:
        return "stable"
    return "increasing" if slope > 0 else "decreasing"


# ---------------------------------------------------------------------------
# Top-level builder
# ---------------------------------------------------------------------------


def _make_zero_buckets(since: date, until: date) -> Dict[str, MonthlyTransactionBucket]:
    """Return a mapping of ``YYYY-MM`` → zero-filled bucket for every month
    in the ``[since, until)`` window."""
    out: Dict[str, MonthlyTransactionBucket] = {}
    for month_start in _months_in_window(since, until):
        key = month_start.strftime("%Y-%m")
        out[key] = MonthlyTransactionBucket(
            month=key,
            transaction_count=0,
            inflow_formatted="$0.00",
            outflow_formatted="$0.00",
            net_formatted="$0.00",
            average_transaction_formatted="$0.00",
        )
    return out


def _is_unassigned_payee(payee_id: Optional[str], payee_name: Optional[str]) -> bool:
    """Return True for transactions with no payee assigned."""
    return payee_id is None and (payee_name is None or payee_name == "")


def _is_uncategorized(category_id: Optional[str]) -> bool:
    return category_id is None


def build_transaction_insights(
    transactions: List[ynab.TransactionDetail],
    period_start: date,
    period_end: date,
) -> TransactionInsightsResponse:
    """Compute a ``TransactionInsightsResponse`` from a list of transactions.

    The window is the half-open interval ``[period_start, period_end)``.
    The result is zero-filled across every calendar month in the
    window.
    """
    if period_end <= period_start:
        return TransactionInsightsResponse(
            period_start=period_start.isoformat(),
            period_end=period_end.isoformat(),
            monthly_buckets=[],
            total_inflow_formatted="$0.00",
            total_outflow_formatted="$0.00",
            net_formatted="$0.00",
            average_monthly_spending_formatted="$0.00",
            average_transaction_formatted="$0.00",
            spending_trend="stable",
            top_payees=[],
            top_categories=[],
            by_cleared_status=ClearedBreakdown(cleared=0, uncleared=0, reconciled=0),
            transaction_count=0,
            error="period_end must be strictly after period_start",
        )

    months = _months_in_window(period_start, period_end)
    months_in_window = len(months)
    # Pick a currency template from the first transaction that has one.
    template: Optional[str] = None
    for txn in transactions:
        if getattr(txn, "amount_formatted", None):
            template = txn.amount_formatted
            break

    buckets = _make_zero_buckets(period_start, period_end)

    # Aggregate accumulators
    total_inflow = 0
    total_outflow = 0
    outflow_count = 0
    cleared_count = 0
    uncleared_count = 0
    reconciled_count = 0
    payee_sums: Dict[Optional[str], Dict[str, Any]] = {}
    category_sums: Dict[Optional[str], Dict[str, Any]] = {}

    for txn in transactions:
        amount = int(txn.amount or 0)
        txn_date = txn.var_date
        if isinstance(txn_date, datetime):
            txn_date = txn_date.date()
        if not isinstance(txn_date, date):
            continue
        # Window filter
        if txn_date < period_start or txn_date >= period_end:
            continue
        key = txn_date.strftime("%Y-%m")
        bucket = buckets.setdefault(
            key,
            MonthlyTransactionBucket(
                month=key,
                transaction_count=0,
                inflow_formatted="$0.00",
                outflow_formatted="$0.00",
                net_formatted="$0.00",
                average_transaction_formatted="$0.00",
            ),
        )
        bucket.transaction_count += 1
        if amount >= 0:
            total_inflow += amount
        else:
            total_outflow += amount
            outflow_count += 1

        # Cleared status (the SDK exposes an enum; compare on .value)
        cleared_val = (
            txn.cleared.value if hasattr(txn.cleared, "value") else str(txn.cleared)
        )
        if cleared_val == "cleared":
            cleared_count += 1
        elif cleared_val == "uncleared":
            uncleared_count += 1
        elif cleared_val == "reconciled":
            reconciled_count += 1

        # Payee aggregation (Unassigned sentinel for None)
        payee_id = str(txn.payee_id) if txn.payee_id is not None else None
        if _is_unassigned_payee(payee_id, txn.payee_name):
            payee_id = None
            payee_name = "Unassigned"
        else:
            payee_name = txn.payee_name or "Unassigned"
        pe = payee_sums.setdefault(
            payee_id,
            {"name": payee_name, "count": 0, "total": 0},
        )
        pe["count"] += 1
        pe["total"] += amount

        # Category aggregation
        category_id = str(txn.category_id) if txn.category_id is not None else None
        if _is_uncategorized(category_id):
            category_id = None
            category_name = "Uncategorized"
        else:
            category_name = txn.category_name or "Uncategorized"
        ce = category_sums.setdefault(
            category_id,
            {"name": category_name, "count": 0, "total": 0},
        )
        ce["count"] += 1
        ce["total"] += amount

    # Finalize buckets: format amounts, compute per-bucket inflow / outflow / net
    outflows_by_month: List[int] = []
    for month_start in months:
        key = month_start.strftime("%Y-%m")
        bucket = buckets[key]
        # Recompute per-bucket inflow / outflow from the (already-filtered)
        # transactions, since the zero-filled buckets are missing values.
        bucket_inflow = 0
        bucket_outflow = 0
        bucket_outflow_count = 0
        for txn in transactions:
            amount = int(txn.amount or 0)
            txn_date = txn.var_date
            if isinstance(txn_date, datetime):
                txn_date = txn_date.date()
            if not isinstance(txn_date, date):
                continue
            if txn_date.strftime("%Y-%m") != key:
                continue
            if amount >= 0:
                bucket_inflow += amount
            else:
                bucket_outflow += amount
                bucket_outflow_count += 1
        outflows_by_month.append(bucket_outflow)
        bucket.inflow_formatted = _ynab_format(bucket_inflow, template)
        bucket.outflow_formatted = _ynab_format(bucket_outflow, template)
        bucket.net_formatted = _ynab_format(bucket_inflow + bucket_outflow, template)
        if bucket_outflow_count > 0:
            avg_outflow = bucket_outflow // bucket_outflow_count
        else:
            avg_outflow = 0
        bucket.average_transaction_formatted = _ynab_format(avg_outflow, template)

    # Top-5 payees (sorted by abs(total) descending)
    top_payees = sorted(
        (
            PayeeAggregate(
                payee_id=k,
                payee_name=v["name"],
                transaction_count=v["count"],
                total_milliunits=v["total"],
                total_formatted=_ynab_format(v["total"], template),
            )
            for k, v in payee_sums.items()
        ),
        key=lambda p: abs(p.total_milliunits),
        reverse=True,
    )[:5]

    # Top-5 categories
    top_categories = sorted(
        (
            CategoryAggregate(
                category_id=k,
                category_name=v["name"],
                transaction_count=v["count"],
                total_milliunits=v["total"],
                total_formatted=_ynab_format(v["total"], template),
            )
            for k, v in category_sums.items()
        ),
        key=lambda p: abs(p.total_milliunits),
        reverse=True,
    )[:5]

    # Spending trend from outflows
    trend = _classify_trend(outflows_by_month)
    months_in_window_n = max(months_in_window, 1)
    avg_monthly = total_outflow // months_in_window_n
    avg_txn = (total_outflow // outflow_count) if outflow_count > 0 else 0

    return TransactionInsightsResponse(
        period_start=period_start.isoformat(),
        period_end=period_end.isoformat(),
        monthly_buckets=[buckets[m.strftime("%Y-%m")] for m in months],
        total_inflow_formatted=_ynab_format(total_inflow, template),
        total_outflow_formatted=_ynab_format(total_outflow, template),
        net_formatted=_ynab_format(total_inflow + total_outflow, template),
        average_monthly_spending_formatted=_ynab_format(avg_monthly, template),
        average_transaction_formatted=_ynab_format(avg_txn, template),
        spending_trend=trend,
        top_payees=top_payees,
        top_categories=top_categories,
        by_cleared_status=ClearedBreakdown(
            cleared=cleared_count,
            uncleared=uncleared_count,
            reconciled=reconciled_count,
        ),
        transaction_count=len(transactions),
        error=None,
    )


# Classmethod-style factory for symmetry with the spec
TransactionInsightsResponse.from_transactions = classmethod(  # type: ignore[attr-defined]
    lambda cls, transactions, period_start, period_end: build_transaction_insights(
        transactions, period_start, period_end
    )
)
