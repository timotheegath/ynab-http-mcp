"""
Unit tests for the refactored category schemas.

Covers ``MCPCategory``, ``MCPCategoryGoal``, ``MCPCategories`` and the
two module-level goal explanation helpers, including the ``HIDE_DELETED``
filter on the flat-list wrapper.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Any, Dict
from uuid import UUID

import pytest
import ynab

from ynab_http_mcp.schemas.categories import (
    MCPCategories,
    MCPCategory,
    MCPCategoryGoal,
    _explain_goal_funding_status,
    _explain_goal_type,
)


# ---------------------------------------------------------------------------
# Test fixtures
# ---------------------------------------------------------------------------


CAT_UUID = UUID("00000000-0000-0000-0000-000000000001")
GRP_UUID = UUID("11111111-1111-1111-1111-111111111111")


def _base_category_kwargs(**overrides: Any) -> Dict[str, Any]:
    """Return the minimum kwargs needed to construct a ynab.Category."""
    kwargs: Dict[str, Any] = dict(
        id=CAT_UUID,
        category_group_id=GRP_UUID,
        name="Vacation",
        hidden=False,
        internal=False,
        deleted=False,
        budgeted=50000,
        activity=-10000,
        balance=40000,
    )
    kwargs.update(overrides)
    return kwargs


def _make_category(**overrides: Any) -> ynab.Category:
    return ynab.Category(**_base_category_kwargs(**overrides))


def _make_group_with_categories(
    *categories: ynab.Category,
    group_id: UUID = GRP_UUID,
    group_name: str = "Bills",
    deleted: bool = False,
) -> ynab.CategoryGroupWithCategories:
    return ynab.CategoryGroupWithCategories(
        id=group_id,
        name=group_name,
        hidden=False,
        internal=False,
        deleted=deleted,
        categories=list(categories),
    )


def _make_categories_response(
    *groups: ynab.CategoryGroupWithCategories,
) -> ynab.CategoriesResponse:
    return ynab.CategoriesResponse(
        data=ynab.CategoriesResponseData(
            category_groups=list(groups),
            server_knowledge=0,
        ),
    )


# ---------------------------------------------------------------------------
# Module-level helpers: _explain_goal_type
# ---------------------------------------------------------------------------


class TestExplainGoalType:
    def test_no_goal_type_returns_unknown(self) -> None:
        raw = _make_category()
        assert _explain_goal_type(raw) == "Unknown goal type: None"

    def test_tb(self) -> None:
        raw = _make_category(
            goal_type="TB", goal_target=100000, goal_target_formatted="$100.00"
        )
        result = _explain_goal_type(raw)
        assert "Target Category Balance" in result
        assert "$100.00" in result

    def test_tbd(self) -> None:
        raw = _make_category(
            goal_type="TBD",
            goal_target=100000,
            goal_target_formatted="$100.00",
            goal_target_date=date(2027, 1, 1),
        )
        result = _explain_goal_type(raw)
        assert "Target Category Balance by Date" in result
        assert "$100.00" in result
        assert "2027-01-01" in result

    @pytest.mark.parametrize(
        "needs_whole_amount,verb", [(True, "Set aside"), (False, "Refill")]
    )
    def test_mf_cadence_0_one_time(self, needs_whole_amount: bool, verb: str) -> None:
        raw = _make_category(
            goal_type="MF",
            goal_cadence=0,
            goal_needs_whole_amount=needs_whole_amount,
            goal_target=50000,
            goal_target_formatted="$50.00",
            goal_target_date=date(2026, 12, 1),
        )
        result = _explain_goal_type(raw)
        assert verb in result
        assert "$50.00" in result
        assert "2026-12-01" in result

    def test_mf_cadence_1_monthly_set_aside(self) -> None:
        raw = _make_category(
            goal_type="MF",
            goal_cadence=1,
            goal_cadence_frequency=2,
            goal_needs_whole_amount=True,
            goal_target=50000,
            goal_target_formatted="$50.00",
        )
        result = _explain_goal_type(raw)
        assert "Set aside" in result
        assert "2 month" in result

    def test_mf_cadence_1_monthly_refill(self) -> None:
        raw = _make_category(
            goal_type="MF",
            goal_cadence=1,
            goal_cadence_frequency=1,
            goal_needs_whole_amount=False,
            goal_target=50000,
            goal_target_formatted="$50.00",
        )
        result = _explain_goal_type(raw)
        assert "Refill" in result
        assert "1 month" in result

    def test_mf_cadence_1_missing_frequency_raises(self) -> None:
        raw = _make_category(
            goal_type="MF", goal_cadence=1, goal_cadence_frequency=None
        )
        with pytest.raises(ValueError, match="goal_cadence_frequency"):
            _explain_goal_type(raw)

    def test_mf_cadence_2_weekly(self) -> None:
        raw = _make_category(
            goal_type="MF",
            goal_cadence=2,
            goal_cadence_frequency=1,
            goal_needs_whole_amount=False,
            goal_target=2000,
            goal_target_formatted="$2.00",
        )
        result = _explain_goal_type(raw)
        assert "Refill" in result
        assert "2 week" in result

    def test_mf_cadence_2_missing_frequency_raises(self) -> None:
        raw = _make_category(
            goal_type="MF", goal_cadence=2, goal_cadence_frequency=None
        )
        with pytest.raises(ValueError, match="goal_cadence_frequency"):
            _explain_goal_type(raw)

    @pytest.mark.parametrize("cadence", [3, 4, 6, 12])
    def test_mf_cadence_3_to_12_every_n_months(self, cadence: int) -> None:
        raw = _make_category(
            goal_type="MF",
            goal_cadence=cadence,
            goal_needs_whole_amount=False,
            goal_target=50000,
            goal_target_formatted="$50.00",
        )
        result = _explain_goal_type(raw)
        assert f"every {cadence - 1} months" in result

    def test_mf_cadence_13_yearly(self) -> None:
        raw = _make_category(
            goal_type="MF",
            goal_cadence=13,
            goal_cadence_frequency=1,
            goal_needs_whole_amount=False,
            goal_target=50000,
            goal_target_formatted="$50.00",
        )
        result = _explain_goal_type(raw)
        # cadence 13 is "Yearly"; period = cadence * cadence_frequency (preserved
        # from the original YNAB SDK cadence formula).
        assert "Refill" in result
        assert "13 year" in result

    def test_mf_cadence_13_missing_frequency_raises(self) -> None:
        raw = _make_category(
            goal_type="MF", goal_cadence=13, goal_cadence_frequency=None
        )
        with pytest.raises(ValueError, match="goal_cadence_frequency"):
            _explain_goal_type(raw)

    def test_mf_cadence_14_every_two_years(self) -> None:
        raw = _make_category(
            goal_type="MF",
            goal_cadence=14,
            goal_needs_whole_amount=False,
            goal_target=50000,
            goal_target_formatted="$50.00",
        )
        result = _explain_goal_type(raw)
        assert "every 2 years" in result

    def test_mf_cadence_out_of_range_raises(self) -> None:
        raw = _make_category(goal_type="MF", goal_cadence=99)
        with pytest.raises(ValueError, match="Unrecognized goal cadence"):
            _explain_goal_type(raw)

    def test_need(self) -> None:
        raw = _make_category(goal_type="NEED")
        result = _explain_goal_type(raw)
        assert "Plan Your Spending" in result

    def test_unknown_goal_type(self) -> None:
        # "DEBT" is a valid ynab.Category.goal_type enum value but not one we
        # explicitly handle; the catch-all branch should still produce output.
        raw = _make_category(goal_type="DEBT")
        assert _explain_goal_type(raw) == "Unknown goal type: DEBT"


# ---------------------------------------------------------------------------
# Module-level helpers: _explain_goal_funding_status
# ---------------------------------------------------------------------------


class TestExplainGoalFundingStatus:
    def test_snoozed(self) -> None:
        raw = _make_category(
            goal_type="TB",
            goal_target=100000,
            goal_snoozed_at=datetime(2026, 1, 1, 12, 0, 0),
        )
        result = _explain_goal_funding_status(raw)
        assert "Snoozed" in result
        assert "2026-01-01" in result

    def test_no_target(self) -> None:
        raw = _make_category(goal_type="TB", goal_target=0)
        assert _explain_goal_funding_status(raw) == "No target set."

    def test_fully_funded_by_percentage(self) -> None:
        raw = _make_category(
            goal_type="TB", goal_target=100000, goal_percentage_complete=100
        )
        assert "Fully funded" in _explain_goal_funding_status(raw)

    def test_fully_funded_by_overall_left_zero(self) -> None:
        raw = _make_category(goal_type="TB", goal_target=100000, goal_overall_left=0)
        assert "Fully funded" in _explain_goal_funding_status(raw)

    def test_on_track_this_period(self) -> None:
        raw = _make_category(
            goal_type="TB",
            goal_target=100000,
            goal_percentage_complete=50,
            goal_under_funded=0,
            goal_months_to_budget=1,
        )
        result = _explain_goal_funding_status(raw)
        assert "On track" in result

    def test_on_track_with_multi_month_period(self) -> None:
        raw = _make_category(
            goal_type="TB",
            goal_target=100000,
            goal_percentage_complete=25,
            goal_under_funded=0,
            goal_months_to_budget=3,
        )
        result = _explain_goal_funding_status(raw)
        assert "On track" in result
        assert "3 months remaining" in result

    def test_underfunded(self) -> None:
        raw = _make_category(
            goal_type="TB",
            goal_target=100000,
            goal_percentage_complete=40,
            goal_under_funded=20000,
            goal_under_funded_formatted="$20.00",
            goal_overall_left=60000,
            goal_overall_left_formatted="$60.00",
            goal_months_to_budget=2,
        )
        result = _explain_goal_funding_status(raw)
        assert "Underfunded by $20.00" in result
        assert "40% complete" in result
        assert "$60.00" in result
        assert "2 month" in result


# ---------------------------------------------------------------------------
# MCPCategoryGoal.from_ynab
# ---------------------------------------------------------------------------


class TestMCPCategoryGoalFromYnab:
    def test_no_goal_returns_empty_instance(self) -> None:
        raw = _make_category()
        result = MCPCategoryGoal.from_ynab(raw)
        assert result.goal_type is None
        assert result.goal_summary is None
        assert result.goal_status is None
        assert result.goal_target is None
        # Pydantic model fields are all defaults
        dumped = result.model_dump()
        assert all(v is None for v in dumped.values())

    def test_tb_goal_populates_raw_and_summary(self) -> None:
        raw = _make_category(
            goal_type="TB",
            goal_target=100000,
            goal_target_formatted="$100.00",
            goal_percentage_complete=50,
            goal_overall_funded=50000,
            goal_overall_funded_formatted="$50.00",
            goal_overall_left=50000,
            goal_overall_left_formatted="$50.00",
            goal_under_funded=50000,
            goal_under_funded_formatted="$50.00",
        )
        result = MCPCategoryGoal.from_ynab(raw)
        assert result.goal_type == "TB"
        assert result.goal_target == 100000
        assert result.goal_target_formatted == "$100.00"
        assert result.goal_summary is not None
        assert "Target Category Balance" in result.goal_summary
        assert result.goal_status is not None
        assert "50% complete" in result.goal_status

    def test_mf_monthly_goal(self) -> None:
        raw = _make_category(
            goal_type="MF",
            goal_cadence=1,
            goal_cadence_frequency=1,
            goal_needs_whole_amount=False,
            goal_target=50000,
            goal_target_formatted="$50.00",
        )
        result = MCPCategoryGoal.from_ynab(raw)
        assert result.goal_type == "MF"
        assert "Refill" in (result.goal_summary or "")
        assert "month" in (result.goal_summary or "")

    def test_unknown_goal_type_does_not_raise(self) -> None:
        # "DEBT" is a valid ynab.Category.goal_type enum value but not one we
        # explicitly handle; the catch-all branch should still produce output.
        raw = _make_category(goal_type="DEBT")
        result = MCPCategoryGoal.from_ynab(raw)
        assert result.goal_type == "DEBT"
        assert result.goal_summary == "Unknown goal type: DEBT"


# ---------------------------------------------------------------------------
# MCPCategory.from_ynab
# ---------------------------------------------------------------------------


class TestMCPCategoryFromYnab:
    def test_from_raw_ynab_category(self) -> None:
        raw = _make_category(
            budgeted_formatted="$500.00",
            activity_formatted="-$100.00",
            balance_formatted="$400.00",
        )
        result = MCPCategory.from_ynab(raw)
        assert result.id == CAT_UUID
        assert result.category_group_id == GRP_UUID
        assert result.name == "Vacation"
        assert result.hidden is False
        assert result.internal is False
        assert result.deleted is False
        assert result.budgeted_formatted == "$500.00"
        assert result.activity_formatted == "-$100.00"
        assert result.balance_formatted == "$400.00"
        # No goal on the raw, so nested goal is the empty instance
        assert result.goal is not None
        assert result.goal.goal_type is None

    def test_from_wrapped_ynab_category_response(self) -> None:
        raw_cat = _make_category(
            name="Power",
            goal_type="TB",
            goal_target=20000,
            goal_target_formatted="$20.00",
            goal_percentage_complete=100,
        )
        wrapped = ynab.CategoryResponse(
            data=ynab.CategoryResponseData(category=raw_cat)
        )
        result = MCPCategory.from_ynab(wrapped)
        assert result.name == "Power"
        assert result.goal is not None
        assert result.goal.goal_type == "TB"
        assert "Target Category Balance" in (result.goal.goal_summary or "")
        assert "Fully funded" in (result.goal.goal_status or "")

    def test_bare_and_wrapped_yield_same_shape(self) -> None:
        raw_cat = _make_category(
            goal_type="NEED",
            goal_needs_whole_amount=True,
            goal_target=10000,
        )
        bare = MCPCategory.from_ynab(raw_cat)
        wrapped = MCPCategory.from_ynab(
            ynab.CategoryResponse(data=ynab.CategoryResponseData(category=raw_cat))
        )
        assert bare.model_dump() == wrapped.model_dump()


# ---------------------------------------------------------------------------
# MCPCategories.from_ynab
# ---------------------------------------------------------------------------


class TestMCPCategoriesFromYnab:
    def test_default_hides_deleted(self) -> None:
        active = _make_category(
            id=UUID("00000000-0000-0000-0000-000000000001"),
            name="Active",
        )
        deleted = _make_category(
            id=UUID("00000000-0000-0000-0000-000000000002"),
            name="Deleted",
            deleted=True,
        )
        group = _make_group_with_categories(active, deleted)
        response = _make_categories_response(group)

        result = MCPCategories.from_ynab(response)

        assert len(result.categories) == 1
        assert result.categories[0].name == "Active"

    def test_flattens_across_groups(self) -> None:
        a = _make_category(
            id=UUID("00000000-0000-0000-0000-000000000001"),
            name="A",
        )
        b = _make_category(
            id=UUID("00000000-0000-0000-0000-000000000002"),
            name="B",
        )
        c = _make_category(
            id=UUID("00000000-0000-0000-0000-000000000003"),
            name="C",
        )
        g1 = _make_group_with_categories(a, b)
        g2 = _make_group_with_categories(
            c, group_id=UUID("22222222-2222-2222-2222-222222222222")
        )
        response = _make_categories_response(g1, g2)

        result = MCPCategories.from_ynab(response)

        names = [cat.name for cat in result.categories]
        assert names == ["A", "B", "C"]

    def test_hide_disabled_subclass_includes_deleted(self) -> None:
        class ShowAll(MCPCategories):
            HIDE_DELETED = False

        active = _make_category(name="Active")
        deleted = _make_category(name="Deleted", deleted=True)
        group = _make_group_with_categories(active, deleted)
        response = _make_categories_response(group)

        result = ShowAll.from_ynab(response)

        names = [cat.name for cat in result.categories]
        assert names == ["Active", "Deleted"]


# ---------------------------------------------------------------------------
# Public API: schemas.categories no longer exports the old wrappers
# ---------------------------------------------------------------------------


class TestPublicSchemaSurface:
    def test_old_types_are_not_exported(self) -> None:
        import ynab_http_mcp.schemas.categories as categories_module

        for name in ("CategoriesResponse", "CategoryResponse", "CategoryGroup"):
            assert not hasattr(categories_module, name), (
                f"{name} should have been deleted from schemas.categories"
            )

    def test_package_init_exports(self) -> None:
        from ynab_http_mcp.schemas import (  # noqa: F401
            MCPCategory,
            MCPCategories,
            MCPCategoryGoal,
        )
