"""
Focused catalog-footprint tests for MCP tool and resource serialization.

Verifies that the serialized ``tools/list``, ``resources/list``, and
``resources/templates/list`` payloads stay within agreed character budgets
and that every tool name, field, constraint, resource URI, and semantic
description requirement is preserved after description trimming.
"""

from __future__ import annotations

import asyncio
import json
import os
from typing import Any, List, Set

import pytest

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

# Ensure YNAB_API_KEY is set so YnabService can be constructed
os.environ.setdefault("YNAB_API_KEY", "00000000-0000-0000-0000-000000000000")


def _compact_json(obj: Any) -> str:
    """Serialize an object to compact JSON (no whitespace)."""
    return json.dumps(obj, separators=(",", ":"), sort_keys=True)


async def _fetch_catalog():
    """Build server and fetch tools/resources/templates."""
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
        resources_raw = await client.list_resources()
        templates_raw = await client.list_resource_templates()

    return {
        "tools": [t.model_dump(mode="json", exclude_none=True) for t in tools_raw],
        "tools_raw": tools_raw,
        "resources": [
            r.model_dump(mode="json", exclude_none=True) for r in resources_raw
        ],
        "resources_raw": resources_raw,
        "templates": [
            t.model_dump(mode="json", exclude_none=True) for t in templates_raw
        ],
        "templates_raw": templates_raw,
    }


@pytest.fixture(scope="session")
def catalog_data():
    """Session-scoped sync fixture that fetches catalog data."""
    return asyncio.run(_fetch_catalog())


# ---------------------------------------------------------------------------
# 1.1 – 1.4  Footprint assertions
# ---------------------------------------------------------------------------


class TestCatalogFootprint:
    """Character-budget assertions for the serialized MCP catalogs."""

    TOOL_BUDGET = 30_000
    RESOURCE_TEMPLATE_BUDGET = 8_000

    def test_tool_catalog_stays_within_budget(self, catalog_data):
        tools_json = _compact_json(catalog_data["tools"])
        char_count = len(tools_json)
        assert char_count <= self.TOOL_BUDGET, (
            f"Tool catalog {char_count} chars exceeds budget {self.TOOL_BUDGET}"
        )

    def test_resource_and_template_catalog_stays_within_budget(self, catalog_data):
        combined = {
            "resources": catalog_data["resources"],
            "templates": catalog_data["templates"],
        }
        combined_json = _compact_json(combined)
        char_count = len(combined_json)
        assert char_count <= self.RESOURCE_TEMPLATE_BUDGET, (
            f"Resource+template catalog {char_count} chars exceeds "
            f"budget {self.RESOURCE_TEMPLATE_BUDGET}"
        )


# ---------------------------------------------------------------------------
# 1.2  Tool contract assertions
# ---------------------------------------------------------------------------


EXPECTED_TOOL_NAMES: Set[str] = {
    # Budget management tools
    "assign_budget_to_category",
    "update_category_goal_to_recurring",
    "update_category_goal_to_target_date",
    "update_category_details",
    "clear_category_goals",
    "create_transaction",
    "check_budget_health",
    "get_spending_insights",
    "get_money_movement_insights",
    "get_money_movement_insights_for_month",
    # ResourcesAsTools gateway
    "list_resources",
    "read_resource",
}

