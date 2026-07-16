import os
import ynab
from uuid import UUID
from datetime import datetime
from ynab_http_mcp.debug import debug_exception, debug_ynab_response, debug_string
from typing import Any, Optional, Callable, TypeVar, cast
from functools import wraps

T = TypeVar("T")


def handle_ynab_errors(expected_404=False, return_none_on_404=False):
    """
    Decorator to handle YNAB API errors with flexible 404 handling.

    This decorator provides a scalable way to handle different types of 404 responses
    from the YNAB Python SDK across multiple service methods.

    Args:
        expected_404 (bool): If True, treats 404 as expected behavior and handles gracefully.
                            If False, re-raises 404 exceptions as errors.
        return_none_on_404 (bool): If True, returns None on 404 (when expected_404=True).
                                 If False, returns empty response object of the expected type.

    Usage Examples:
        # Case 1: 404 is an error - re-raise exception
        @handle_ynab_errors(expected_404=False)
        def get_required_resource(self) -> ResourceResponse:
            return self._call_api(...)

        # Case 2: 404 is expected - return None
        @handle_ynab_errors(expected_404=True, return_none_on_404=True)
        def get_optional_resource(self) -> Optional[ResourceResponse]:
            return self._call_api(...)

        # Case 3: 404 is expected - return empty object
        @handle_ynab_errors(expected_404=True)
        def get_resource_with_fallback(self) -> ResourceResponse:
            return self._call_api(...)

    Behavior:
        - Catches ynab.ApiException instances
        - For 404 errors: follows expected_404 and return_none_on_404 configuration
        - For other HTTP errors: always re-raises the exception
        - Provides debug logging for all handled exceptions
    """

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        def wrapper(*args, **kwargs) -> T:
            try:
                return func(*args, **kwargs)
            except ynab.ApiException as e:
                if e.status == 404:
                    if expected_404:
                        debug_string(f"Expected 404 for {func.__name__}", str(e))
                        if return_none_on_404:
                            return cast(T, None)
                        else:
                            # Return empty object of the expected type
                            return YnabService._create_empty_response(
                                func.__annotations__.get("return", None)
                            )
                    else:
                        debug_exception(f"Unexpected 404 error in {func.__name__}")
                        raise
                else:
                    debug_exception(f"YNAB API error in {func.__name__}")
                    raise

        return wrapper

    return decorator


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
            reformatted_date = date.replace(day=1).strftime('%Y-%m-%d')# Hardcode the day to be the first of the month
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

    def get_transactions(
            self,
            since_date: Optional[datetime],
            until_date: Optional[datetime], 
            type: str,
            account_id: Optional[str],
            month: Optional[datetime],
            payee_id: Optional[str],
            category_id: Optional[str]) -> ynab.TransactionsResponse:
        """
        Will always consider since, until, type as parameters.
        Will only consider one of account_id, month, payee_id, category_id. Whoever is defined first.
        """
        # Build parameters dictionary
        params = {}
        
        # 1. Take all of since, until, and type parameters if they are not none
        if since_date is not None:
            params["since_date"] = since_date.strftime('%Y-%m-%d')
        if until_date is not None:
            params["until_date"] = until_date.strftime('%Y-%m-%d')
        if type is not None:
            params["type"] = type
        
        # 2. Take the first of account_id, month, payee_id or category_id that is not none
        if account_id is not None:
            params["account_id"] = account_id
            return self._call_api(
                ynab.TransactionsApi,
                lambda api: api.get_transactions_by_account(str(self.plan_id), **params),
            )
        elif month is not None:
            params["month"] = month.replace(day=1).strftime('%Y-%m-%d')
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
                lambda api: api.get_transactions_by_category(str(self.plan_id), **params),
            )
        else:

            return self._call_api(
                ynab.TransactionsApi,
                lambda api: api.get_transactions(str(self.plan_id), **params),
            )



    @staticmethod
    def _create_empty_response(response_type) -> Any:
        """
        Creates an empty response object of the given type.
        For YNAB SDK types, this typically means creating an instance with empty data.
        """
        if response_type is None or not hasattr(response_type, "__new__"):
            return None

        try:
            # Try to create an empty instance
            empty_instance = response_type.__new__(response_type)
            # For YNAB response types, set data to None or empty
            if hasattr(empty_instance, "data"):
                empty_instance.data = None
            return empty_instance
        except Exception:
            # Fallback to None if we can't create empty instance
            return None

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
            debug_exception(
                "YnabService API returned a response with no to_dict() method"
            )
            raise AttributeError("Cannot convert YNAB API response to dict")

        return resp.to_dict()
