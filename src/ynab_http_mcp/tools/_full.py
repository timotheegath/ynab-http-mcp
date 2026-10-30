"""Conditional registration for the verbose ``/full`` drill-in resources."""

from collections.abc import Callable
from typing import Any, TypeVar

from ynab_http_mcp.config import full_resources_enabled

F = TypeVar("F", bound=Callable[..., Any])


def full_resource(mcp: Any, uri: str, **kwargs: Any) -> Callable[[F], F]:
    """Register a ``/full`` resource only when full resources are enabled.

    When disabled the decorated function is returned untouched, so the
    resource never reaches the MCP catalog (neither as a resource nor as a
    ``ResourcesAsTools`` tool).
    """

    def decorator(fn: F) -> F:
        if full_resources_enabled():
            mcp.resource(uri=uri, **kwargs)(fn)
        return fn

    return decorator
