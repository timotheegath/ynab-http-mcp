from datetime import datetime
from ynab import PlanSummaryResponse, Configuration, ApiClient, PlansApi
from uuid import UUID
import os


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

def set_default_plan(ynab_config: Configuration) -> UUID:
    plan_id : UUID | None
    plan_id_str = os.getenv("YNAB_PLAN_ID")
    if plan_id_str is not None:        
        return UUID(plan_id_str)
    else:
        with ApiClient(ynab_config) as api_client:
            plans_api = PlansApi(api_client)
            plans_response = plans_api.get_plans()
            plan_id = find_latest_plan(plans_response)
            if plan_id is None:
                raise ValueError("There are no budgets for this YNAB user.")
            else:
                return plan_id