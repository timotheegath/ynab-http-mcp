"""Tests for MCP tool registration and the catalog / serialization contract.

Every assertion in this module is a real ``assert``. These tests guard the
registration contract, so a broken registration has to fail loudly instead of
returning ``False`` — which pytest 9 would happily count as a pass.
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from unittest.mock import MagicMock
from uuid import UUID

import ynab
from fastmcp import FastMCP
from fastmcp.client import Client
from pydantic import BaseModel

from ynab_http_mcp.schemas import MCPCategories
from ynab_http_mcp.tools.categories import register as register_categories
from ynab_http_mcp.tools.planning import register as register_planning
from ynab_http_mcp.tools.transactions import register as register_transactions
from ynab_http_mcp.ynab_service import YnabService

# Paths are derived from this file, never hardcoded to one developer's
# machine. The old absolute ``/home/timo/...`` paths raised FileNotFoundError
# for everyone else, and the surrounding try/except swallowed it.
REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
TOOLS_DIR = SRC_ROOT / "ynab_http_mcp" / "tools"

# The legacy validation helper that was replaced by the Pydantic MCP* schema
# layer. It must not creep back into the tool modules.
REMOVED_VALIDATION_HELPER = "validate_and_clean_data"

# SDK bookkeeping fields that must never reach the wire format.
IMPORT_FIELDS = (
    "import_id",
    "import_payee_name",
    "import_payee_name_original",
    "import_account_name",
)

TEST_PLAN_ID = UUID("12345678-1234-5678-1234-567812345678")

# The registration contract: every resource URI each tool module advertises.
EXPECTED_REGISTRATION = {
    "transactions": {
        "resources": set(),
        "templates": {
            "data://accounts/{account_id}/transactions{?since_date,until_date,type}",
            "data://categories/{category_id}/transactions{?since_date,until_date,type}",
            "data://months/{month_date}/transactions{?type}",
            "data://payees/{payee_id}/transactions{?since_date,until_date,type}",
            "data://transactions/insights{?since_date,until_date,account_id}",
            "data://transactions/{id}",
            "data://transactions{?since_date,until_date,type,limit}",
        },
    },
    "categories": {
        "resources": {"data://categories"},
        "templates": {"data://categories/{category_id}"},
    },
    "planning": {
        "resources": {"data://months"},
        "templates": {
            "data://months/{month_date}",
            "data://months/{month_date}/categories/{category_id}",
        },
    },
}

# The public schema surface promised by ``ynab_http_mcp.schemas``.
EXPECTED_SCHEMA_NAMES = (
    "MCPTransaction",
    "MCPTransactions",
    "MCPCategory",
    "MCPCategoryGroup",
    "MCPCategories",
    "MonthCategory",
    "PlanMonth",
    "PlanMonthResponse",
    "PlanMonthSummary",
    "AllPlanMonthsResponse",
)

GROUP_ID = UUID("11111111-1111-1111-1111-111111111111")
CATEGORY_ID = UUID("22222222-2222-2222-2222-222222222222")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _catalog(mcp: FastMCP) -> dict[str, set[str]]:
    """List the resources and resource templates a server advertises."""
    async with Client(mcp) as client:
        resources = await client.list_resources()
        templates = await client.list_resource_templates()
    return {
        "resources": {str(r.uri) for r in resources},
        "templates": {t.uri_template for t in templates},
    }


async def _read_resource(mcp: FastMCP, uri: str) -> str:
    """Read a resource through an in-memory client and return its payload."""
    async with Client(mcp) as client:
        result = await client.read_resource(uri)
    return result[0].text


def _contains_null(value: object) -> bool:
    """Recursively check whether a decoded JSON payload holds a null value."""
    if isinstance(value, dict):
        return any(_contains_null(v) for v in value.values())
    if isinstance(value, list):
        return any(_contains_null(v) for v in value)
    return value is None


def _collect_keys(value: object) -> set[str]:
    """Recursively collect every mapping key in a decoded JSON payload."""
    if isinstance(value, dict):
        return set(value) | {k for v in value.values() for k in _collect_keys(v)}
    if isinstance(value, list):
        return {k for v in value for k in _collect_keys(v)}
    return set()


def _categories_response() -> ynab.CategoriesResponse:
    """A minimal but realistic YNAB categories response."""
    category = ynab.Category(
        id=CATEGORY_ID,
        category_group_id=GROUP_ID,
        name="Rent",
        hidden=False,
        internal=False,
        deleted=False,
        budgeted=50000,
        activity=-10000,
        balance=40000,
    )
    group = ynab.CategoryGroupWithCategories(
        id=GROUP_ID,
        name="Bills",
        hidden=False,
        internal=False,
        deleted=False,
        categories=[category],
    )
    return ynab.CategoriesResponse(
        data=ynab.CategoriesResponseData(
            category_groups=[group],
            server_knowledge=0,
        ),
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_tool_modules_register_expected_resources(monkeypatch):
    """Each tool module registers exactly the resource URIs it documents."""
    # The lean catalog is the default. Pin the flag so the assertion does not
    # depend on the ambient environment or on test execution order.
    monkeypatch.delenv("SHOW_FULL_RESOURCES", raising=False)

    registrars = {
        "transactions": register_transactions,
        "categories": register_categories,
        "planning": register_planning,
    }

    for label, expected in EXPECTED_REGISTRATION.items():
        mcp = FastMCP(label)
        registrars[label](mcp, YnabService(plan_id=TEST_PLAN_ID))

        catalog = asyncio.run(_catalog(mcp))

        assert catalog["resources"] == expected["resources"], (
            f"{label}: unexpected resource URIs. "
            f"Missing: {sorted(expected['resources'] - catalog['resources'])}, "
            f"unexpected: {sorted(catalog['resources'] - expected['resources'])}"
        )
        assert catalog["templates"] == expected["templates"], (
            f"{label}: unexpected resource templates. "
            f"Missing: {sorted(expected['templates'] - catalog['templates'])}, "
            f"unexpected: {sorted(catalog['templates'] - expected['templates'])}"
        )


def test_resources_serialize_through_the_schema_layer():
    """A registered resource returns lean JSON built by the MCP* schema models."""
    service = MagicMock()
    service.get_categories.return_value = _categories_response()

    mcp = FastMCP("categories")
    register_categories(mcp, service)

    payload = asyncio.run(_read_resource(mcp, "data://categories"))
    decoded = json.loads(payload)

    # The payload conforms to the schema layer...
    model = MCPCategories.model_validate(decoded)
    assert isinstance(model, MCPCategories)

    # ...and re-serializing it reproduces the wire format byte for byte,
    # which pins the "exclude_none" lean contract.
    assert model.model_dump_json(exclude_none=True) == payload

    # No "key": null noise anywhere in the payload.
    assert not _contains_null(decoded), "lean payload must not contain null values"

    # No SDK import bookkeeping leaks through.
    leaked = _collect_keys(decoded) & set(IMPORT_FIELDS)
    assert not leaked, f"import fields leaked into the payload: {sorted(leaked)}"

    # UUIDs are serialized as strings, not as objects.
    groups = decoded["category_groups"]
    assert len(groups) == 1
    assert groups[0]["id"] == str(GROUP_ID)
    assert groups[0]["categories"][0]["id"] == str(CATEGORY_ID)


def test_tool_modules_do_not_use_removed_validation_helper():
    """The tool modules must not fall back to the removed validation helper."""
    offenders = [
        path.name
        for path in sorted(TOOLS_DIR.glob("*.py"))
        if REMOVED_VALIDATION_HELPER in path.read_text(encoding="utf-8")
    ]

    assert not offenders, (
        f"{REMOVED_VALIDATION_HELPER} is referenced by {offenders}; "
        "the tools serialize through the MCP* schema layer instead"
    )


def test_public_schema_api_exposes_expected_models():
    """The schema package re-exports the documented public model surface."""
    import ynab_http_mcp.schemas as schemas

    for name in EXPECTED_SCHEMA_NAMES:
        assert hasattr(schemas, name), f"{name} is missing from ynab_http_mcp.schemas"
        assert name in schemas.__all__, f"{name} is missing from schemas.__all__"
        assert issubclass(getattr(schemas, name), BaseModel), (
            f"{name} is not a Pydantic model"
        )


def test_clean_ynab_data_functionality():
    """``clean_ynab_data`` converts rich types and drops import fields."""
    from datetime import date

    from ynab_http_mcp.utils.schema_utils import clean_ynab_data

    cleaned = clean_ynab_data(
        {
            "id": UUID("123e4567-e89b-12d3-a456-426614174000"),
            "date": date(2023, 1, 15),
            "amount": -50000,
            "import_id": "should-be-filtered",
            "name": "Test Transaction",
        }
    )

    assert cleaned["id"] == "123e4567-e89b-12d3-a456-426614174000", (
        "UUID should be converted to string"
    )
    assert cleaned["date"] == "2023-01-15", "Date should be converted to ISO string"
    assert cleaned["amount"] == -50000, "Primitive types should be preserved"
    assert "import_id" not in cleaned, "Import fields should be filtered"
    assert cleaned["name"] == "Test Transaction", "String fields should be preserved"
