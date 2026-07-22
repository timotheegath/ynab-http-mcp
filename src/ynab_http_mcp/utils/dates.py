from datetime import datetime


def parse_timestamp(ts: str) -> datetime:
    """Parse a full ISO-8601 timestamp string (e.g. '2026-07-15 08:19:21+00:00')."""
    return datetime.fromisoformat(ts)


def parse_month_date(value: datetime | str) -> datetime:
    """
    Parse and normalise a month specifier into a datetime.

    Accepts:
    - A ``datetime`` object (returned unchanged)
    - ``'YYYY-MM'`` — year/month only, day is set to 1
    - ``'YYYY-MM-DD'`` — full ISO date string

    Returns:
        A ``datetime`` whose day component is the *original* day in the
        string (use ``.replace(day=1)`` yourself if you need month-start).

    Raises:
        ValueError: if the input is not one of the accepted types / formats.
    """
    if isinstance(value, datetime):
        return value
    if not isinstance(value, str):
        raise ValueError(
            "month_date must be a datetime object or an ISO format string "
            "('YYYY-MM' or 'YYYY-MM-DD')"
        )
    try:
        # Handle short 'YYYY-MM' format by appending a day
        if len(value) == 7 and value[4] == "-":
            return datetime.fromisoformat(value + "-01")
        return datetime.fromisoformat(value)
    except ValueError as exc:
        raise ValueError(
            f"Invalid month_date format: '{value}'. Expected 'YYYY-MM' or 'YYYY-MM-DD'."
        ) from exc


def parse_date(value: datetime | str) -> datetime:
    """
    Parse a date/datetime value into a ``datetime``.

    Accepts a ``datetime`` (returned unchanged) or any ISO-format date
    string recognised by ``datetime.fromisoformat``.

    Raises:
        ValueError: if the input is not a datetime or a valid ISO string.
    """
    if isinstance(value, datetime):
        return value
    if not isinstance(value, str):
        raise ValueError("date must be a datetime object or an ISO format string")
    try:
        return datetime.fromisoformat(value)
    except ValueError as exc:
        raise ValueError(f"Invalid date format: '{value}'.") from exc


def month_str(dt: datetime) -> str:
    """Return the first-of-month string (YYYY-MM-01) expected by the YNAB API."""
    return dt.replace(day=1).strftime("%Y-%m-%d")
