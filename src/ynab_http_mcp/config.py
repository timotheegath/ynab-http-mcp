"""Runtime configuration read from the environment."""

import os

_TRUE_VALUES = {"1", "true", "yes", "on"}


def full_resources_enabled() -> bool:
    """Return True when the verbose ``/full`` drill-in resources are exposed.

    Controlled by the ``SHOW_FULL_RESOURCES`` env flag. Defaults to False so
    the MCP catalog stays lean; the flag is read on every call so it can be
    toggled between registrations (e.g. in tests).
    """
    raw = os.getenv("SHOW_FULL_RESOURCES", "").strip().lower()
    return raw in _TRUE_VALUES
