"""
MCP prompts for YNAB HTTP MCP.

Currently ships a single prompt, ``plan_expense``, which choreographs the
advisory "can I afford this one-time expense?" conversation. All semantic
judgment — category matching, credibility weighing, cuttability, and the
essential-versus-discretionary call — is deliberately left to the client
agent; the prompt supplies the data grounding and the reasoning discipline.

The prompt is advisory only: it never instructs the agent to call a write
tool, and it scopes the conversation to one-time expenses.
"""

from __future__ import annotations

_PLAN_EXPENSE_TEMPLATE = """\
You are helping a YNAB user decide whether they can afford a one-time \
expense, and if not, where the money could come from. This is advisory only \
— recommend, do not act.

The user wants to plan for this expense:

- Description: {expense_description}
- Target amount: {target_amount}
- Target month: {target_month}

The expense must be fully funded by the START of the target month.

Ground your answer in the planning-insights aggregate. Call the tool \
get_plan_insights (optionally with since_date/until_date covering up \
to the target month) and use it as your only data foundation:

- Each month carries a month-level Ready-to-Assign (to-be-budgeted) amount. \
Income is deliberately absent from the payload.
- Each category carries a per-month budgeted / activity / balance series (in \
milliunits and formatted), a goal block with the raw goal integers plus a \
server-computed goal_monthly_rate, and derived stats: average monthly \
budgeted, average monthly activity, funding ratio, balance runway, and \
overfunded-versus-target.

Steps:

1. Resolve the expense to a category by semantic match against the full \
category list — do not rely on string matching alone ("Bali" should map to a \
Trips/Travel category by meaning).

2. If no existing category matches, assume a zero available balance and zero \
funding pace for this expense, and propose creating a dedicated category for \
it.

3. Establish the forecast:
   - If the category has a goal, TRUST the declared schedule as the basis: \
use the goal_monthly_rate together with YNAB's own progress fields \
(under_funded, overall_left, months_to_budget, percentage_complete).
   - REQUIRED credibility check: judge that schedule against demonstrated \
assignment behavior (the per-month budgeted/activity series and the funding \
ratio) before relying on it. A schedule contradicted by behavior is not a \
forecast.
   - Roll the forecast forward to the user's target month yourself: add any \
already-written forward assignments, then net out expected spending.

4. Verdict:
   - If the expense is funded in time, answer plainly: on track — change \
nothing.
   - Otherwise, explain the shortfall and narrate one or two funding plans.

5. Hunt for funding sources from these objective signals only, applying your \
own judgment about category names and user context to classify what is truly \
cuttable (essential vs. discretionary):
   - Ready-to-Assign surplus (current month is sweepable).
   - Categories overfunded versus their goal target.
   - Idle balances (funding ratio well below 1.0, indicating chronically \
overfunded behavior).
   - Never source funds from overspent (negative-balance) categories.

Do NOT call any write tool (no budget assignment, goal update, or transaction \
creation). This covers one-time expenses only — recurring expense simulation \
is out of scope.
"""


def build_plan_expense_message(
    expense_description: str, target_amount: str, target_month: str
) -> str:
    """Render the ``plan_expense`` prompt message for the given inputs."""
    return _PLAN_EXPENSE_TEMPLATE.format(
        expense_description=expense_description,
        target_amount=target_amount,
        target_month=target_month,
    )


def plan_expense(
    expense_description: str, target_amount: str, target_month: str
) -> str:
    """Advisory prompt: can the user afford a one-time expense by a target month?"""
    return build_plan_expense_message(expense_description, target_amount, target_month)


def register(mcp) -> None:
    """Register the ``plan_expense`` prompt on the server."""
    mcp.prompt(
        name="plan_expense",
        description=(
            "Choreograph an advisory affordability conversation for a one-time "
            "expense: ground in the planning-insights aggregate, match a "
            "category semantically, trust-check the goal schedule, and hunt "
            "funding sources. Never instructs write tools."
        ),
    )(plan_expense)
