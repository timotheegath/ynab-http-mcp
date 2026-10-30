"""Tests for the ``SHOW_FULL_RESOURCES`` env flag gating ``/full`` resources.

The verbose ``/full`` drill-in resources are hidden by default so the
agent-facing MCP catalog stays lean, and are only registered when the flag is
explicitly enabled.
"""

from __future__ import annotations

import asyncio
import os

import pytest

# Ensure YNAB_API_KEY is set so YnabService can be constructed
os.environ.setdefault("YNAB_API_KEY", "00000000-0000-0000-0000-000000000000")


FULL_TEMPLATE_URIS = {
    "data://accounts/{account_id}/full",
    "data://categories/{category_id}/full",
    "data://months/{month_date}/full",
    "data://months/{month_date}/categories/{category_id}/full",
    "data://payees/{id}/full",
    "data://transactions/{id}/full",
}

LEAN_TEMPLATE_URIS = {
    "data://transactions/{id}",
    "data://transactions{?since_date,until_date,type,limit}",
}


async def _build_catalog():
    """Build a FRESH server and fetch the catalog for the current env."""
    from fastmcp import FastMCP
    from fastmcp.client import Client
    from fastmcp.server.transforms import ResourcesAsTools
    from ynab_http_mcp.ynab_service import YnabService

    mcp = FastMCP("ynab")
    ynab_service = YnabService()

    import ynab_http_mcp.tools.categories as category_tools
    import ynab_http_mcp.tools.planning as planning_tools
    import ynab_http_mcp.tools.transactions as transaction_tools
    import ynab_http_mcp.tools.accounts as account_tools
    import ynab_http_mcp.tools.payees as payee_tools
    import ynab_http_mcp.tools.budget_management as budget_tools
    import ynab_http_mcp.tools.money_movements as money_movement_tools

    category_tools.register(mcp, ynab_service)
    planning_tools.register(mcp, ynab_service)
    transaction_tools.register(mcp, ynab_service)
    account_tools.register(mcp, ynab_service)
    payee_tools.register(mcp, ynab_service)
    budget_tools.register(mcp, ynab_service)
    money_movement_tools.register(mcp, ynab_service)
    mcp.add_transform(ResourcesAsTools(mcp))

    async with Client(mcp) as client:
        tools_raw = await client.list_tools()
        await client.list_resources()
        templates_raw = await client.list_resource_templates()

    return {
        "tool_names": {t.name for t in tools_raw},
        "template_uris": {
            t.model_dump(mode="json", by_alias=True)["uriTemplate"]
            for t in templates_raw
        },
    }


def _fresh_catalog() -> dict:
    """Build a fresh catalog (fresh FastMCP instance) for the current env."""
    return asyncio.run(_build_catalog())


def test_flag_unset_hides_full_resources(monkeypatch):
    """With the flag unset, no ``/full`` resources are advertised."""
    monkeypatch.delenv("SHOW_FULL_RESOURCES", raising=False)
    catalog = _fresh_catalog()

    assert catalog["template_uris"] & FULL_TEMPLATE_URIS == set()
    assert LEAN_TEMPLATE_URIS <= catalog["template_uris"]
    assert not any("full" in name for name in catalog["tool_names"])


def test_flag_false_hides_full_resources(monkeypatch):
    """``SHOW_FULL_RESOURCES=false`` behaves like the flag being unset."""
    monkeypatch.setenv("SHOW_FULL_RESOURCES", "false")
    catalog = _fresh_catalog()

    assert catalog["template_uris"] & FULL_TEMPLATE_URIS == set()


def test_flag_true_shows_full_resources(monkeypatch):
    """``SHOW_FULL_RESOURCES=true`` registers exactly the six ``/full`` URIs."""
    monkeypatch.setenv("SHOW_FULL_RESOURCES", "true")
    catalog = _fresh_catalog()

    assert catalog["template_uris"] & FULL_TEMPLATE_URIS == FULL_TEMPLATE_URIS


def test_flag_true_keeps_lean_resources(monkeypatch):
    """Enabling full resources must not remove any lean templates."""
    monkeypatch.setenv("SHOW_FULL_RESOURCES", "true")
    catalog = _fresh_catalog()

    assert LEAN_TEMPLATE_URIS <= catalog["template_uris"]


@pytest.mark.parametrize("value", ["1", "yes", "on"])
def test_truthy_values_enable_full_resources(monkeypatch, value):
    """Common truthy spellings are treated as enabled."""
    monkeypatch.setenv("SHOW_FULL_RESOURCES", value)
    catalog = _fresh_catalog()

    assert catalog["template_uris"] & FULL_TEMPLATE_URIS == FULL_TEMPLATE_URIS
