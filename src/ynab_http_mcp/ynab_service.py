import os
import ynab
from uuid import UUID
from datetime import datetime
from ynab_http_mcp.debug import debug_exception, debug_ynab_response, debug_string
from typing import Any, Optional, Callable, TypeVar, cast
from functools import wraps

T = TypeVar("T")





class YnabService:
    def __init__(self):
        self.config = ynab.Configuration(access_token=os.getenv("YNAB_API_KEY"))
        self.plan_id = YnabService._set_default_plan(self.config)

    def _call_api(self, api_cls, fn: Callable):
        with ynab.ApiClient(self.config) as api_client:
            api = api_cls(api_client)
            resp = fn(api)
            debug_ynab_response(f"Response from {fn.__name__}", resp)
            return resp

    def list_plans(self) -> ynab.PlanSummaryResponse:
        return self._call_api(ynab.PlansApi, lambda api: api.get_plans())

    def get_categories(self) -> ynab.CategoriesResponse:
        return self._call_api(
            ynab.CategoriesApi,
            lambda api: api.get_categories(str(self.plan_id)),
        )

    def get_plan_month(self, date: datetime | None = None) -> ynab.MonthDetail:
        """
        Returns the plan for a specific month.
        If no date is passed, returns the current month's plan.
        """
        if date:
            reformatted_date = date.replace(day=1).strftime(
                "%Y-%m-%d"
            )  # Hardcode the day to be the first of the month
        else:
            reformatted_date = "current"
        return self._call_api(
            ynab.MonthsApi,
            lambda api: api.get_plan_month(str(self.plan_id), reformatted_date),
        )

    def get_all_plan_months(self) -> ynab.MonthSummariesResponse:

        return self._call_api(
            ynab.MonthsApi,
            lambda api: api.get_plan_months(str(self.plan_id)),
        )

    def get_accounts(self) -> ynab.AccountsResponse:
        return self._call_api(
            ynab.AccountsApi, lambda api: api.get_accounts(str(self.plan_id))
        )

    def get_transactions(
        self,
        since_date: Optional[datetime],
        until_date: Optional[datetime],
        type: str,
        month: Optional[datetime] = None,
        payee_id: Optional[str] = None,
        category_id: Optional[str] = None,
        account_id: Optional[str] = None,
    ) -> ynab.TransactionsResponse:
        """
        Will always consider since, until, type as parameters.
        Will only consider one of month, payee_id, category_id, or account_id. Whoever is defined first.
        """
        # Build parameters dictionary
        params = {}

        # 1. Take all of since, until, and type parameters if they are not none
        if since_date is not None:
            params["since_date"] = since_date.strftime("%Y-%m-%d")
        if until_date is not None:
            params["until_date"] = until_date.strftime("%Y-%m-%d")
        if type is not None:
            params["type"] = type

        # 2. Take the first of month, payee_id, category_id, or account_id that is not none
        if month is not None:
            params["month"] = month.replace(day=1).strftime("%Y-%m-%d")
            return self._call_api(
                ynab.TransactionsApi,
                lambda api: api.get_transactions_by_month(str(self.plan_id), **params),
            )
        elif payee_id is not None:
            params["payee_id"] = payee_id
            return self._call_api(
                ynab.TransactionsApi,
                lambda api: api.get_transactions_by_payee(str(self.plan_id), **params),
            )

        elif category_id is not None:
            params["category_id"] = category_id
            return self._call_api(
                ynab.TransactionsApi,
                lambda api: api.get_transactions_by_category(
                    str(self.plan_id), **params
                ),
            )
        elif account_id is not None:
            params["account_id"] = account_id
            return self._call_api(
                ynab.TransactionsApi,
                lambda api: api.get_transactions_by_account(str(self.plan_id), **params),
            )
        else:
            return self._call_api(
                ynab.TransactionsApi,
                lambda api: api.get_transactions(str(self.plan_id), **params),
            )

    def get_transaction(self, id: str) -> ynab.TransactionResponse:

        return self._call_api(
            ynab.TransactionsApi,
            lambda api: api.get_transaction_by_id(str(self.plan_id), id),
        )

    def get_payees(self) -> ynab.PayeesResponse:

        return self._call_api(
            ynab.PayeesApi,
            lambda api: api.get_payees(str(self.plan_id)),
        )

    def get_payee(self, id: str) -> ynab.PayeeResponse:

        return self._call_api(
            ynab.PayeesApi,
            lambda api: api.get_payee_by_id(str(self.plan_id), id),
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
