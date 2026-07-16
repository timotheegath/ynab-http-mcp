import os
import ynab
from uuid import UUID
from datetime import datetime
from ynab_http_mcp.debug import debug_exception, debug_string
from typing import Any

class YnabService:
    def __init__(self):
        self.config = ynab.Configuration(access_token=os.getenv("YNAB_API_KEY"))
        self.plan_id = YnabService._set_default_plan(self.config)

    def _call_api(self, api_cls, fn):
        with ynab.ApiClient(self.config) as api_client:
            api = api_cls(api_client)
            return fn(api)
        
    def list_plans(self) -> ynab.PlanSummaryResponse:

        return self._call_api(ynab.PlansApi, lambda api: api.get_plans())


    def get_categories(self) -> ynab.CategoriesResponse:
        return self._call_api(
            ynab.CategoriesApi,
            lambda api: api.get_categories(str(self.plan_id)),
        )
        
    def get_plan_month(self, date : datetime | None = None) -> ynab.MonthDetail:
        """
        Returns the plan for a specific month. 
        If no date is passed, returns the current month's plan.
        """
        
        if date:
            reformatted_date = str(date.date())
            debug_string("reformatted_date", reformatted_date)
            return self._call_api(
                ynab.MonthsApi,
                lambda api: api.get_plan_month(str(self.plan_id), reformatted_date)
            )
        else:
            return self._call_api(
                ynab.MonthsApi,
                lambda api: api.get_plan_month(str(self.plan_id), "current")
            )
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
    
    @staticmethod
    def _handle_api_output(resp) -> dict[str, Any]:

        if not hasattr(resp, "to_dict"):
            debug_exception("YnabService API returned a response with no to_dict() method")
            raise AttributeError("Cannot convert YNAB API response to dict")
         
        return resp.to_dict()
        

