import os
import ynab
from uuid import UUID
from datetime import datetime


class YnabService:
    def __init__(self):
        self.config = ynab.Configuration(access_token=os.getenv("YNAB_API_KEY"))
        self.plan_id = YnabService._set_default_plan(self.config)

    def list_plans(self):
        with ynab.ApiClient(self.config) as api_client:
            plans_api = ynab.PlansApi(api_client)
            return plans_api.get_plans()

    def get_categories(self):
        with ynab.ApiClient(self.config) as api_client:
            categories_api = ynab.CategoriesApi(api_client)
            categories_response = categories_api.get_categories(str(self.plan_id))
            return categories_response.data.to_dict()

    @staticmethod
    def _set_default_plan(config: ynab.Configuration):
        plan_id: UUID | None
        plan_id_str = os.getenv("YNAB_PLAN_ID")
        if plan_id_str is not None:
            return UUID(plan_id_str)
        else:
            with ynab.ApiClient(config) as api_client:
                plans_api = ynab.PlansApi(api_client)
                plans_response = plans_api.get_plans()
                plan_id = YnabService._find_latest_plan(plans_response)
                if plan_id is None:
                    raise ValueError("There are no budgets for this YNAB user.")
                else:
                    return plan_id
            return

    @staticmethod
    def _find_latest_plan(plans: ynab.PlanSummaryResponse) -> UUID | None:
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