# (tool_name, field_name, required, type_str, has_ge, has_pattern, enum_values)
TOOL_FIELD_CONTRACTS: List[tuple] = [
    # assign_budget_to_category -> AssignBudgetCategoryRequest
    ("assign_budget_to_category", "month", True, "string", False, False, None),
    ("assign_budget_to_category", "category_id", True, "string", False, False, None),
    (
        "assign_budget_to_category",
        "budgeted_amount",
        True,
        "integer",
        True,
        False,
        None,
    ),
    # update_category_goal_to_recurring -> UpdateCategoryGoalRecurringRequest
    (
        "update_category_goal_to_recurring",
        "category_id",
        True,
        "string",
        False,
        True,
        None,
    ),
    (
        "update_category_goal_to_recurring",
        "goal_target",
        True,
        "integer",
        True,
        False,
        None,
    ),
    (
        "update_category_goal_to_recurring",
        "goal_needs_whole_amount",
        True,
        "boolean",
        False,
        False,
        None,
    ),
    (
        "update_category_goal_to_recurring",
        "goal_frequency",
        True,
        "string",
        False,
        False,
        ["monthly", "weekly", "daily", "yearly"],
    ),
    (
        "update_category_goal_to_recurring",
        "note",
        False,
        "string",
        False,
        False,
        None,
    ),
    # update_category_goal_to_target_date -> UpdateCategoryTargetDateRequest
    (
        "update_category_goal_to_target_date",
        "category_id",
        True,
        "string",
        False,
        True,
        None,
    ),
    (
        "update_category_goal_to_target_date",
        "goal_target",
        True,
        "integer",
        True,
        False,
        None,
    ),
    (
        "update_category_goal_to_target_date",
        "goal_target_date",
        True,
        "string",
        False,
        True,
        None,
    ),
    # update_category_details -> UpdateCategoryDetailsRequest
    (
        "update_category_details",
        "category_id",
        True,
        "string",
        False,
        True,
        None,
    ),
    ("update_category_details", "name", False, "string", False, False, None),
    ("update_category_details", "note", False, "string", False, False, None),
    (
        "update_category_details",
        "category_group_id",
        False,
        "string",
        False,
        True,
        None,
    ),
    # clear_category_goals -> ClearCategoryGoalRequest
    ("clear_category_goals", "category_id", True, "string", False, True, None),
    ("clear_category_goals", "note", False, "string", False, False, None),
    # create_transaction -> CreateTransactionRequest
    ("create_transaction", "account_id", True, "string", False, False, None),
    ("create_transaction", "date", True, "string", False, False, None),
    ("create_transaction", "amount", True, "integer", False, False, None),
    ("create_transaction", "payee_id", False, "string", False, False, None),
    ("create_transaction", "payee_name", False, "string", False, False, None),
    ("create_transaction", "category_id", False, "string", False, False, None),
    ("create_transaction", "memo", False, "string", False, False, None),
    ("create_transaction", "cleared", False, "string", False, False, None),
    ("create_transaction", "approved", False, "boolean", False, False, None),
    ("create_transaction", "flag_color", False, "string", False, False, None),
    # check_budget_health
    ("check_budget_health", "month", True, "string", False, False, None),
    # get_spending_insights
    ("get_spending_insights", "month", True, "string", False, False, None),
    ("get_spending_insights", "category_id", False, "string", False, False, None),
    # get_money_movement_insights
    (
        "get_money_movement_insights",
        "since_date",
        False,
        "string",
        False,
        False,
        None,
    ),
    (
        "get_money_movement_insights",
        "until_date",
        False,
        "string",
        False,
        False,
        None,
    ),
    # get_money_movement_insights_for_month
    (
        "get_money_movement_insights_for_month",
        "month_date",
        True,
        "string",
        False,
        False,
        None,
    ),
]


