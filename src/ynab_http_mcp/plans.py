from datetime import datetime
from ynab import PlanSummaryResponse
from uuid import UUID


def find_latest_plan(plans: PlanSummaryResponse) -> UUID | None:
    """
    Amongst all of the user's plans, find the one that was modified the most recently.
    Returns its UUID.
    """
    if not plans or not plans.data.plans:
        return None

    plan_list = plans.data.plans

    # Filter out plans with None last_modified_on and find the most recent
    plans_with_timestamps = [
        plan for plan in plan_list if plan.last_modified_on is not None
    ]

    if not plans_with_timestamps:
        # If no plans have timestamps, return the first plan's ID
        return plan_list[0].id

    most_recent_plan = max(
        plans_with_timestamps,
        key=lambda plan: plan.last_modified_on or datetime.min,
    )
    return most_recent_plan.id
