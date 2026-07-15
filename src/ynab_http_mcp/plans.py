from .utils.dates import parse_timestamp
from ynab import PlanSummaryResponse
from uuid import UUID
def find_latest_plan(plans: PlanSummaryResponse) -> UUID | None:
    """
    Amongst all of the user's plans, find the one that was modified the most recently.
    Returns its UUID.
    """
    if not plans:
        return None
    plan_list = plans.to_dict()["data"]["plans"]
    most_recent_plan = max(
        plan_list,
        key=lambda plan: parse_timestamp(plan["last_modified_on"]),
    )
    return UUID(most_recent_plan["id"])