class TestToolContract:
    """Verify every tool name, field, constraint, and annotation is preserved."""

    def test_all_expected_tools_present(self, catalog_data):
        names = {t["name"] for t in catalog_data["tools"]}
        assert names == EXPECTED_TOOL_NAMES, (
            f"Tool name mismatch. Missing: {EXPECTED_TOOL_NAMES - names}. "
            f"Extra: {names - EXPECTED_TOOL_NAMES}"
        )

    def test_tool_field_contracts(self, catalog_data):
        """Check every expected field's required/type/constraint/enum."""
        tools_by_name = {t["name"]: t for t in catalog_data["tools"]}

        for (
            tool_name,
            field_name,
            required,
            type_str,
            has_ge,
            has_pattern,
            enum_values,
        ) in TOOL_FIELD_CONTRACTS:
            tool = tools_by_name.get(tool_name)
            assert tool is not None, f"Tool '{tool_name}' not found"
            input_schema = tool.get("inputSchema", {})
            props = input_schema.get("properties", {})

            # Tools using Pydantic request models wrap fields in a "request" object
            if field_name not in props and "request" in props:
                request_props = props["request"].get("properties", {})
                assert field_name in request_props, (
                    f"Field '{field_name}' missing from tool '{tool_name}' "
                    f"(not in top-level props or request wrapper)"
                )
                field = request_props[field_name]
                required_list = props["request"].get("required", [])
            else:
                assert field_name in props, (
                    f"Field '{field_name}' missing from tool '{tool_name}'"
                )
                field = props[field_name]
                required_list = input_schema.get("required", [])

            # Required/optional
            if required:
                assert field_name in required_list, (
                    f"Field '{field_name}' in tool '{tool_name}' should be required"
                )
            else:
                assert field_name not in required_list, (
                    f"Field '{field_name}' in tool '{tool_name}' should be optional"
                )

            # Type - handle nullable fields (anyOf with null)
            if field.get("type") != type_str:
                any_of = field.get("anyOf", [])
                types_in_anyof = {s.get("type") for s in any_of if s.get("type")}
                assert type_str in types_in_anyof, (
                    f"Field '{field_name}' in tool '{tool_name}' expected type "
                    f"'{type_str}', got anyOf with {types_in_anyof}"
                )

            # Numeric bound (ge)
            if has_ge:
                assert "minimum" in field, (
                    f"Field '{field_name}' in tool '{tool_name}' should have minimum"
                )
                assert field["minimum"] >= 0

            # Pattern - may be inside anyOf for nullable fields
            if has_pattern:
                if "pattern" in field:
                    pass  # direct pattern
                else:
                    any_of = field.get("anyOf", [])
                    has_pattern_in_anyof = any("pattern" in s for s in any_of)
                    assert has_pattern_in_anyof, (
                        f"Field '{field_name}' in tool '{tool_name}' should have pattern"
                    )

            # Enum values
            if enum_values is not None:
                assert "enum" in field, (
                    f"Field '{field_name}' in tool '{tool_name}' should have enum"
                )
                assert set(field["enum"]) == set(enum_values), (
                    f"Field '{field_name}' in tool '{tool_name}' enum mismatch. "
                    f"Expected {set(enum_values)}, got {set(field['enum'])}"
                )

    def test_destructive_annotations_preserved(self, catalog_data):
        """Verify destructiveHint annotations on mutation tools."""
        tools_by_name = {t["name"]: t for t in catalog_data["tools"]}
        destructive_tools = {
            "assign_budget_to_category",
            "update_category_goal_to_recurring",
            "update_category_goal_to_target_date",
            "update_category_details",
            "clear_category_goals",
        }
        for name in destructive_tools:
            t = tools_by_name[name]
            ann = t.get("annotations") or {}
            assert ann.get("destructiveHint") is True, (
                f"Tool '{name}' should have destructiveHint=True"
            )

    def test_readonly_annotations_preserved(self, catalog_data):
        """Verify readOnlyHint annotations on read-only tools."""
        tools_by_name = {t["name"]: t for t in catalog_data["tools"]}
        readonly_tools = {
            "check_budget_health",
            "get_spending_insights",
            "get_money_movement_insights",
            "get_money_movement_insights_for_month",
        }
        for name in readonly_tools:
            t = tools_by_name[name]
            ann = t.get("annotations") or {}
            assert ann.get("readOnlyHint") is True, (
                f"Tool '{name}' should have readOnlyHint=True"
            )


# ---------------------------------------------------------------------------
# 1.3  Resource catalog contract assertions
# ---------------------------------------------------------------------------


EXPECTED_RESOURCE_URIS: Set[str] = {
    "data://accounts",
    "data://categories",
    "data://months",
    "data://payees",
}

