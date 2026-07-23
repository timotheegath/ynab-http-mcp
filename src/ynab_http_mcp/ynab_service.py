import os
import ynab
from uuid import UUID
from datetime import datetime
from ynab_http_mcp.debug import debug_exception, debug_ynab_response
from typing import Optional, Callable, TypeVar
from ynab_http_mcp.schemas.budget_tools import UpdateCategoryRequest
from ynab_http_mcp.utils.dates import parse_month_date, parse_date, month_str

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

    def get_category(self, id: UUID) -> ynab.CategoryResponse:
        return self._call_api(
            ynab.CategoriesApi,
            lambda api: api.get_category_by_id(str(self.plan_id), str(id)),
        )

    def get_month_category(
        self, month_date: datetime | str, category_id: str
    ) -> ynab.CategoryResponse:
        """
        Returns a specific category's data for a given month.

        Args:
            month_date: datetime object or ISO format string representing the month.
                       Accepts both 'YYYY-MM-DD' and 'YYYY-MM' formats. Day is ignored.
                       Examples: '2025-12-01', '2025-12-15', or '2025-12'
            category_id: ID of the category to retrieve

        Returns:
            CategoryResponse containing the category data for the specified month

        Raises:
            ValueError: If category_id is empty or invalid, or if month_date format is invalid
            RuntimeError: If there are issues with the YNAB API call
        """
        if not category_id or not isinstance(category_id, str):
            raise ValueError("category_id must be a non-empty string")

        try:
            month_str_val = month_str(parse_month_date(month_date))
            return self._call_api(
                ynab.CategoriesApi,
                lambda api: api.get_month_category_by_id(
                    str(self.plan_id), month_str_val, category_id
                ),
            )
        except ValueError:
            raise
        except Exception as e:
            debug_exception(f"Error fetching month category: {str(e)}")
            raise RuntimeError(
                f"Failed to retrieve month category data: {str(e)}"
            ) from e

    def get_plan_month(
        self, date: datetime | str | None = None
    ) -> ynab.MonthDetailResponse:
        """
        Returns the plan for a specific month.
        If no date is passed, returns the current month's plan.
        """
        if date:
            reformatted_date = month_str(parse_month_date(date))
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

    def get_account(self, id: UUID) -> ynab.AccountResponse:
        return self._call_api(
            ynab.AccountsApi,
            lambda api: api.get_account_by_id(str(self.plan_id), account_id=id),
        )

    def get_transactions(
        self,
        since_date: Optional[datetime | str],
        until_date: Optional[datetime | str],
        type: str,
        month: Optional[datetime | str] = None,
        payee_id: Optional[str] = None,
        category_id: Optional[str] = None,
        account_id: Optional[str] = None,
    ) -> ynab.TransactionsResponse:
        """
        Will always consider since, until, type as parameters.
        Will only consider one of month, payee_id, category_id, or account_id.
        Whoever is defined first takes priority.

        Raises:
            ValueError: If no filter is provided or a date string is invalid.
        """
        if not any(
            [
                since_date,
                until_date,
                type and type != "all",
                month,
                payee_id,
                category_id,
                account_id,
            ]
        ):
            raise ValueError(
                "At least one filter parameter must be provided (since_date, "
                "until_date, type, month, payee_id, category_id, or account_id)"
            )

        converted_since_date = parse_date(since_date) if since_date else None
        converted_until_date = parse_date(until_date) if until_date else None
        converted_month = parse_month_date(month) if month else None

        params = {}
        if converted_since_date is not None:
            params["since_date"] = converted_since_date.strftime("%Y-%m-%d")
        if converted_until_date is not None:
            params["until_date"] = converted_until_date.strftime("%Y-%m-%d")
        if type is not None:
            params["type"] = type

        if converted_month is not None:
            params["month"] = month_str(converted_month)
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
                lambda api: api.get_transactions_by_account(
                    str(self.plan_id), **params
                ),
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

    def update_month_category(
        self,
        month_date: datetime | str,
        category_id: str,
        budgeted_amount: int | None = None,
        balance_adjustment: int | None = None,
    ) -> ynab.CategoryResponse:
        """
        Updates a category's budgeted amount for a specific month.

        Args:
            month_date: datetime object or ISO format string representing the month.
                       Accepts both 'YYYY-MM-DD' and 'YYYY-MM' formats. Day is ignored.
            category_id: ID of the category to update
            budgeted_amount: New budgeted amount in milliunits (optional)
            balance_adjustment: Not currently implemented — pass budgeted_amount instead.

        Returns:
            CategoryResponse containing the updated category data

        Raises:
            ValueError: If inputs are invalid
            NotImplementedError: If balance_adjustment is used
            RuntimeError: If there are issues with the YNAB API call
        """
        if not category_id or not isinstance(category_id, str):
            raise ValueError("category_id must be a non-empty string")

        if budgeted_amount is None and balance_adjustment is None:
            raise ValueError(
                "At least one of budgeted_amount or balance_adjustment must be provided"
            )

        if balance_adjustment is not None:
            raise NotImplementedError(
                "balance_adjustment is not supported by the YNAB API directly. "
                "Create a transaction instead to adjust a category balance."
            )

        try:
            month_str_val = month_str(parse_month_date(month_date))
            payload = {"category": {"budgeted": budgeted_amount}}
            return self._call_api(
                ynab.CategoriesApi,
                lambda api: api.update_month_category(
                    str(self.plan_id), month_str_val, category_id, payload
                ),
            )
        except (ValueError, NotImplementedError):
            raise
        except Exception as e:
            debug_exception(f"Error updating month category: {str(e)}")
            raise RuntimeError(f"Failed to update month category data: {str(e)}") from e

    def assign_money(
        self, month_date: datetime | str, category_id: str, assigned_money: int
    ) -> ynab.SaveCategoryResponse:
        """
        Assigns an amount (in milliunits) to a category for a given month.

        Args:
            month_date: datetime or ISO string ('YYYY-MM' or 'YYYY-MM-DD')
            category_id: ID of the category
            assigned_money: Amount to assign in milliunits
        """
        if not category_id or not isinstance(category_id, str):
            raise ValueError("category_id must be a non-empty string")

        try:
            month_str_val = month_str(parse_month_date(month_date))
            payload = {"category": {"budgeted": assigned_money}}
            return self._call_api(
                ynab.CategoriesApi,
                lambda api: api.update_month_category(
                    str(self.plan_id), month_str_val, category_id, payload
                ),
            )
        except ValueError:
            raise
        except Exception as e:
            debug_exception(f"Error assigning money to month category: {str(e)}")
            raise RuntimeError(
                f"Failed to assign money to month category: {str(e)}"
            ) from e

    def update_category(
        self,
        request: UpdateCategoryRequest,
    ) -> ynab.SaveCategoryResponse:
        """
        Updates a category in YNAB with comprehensive goal settings.

        Args:
            request: UpdateCategoryRequest with all optional category/goal fields.

        Returns:
            SaveCategoryResponse containing the updated category data

        Raises:
            ValueError: If inputs are invalid
            RuntimeError: If there are issues with the YNAB API call
        """
        if not request.category_id or not isinstance(request.category_id, str):
            raise ValueError("category_id must be a non-empty string")

        # Detect clear-goal: goal_target=0 with no other goal fields present.
        # This combination signals that the caller wants to fully remove the
        # goal, not just zero the target.
        is_clearing = (
            request.goal_target is not None
            and request.goal_target == 0
            and request.goal_target_date is None
            and request.goal_needs_whole_amount is None
            and request.goal_frequency is None
        )

        try:
            if is_clearing:
                # The SDK's ExistingCategory.to_dict() uses exclude_none=True,
                # which strips None values from serialization.  To send
                # explicit JSON null for every goal_* field (required by the
                # YNAB API to fully remove a goal) we build a raw dict instead.
                cat_dict: dict = {}
                if request.name is not None:
                    cat_dict["name"] = request.name
                if request.note is not None:
                    cat_dict["note"] = request.note
                if request.category_group_id is not None:
                    cat_dict["category_group_id"] = request.category_group_id
                # Goal-clearing fields — explicit nulls for every goal_* field
                cat_dict["goal_target"] = 0
                cat_dict["goal_target_date"] = None
                cat_dict["goal_needs_whole_amount"] = None
                cat_dict["goal_frequency"] = None

                return self._call_api(
                    ynab.CategoriesApi,
                    lambda api: api.update_category(
                        str(self.plan_id),
                        request.category_id,
                        {"category": cat_dict},
                    ),
                )

            update_payload = ynab.ExistingCategory()

            if request.name is not None:
                update_payload.name = request.name
            if request.note is not None:
                update_payload.note = request.note
            if request.category_group_id is not None:
                update_payload.category_group_id = UUID(request.category_group_id)
            if request.goal_target is not None:
                update_payload.goal_target = request.goal_target
            if request.goal_target_date is not None:
                update_payload.goal_target_date = parse_date(
                    request.goal_target_date
                ).date()
            if request.goal_needs_whole_amount is not None:
                update_payload.goal_needs_whole_amount = request.goal_needs_whole_amount
            if request.goal_frequency is not None:
                update_payload.goal_frequency = request.goal_frequency

            return self._call_api(
                ynab.CategoriesApi,
                lambda api: api.update_category(
                    str(self.plan_id),
                    request.category_id,
                    ynab.PatchCategoryWrapper(category=update_payload),
                ),
            )
        except Exception as e:
            debug_exception(f"Error updating category: {str(e)}")
            raise RuntimeError(f"Failed to update category: {str(e)}") from e

    def create_transaction(
        self,
        account_id: str,
        date: datetime | str,
        amount: int,
        payee_id: str | None = None,
        payee_name: str | None = None,
        category_id: str | None = None,
        memo: str | None = None,
        cleared: str = "cleared",
        approved: bool = True,
        flag_color: str | None = None,
    ) -> ynab.TransactionResponse:
        """
        Creates a new transaction in YNAB.

        Args:
            account_id: ID of the account for the transaction
            date: Transaction date as datetime or ISO format string
            amount: Transaction amount in milliunits (negative for outflow, positive for inflow)
            payee_id: Optional payee ID
            payee_name: Optional payee name (required if payee_id not provided)
            category_id: Optional category ID
            memo: Optional memo text
            cleared: Cleared status (cleared, uncleared, reconciled)
            approved: Whether transaction is approved
            flag_color: Optional flag color

        Returns:
            TransactionResponse containing the created transaction

        Raises:
            ValueError: If required inputs are missing or invalid
            RuntimeError: If there are issues with the YNAB API call
        """
        if not account_id or not isinstance(account_id, str):
            raise ValueError("account_id must be a non-empty string")
        if not isinstance(amount, int):
            raise ValueError("amount must be an integer (milliunits)")
        if amount == 0:
            raise ValueError("amount cannot be zero")
        if not payee_id and not payee_name:
            raise ValueError("Either payee_id or payee_name must be provided")
        if payee_id and not isinstance(payee_id, str):
            raise ValueError("payee_id must be a string if provided")
        if payee_name and not isinstance(payee_name, str):
            raise ValueError("payee_name must be a string if provided")
        if category_id and not isinstance(category_id, str):
            raise ValueError("category_id must be a string if provided")
        if memo and not isinstance(memo, str):
            raise ValueError("memo must be a string if provided")
        if cleared not in ["cleared", "uncleared", "reconciled"]:
            raise ValueError("cleared must be one of: cleared, uncleared, reconciled")
        if not isinstance(approved, bool):
            raise ValueError("approved must be a boolean")
        if flag_color and flag_color not in [
            "red",
            "orange",
            "yellow",
            "green",
            "blue",
            "purple",
            None,
        ]:
            raise ValueError(
                "flag_color must be one of: red, orange, yellow, green, blue, purple, or None"
            )

        parsed_date = parse_date(date)

        transaction_data = {
            "transaction": {
                "account_id": account_id,
                "date": parsed_date.strftime("%Y-%m-%d"),
                "amount": amount,
                "cleared": cleared,
                "approved": approved,
            }
        }

        if payee_id:
            transaction_data["transaction"]["payee_id"] = payee_id
        else:
            transaction_data["transaction"]["payee_name"] = payee_name
        if category_id:
            transaction_data["transaction"]["category_id"] = category_id
        if memo:
            transaction_data["transaction"]["memo"] = memo
        if flag_color:
            transaction_data["transaction"]["flag_color"] = flag_color

        try:
            return self._call_api(
                ynab.TransactionsApi,
                lambda api: api.create_transaction(str(self.plan_id), transaction_data),
            )
        except Exception as e:
            debug_exception(f"Error creating transaction: {str(e)}")
            raise RuntimeError(f"Failed to create transaction: {str(e)}") from e

    @staticmethod
    def _set_default_plan(config: ynab.Configuration):
        plan_id_str = os.getenv("YNAB_PLAN_ID")
        if plan_id_str is not None:
            return UUID(plan_id_str)
        with ynab.ApiClient(config) as api_client:
            plans_api = ynab.PlansApi(api_client)
            plans_response = plans_api.get_plans()
            plan_id = YnabService._find_latest_plan(plans_response)
            if plan_id is None:
                raise ValueError("There are no budgets for this YNAB user.")
            return plan_id

    @staticmethod
    def _find_latest_plan(plans: ynab.PlanSummaryResponse) -> UUID | None:
        """
        Amongst all of the user's plans, find the one that was modified the most recently.
        Returns its UUID.
        """
        if not plans or not plans.data.plans:
            return None

        plan_list = plans.data.plans
        plans_with_timestamps = [
            plan for plan in plan_list if plan.last_modified_on is not None
        ]

        if not plans_with_timestamps:
            return plan_list[0].id

        most_recent_plan = max(
            plans_with_timestamps,
            key=lambda plan: plan.last_modified_on or datetime.min,
        )
        return most_recent_plan.id
