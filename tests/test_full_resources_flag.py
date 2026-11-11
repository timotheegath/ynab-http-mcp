"""Tests for the removed ``/full`` drill-in resources.

The ``*Full`` schema siblings and the ``data://{entity}/{id}/full``
resources were removed; insights are exposed as tools instead. The
``SHOW_FULL_RESOURCES`` env flag no longer changes the advertised
catalog, so no ``/full`` template may ever be registered.
"""

from __future__ import annotations

import asyncio
import os

import pytest

# Ensure YNAB_API_KEY is set so YnabService can be constructed
os.environ.setdefault("YNAB_API_KEY", "00000000-0000-0000-0000-000000000000")


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


@pytest.mark.parametrize("value", [None, "false", "true", "1", "yes", "on"])
def test_full_resources_are_never_advertised(monkeypatch, value):
    """No ``/full`` template is registered for any flag spelling — the
    Full layer was removed; the lean templates are unaffected."""
    if value is None:
        monkeypatch.delenv("SHOW_FULL_RESOURCES", raising=False)
    else:
        monkeypatch.setenv("SHOW_FULL_RESOURCES", value)
    catalog = _fresh_catalog()

    assert not any("/full" in uri for uri in catalog["template_uris"])
    assert not any("full" in name for name in catalog["tool_names"])
    assert LEAN_TEMPLATE_URIS <= catalog["template_uris"]