EXPECTED_RESOURCE_TEMPLATE_URIS: Set[str] = {
    "data://accounts/{account_id}",
    "data://accounts/{account_id}/full",
    "data://categories/{category_id}",
    "data://categories/{category_id}/full",
    "data://months/{month_date}",
    "data://months/{month_date}/full",
    "data://months/{month_date}/categories/{category_id}",
    "data://months/{month_date}/categories/{category_id}/full",
    "data://payees/{id}",
    "data://payees/{id}/full",
    "data://transactions/{id}",
    "data://transactions/{id}/full",
    "data://transactions{?since_date,until_date,type,limit}",
    "data://transactions/insights{?since_date,until_date,account_id}",
    "data://accounts/{account_id}/transactions{?since_date,until_date,type}",
    "data://months/{month_date}/transactions{?type}",
    "data://payees/{payee_id}/transactions{?since_date,until_date,type}",
    "data://categories/{category_id}/transactions{?since_date,until_date,type}",
}


class TestResourceContract:
    """Verify every resource URI and template is registered."""

    def test_all_static_resources_present(self, catalog_data):
        uris = {r["uri"] for r in catalog_data["resources"]}
        assert uris == EXPECTED_RESOURCE_URIS, (
            f"Resource URI mismatch. Missing: {EXPECTED_RESOURCE_URIS - uris}. "
            f"Extra: {uris - EXPECTED_RESOURCE_URIS}"
        )

    def test_all_resource_templates_present(self, catalog_data):
        uris = {t["uriTemplate"] for t in catalog_data["templates"]}
        assert uris == EXPECTED_RESOURCE_TEMPLATE_URIS, (
            f"Template URI mismatch. Missing: {EXPECTED_RESOURCE_TEMPLATE_URIS - uris}. "
            f"Extra: {uris - EXPECTED_RESOURCE_TEMPLATE_URIS}"
        )

    def test_resources_as_tools_gateway_present(self, catalog_data):
        """Verify list_resources and read_resource tools exist."""
        names = {t["name"] for t in catalog_data["tools"]}
        assert "list_resources" in names
        assert "read_resource" in names


# ---------------------------------------------------------------------------
# 1.5  Semantic description assertions
# ---------------------------------------------------------------------------


def _get_field(tool: dict, field_name: str) -> dict:
    """Get a field from a tool's inputSchema, handling request wrapper."""
    props = tool.get("inputSchema", {}).get("properties", {})
    if field_name in props:
        return props[field_name]
    if "request" in props:
        request_props = props["request"].get("properties", {})
        if field_name in request_props:
            return request_props[field_name]
    raise KeyError(f"Field '{field_name}' not found in tool '{tool.get('name')}'")


