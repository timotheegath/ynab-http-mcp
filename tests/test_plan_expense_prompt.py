"""
Tests for the ``plan_expense`` MCP prompt.

Covers prompt registration and its three arguments (3.1) and content
assertions for every spec scenario (3.2): aggregate grounded, start-of-month
deadline, no-match handling, goal-trusting with credibility check, roll-forward
and happy path, funding-source signals with agent-side classification, and
advisory-only scope.
"""

from __future__ import annotations

import asyncio
from typing import Any, List

from fastmcp import FastMCP
from fastmcp.client import Client

from ynab_http_mcp import prompts


def _prompt_texts(result: Any) -> List[str]:
    """Extract all text from a ``GetPromptResult``'s messages."""
    texts: List[str] = []
    for message in result.messages:
        content = message.content
        if isinstance(content, str):
            texts.append(content)
        elif isinstance(content, list):
            for part in content:
                if isinstance(part, dict):
                    texts.append(part.get("text", ""))
                elif hasattr(part, "text"):
                    texts.append(part.text)
        elif hasattr(content, "text"):
            texts.append(content.text)
    return texts


def _get_prompt(arguments: dict) -> str:
    async def run() -> str:
        mcp = FastMCP("test")
        prompts.register(mcp)
        async with Client(mcp) as client:
            result = await client.get_prompt("plan_expense", arguments=arguments)
            return "\n".join(_prompt_texts(result))

    return asyncio.run(run())


# ---------------------------------------------------------------------------
# 3.1 Registration
# ---------------------------------------------------------------------------


class TestPromptRegistration:
    def test_prompt_listed_with_three_arguments(self) -> None:
        async def run() -> list:
            mcp = FastMCP("test")
            prompts.register(mcp)
            async with Client(mcp) as client:
                return await client.list_prompts()

        listed = asyncio.run(run())
        plan = [p for p in listed if p.name == "plan_expense"]
        assert len(plan) == 1
        args = {a.name: a for a in plan[0].arguments}
        assert set(args) == {"expense_description", "target_amount", "target_month"}
        for arg in args.values():
            assert arg.required is True


# ---------------------------------------------------------------------------
# 3.2 Content assertions
# ---------------------------------------------------------------------------


class TestPromptContent:
    def test_names_aggregate_and_deadline(self) -> None:
        text = _get_prompt(
            {
                "expense_description": "trip",
                "target_amount": "£3000",
                "target_month": "2026-11",
            }
        )
        assert "get_plan_insights" in text
        assert "fully funded" in text
        assert "start of the target month" in text.lower()

    def test_no_match_instructions(self) -> None:
        text = _get_prompt(
            {
                "expense_description": "trip",
                "target_amount": "£3000",
                "target_month": "2026-11",
            }
        )
        assert "zero available balance" in text.lower()
        assert "zero funding pace" in text.lower()
        assert "dedicated category" in text.lower()

    def test_credibility_check_instructed(self) -> None:
        text = _get_prompt(
            {
                "expense_description": "trip",
                "target_amount": "£3000",
                "target_month": "2026-11",
            }
        )
        assert "credibility check" in text.lower()

    def test_happy_path_verdict(self) -> None:
        text = _get_prompt(
            {
                "expense_description": "trip",
                "target_amount": "£3000",
                "target_month": "2026-11",
            }
        )
        assert "on track" in text.lower()
        assert "change nothing" in text.lower()

    def test_goal_schedule_and_roll_forward(self) -> None:
        text = _get_prompt(
            {
                "expense_description": "trip",
                "target_amount": "£3000",
                "target_month": "2026-11",
            }
        )
        assert "goal_monthly_rate" in text
        assert "roll the forecast forward" in text.lower()
        assert "net out expected spending" in text.lower()

    def test_funding_source_signals_named(self) -> None:
        text = _get_prompt(
            {
                "expense_description": "trip",
                "target_amount": "£3000",
                "target_month": "2026-11",
            }
        )
        lowered = text.lower()
        assert "ready-to-assign" in lowered
        assert "overfunded versus their goal target" in lowered
        assert "idle balances" in lowered
        assert "funding ratio" in lowered
        assert "1.0" in lowered

    def test_agent_side_classification(self) -> None:
        text = _get_prompt(
            {
                "expense_description": "trip",
                "target_amount": "£3000",
                "target_month": "2026-11",
            }
        )
        assert "essential" in text.lower()
        assert "discretionary" in text.lower()

    def test_no_write_tool_instructions(self) -> None:
        text = _get_prompt(
            {
                "expense_description": "trip",
                "target_amount": "£3000",
                "target_month": "2026-11",
            }
        )
        assert "do not call any write tool" in text.lower()
        for tool in (
            "assign_budget_to_category",
            "update_category_goal",
            "create_transaction",
        ):
            assert tool not in text

    def test_advisory_only_one_time_expenses(self) -> None:
        text = _get_prompt(
            {
                "expense_description": "trip",
                "target_amount": "£3000",
                "target_month": "2026-11",
            }
        )
        assert "advisory only" in text.lower()
        assert "one-time expenses only" in text.lower()

    def test_arguments_embedded(self) -> None:
        text = _get_prompt(
            {
                "expense_description": "trip to Bali",
                "target_amount": "£3000",
                "target_month": "2026-11",
            }
        )
        assert "trip to Bali" in text
        assert "£3000" in text
        assert "2026-11" in text