class TestSemanticDescriptions:
    """Verify descriptions retain operational semantics."""

    def test_milliunits_identified_in_tool_inputs(self, catalog_data):
        """Monetary inputs must mention milliunits."""
        tools_by_name = {t["name"]: t for t in catalog_data["tools"]}
        milliunit_fields = {
            ("assign_budget_to_category", "budgeted_amount"),
            ("create_transaction", "amount"),
            ("update_category_goal_to_recurring", "goal_target"),
            ("update_category_goal_to_target_date", "goal_target"),
        }
        for tool_name, field_name in milliunit_fields:
            tool = tools_by_name[tool_name]
            field = _get_field(tool, field_name)
            desc = field.get("description", "")
            assert "milliunit" in desc.lower(), (
                f"Field '{field_name}' in tool '{tool_name}' should mention milliunits"
            )

    def test_date_format_in_tool_inputs(self, catalog_data):
        """Date fields must identify YYYY-MM-DD format."""
        tools_by_name = {t["name"]: t for t in catalog_data["tools"]}
        date_fields = {
            ("assign_budget_to_category", "month"),
            ("create_transaction", "date"),
            ("update_category_goal_to_target_date", "goal_target_date"),
            ("check_budget_health", "month"),
            ("get_spending_insights", "month"),
        }
        for tool_name, field_name in date_fields:
            tool = tools_by_name[tool_name]
            field = _get_field(tool, field_name)
            desc = field.get("description", "")
            assert "YYYY-MM" in desc.upper() or "YYYY-MM" in desc, (
                f"Field '{field_name}' in tool '{tool_name}' should mention date format"
            )

    def test_full_details_mentioned_in_full_resources(self, catalog_data):
        """Every Full resource description must mention full_details."""
        templates_by_uri = {t["uriTemplate"]: t for t in catalog_data["templates"]}
        full_uris = [
            uri for uri in EXPECTED_RESOURCE_TEMPLATE_URIS if uri.endswith("/full")
        ]
        for uri in full_uris:
            t = templates_by_uri[uri]
            desc = t.get("description", "")
            assert "full_details" in desc.lower(), (
                f"Full resource '{uri}' description should mention full_details"
            )

    def test_full_resources_identify_drill_in_purpose(self, catalog_data):
        """Full resources should mention arithmetic or SDK-fidelity."""
        templates_by_uri = {t["uriTemplate"]: t for t in catalog_data["templates"]}
        full_uris = [
            uri for uri in EXPECTED_RESOURCE_TEMPLATE_URIS if uri.endswith("/full")
        ]
        for uri in full_uris:
            t = templates_by_uri[uri]
            desc = t.get("description", "")
            has_purpose = (
                "arithmetic" in desc.lower()
                or "sdk-fidelity" in desc.lower()
                or "raw sdk" in desc.lower()
                or "integer" in desc.lower()
            )
            assert has_purpose, (
                f"Full resource '{uri}' description should mention arithmetic, "
                f"SDK-fidelity, raw SDK, or integer access purpose"
            )

    def test_lean_resources_have_concise_descriptions(self, catalog_data):
        """Lean resource descriptions should be concise (no multi-line essays)."""
        templates_by_uri = {t["uriTemplate"]: t for t in catalog_data["templates"]}
        lean_uris = [
            uri for uri in EXPECTED_RESOURCE_TEMPLATE_URIS if not uri.endswith("/full")
        ]
        for uri in lean_uris:
            t = templates_by_uri[uri]
            desc = t.get("description", "")
            assert "Lean endpoint" not in desc, (
                f"Lean resource '{uri}' should not reference 'Lean endpoint'"
            )

    def test_goal_operations_distinguishable(self, catalog_data):
        """Similar goal tools must have distinct descriptions."""
        tools_by_name = {t["name"]: t for t in catalog_data["tools"]}
        recurring_desc = tools_by_name["update_category_goal_to_recurring"].get(
            "description", ""
        )
        target_date_desc = tools_by_name["update_category_goal_to_target_date"].get(
            "description", ""
        )
        details_desc = tools_by_name["update_category_details"].get("description", "")
        clear_desc = tools_by_name["clear_category_goals"].get("description", "")

        assert "recurring" in recurring_desc.lower()
        assert (
            "target date" in target_date_desc.lower()
            or "target" in target_date_desc.lower()
        )
        assert (
            "name" in details_desc.lower()
            or "note" in details_desc.lower()
            or "group" in details_desc.lower()
        )
        assert "clear" in clear_desc.lower()

    def test_date_boundary_semantics_preserved(self, catalog_data):
        """Date filter descriptions should retain boundary semantics."""
        templates_by_uri = {t["uriTemplate"]: t for t in catalog_data["templates"]}
        insights = templates_by_uri.get(
            "data://transactions/insights{?since_date,until_date,account_id}"
        )
        if insights:
            desc = insights.get("description", "")
            assert "exclusive" in desc.lower() or "default" in desc.lower(), (
                "Insights resource should mention exclusive boundary or default window"
            )


# ---------------------------------------------------------------------------
# 4.1  Focused verification: run catalog-footprint tests
# ---------------------------------------------------------------------------


class TestFocusedVerification:
    """Additional focused checks that complement the above."""

    def test_tool_descriptions_not_empty(self, catalog_data):
        """Every tool should have a non-empty description."""
        for t in catalog_data["tools"]:
            assert t.get("description"), f"Tool '{t['name']}' has empty description"

    def test_no_lean_endpoint_essays_in_descriptions(self, catalog_data):
        """Resource descriptions should not contain repeated Lean/Full essays."""
        for t in catalog_data["templates"]:
            desc = t.get("description", "")
            assert "The Lean endpoint" not in desc, (
                f"Template '{t.get('uriTemplate')}' still has old Lean endpoint essay"
            )
            assert "returns only the" not in desc, (
                f"Template '{t.get('uriTemplate')}' still has verbose description"
            )
