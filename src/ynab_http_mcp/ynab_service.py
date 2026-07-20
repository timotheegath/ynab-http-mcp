import os
import ynab
from uuid import UUID
from datetime import datetime
from ynab_http_mcp.debug import debug_exception, debug_ynab_response
from typing import Optional, Callable, TypeVar, Dict, Any

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

    def get_category(self, id: str) -> ynab.CategoryResponse:
        return self._call_api(
            ynab.CategoriesApi,
            lambda api: api.get_category_by_id(str(self.plan_id), id),
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
        # Validate category_id
        if not category_id or not isinstance(category_id, str):
            raise ValueError("category_id must be a non-empty string")

        # Validate and convert month_date
        if isinstance(month_date, str):
            try:
                # Handle both 'YYYY-MM' and 'YYYY-MM-DD' formats
                if len(month_date) == 7 and month_date[4] == "-":  # YYYY-MM format
                    # Append '-01' to make it a valid date string
                    month_date = datetime.fromisoformat(month_date + "-01")
                else:
                    # Full date format YYYY-MM-DD
                    month_date = datetime.fromisoformat(month_date)
            except ValueError as e:
                raise ValueError(
                    f"Invalid month_date format: {str(e)}. Expected 'YYYY-MM' or 'YYYY-MM-DD' format"
                ) from e
        elif not isinstance(month_date, datetime):
            raise ValueError(
                "month_date must be a datetime object or ISO format string ('YYYY-MM' or 'YYYY-MM-DD')"
            )

        try:
            # Format month as YYYY-MM-DD with day=01 (YNAB API expects full date format)
            month_str = month_date.replace(day=1).strftime("%Y-%m-%d")
            return self._call_api(
                ynab.CategoriesApi,
                lambda api: api.get_month_category_by_id(
                    str(self.plan_id), month_str, category_id
                ),
            )
        except Exception as e:
            debug_exception(f"Error fetching month category: {str(e)}")
            raise RuntimeError(
                f"Failed to retrieve month category data: {str(e)}"
            ) from e

    def get_plan_month(self, date: datetime | str | None = None) -> ynab.MonthDetailResponse:
        """
        Returns the plan for a specific month.
        If no date is passed, returns the current month's plan.
        """
        if date:
            if isinstance(date, str):
                try:
                    # Handle both 'YYYY-MM' and 'YYYY-MM-DD' formats
                    if len(date) == 7 and date[4] == "-":  # YYYY-MM format
                        # Append '-01' to make it a valid date string
                        date = datetime.fromisoformat(date + "-01")
                    else:
                        # Full date format YYYY-MM-DD
                        date = datetime.fromisoformat(date)
                except ValueError as e:
                    raise ValueError(f"Invalid date format: {str(e)}") from e
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
        Will only consider one of month, payee_id, category_id, or account_id. Whoever is defined first.

        Now includes validation logic to handle string dates and ensure proper filtering.
        """
        # Validate that at least one filter is provided
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
                "At least one filter parameter must be provided (since_date, until_date, type, month, payee_id, category_id, or account_id)"
            )

        # Convert string parameters to appropriate types with error handling
        try:
            converted_since_date = (
                (
                    datetime.fromisoformat(since_date)
                    if isinstance(since_date, str)
                    else since_date
                )
                if since_date
                else None
            )
            converted_until_date = (
                (
                    datetime.fromisoformat(until_date)
                    if isinstance(until_date, str)
                    else until_date
                )
                if until_date
                else None
            )
            converted_month = (
                (datetime.fromisoformat(month) if isinstance(month, str) else month)
                if month
                else None
            )
        except ValueError as e:
            raise ValueError(f"Invalid date format: {str(e)}")

        # Build parameters dictionary
        params = {}

        # 1. Take all of since, until, and type parameters if they are not none
        if converted_since_date is not None:
            params["since_date"] = converted_since_date.strftime("%Y-%m-%d")
        if converted_until_date is not None:
            params["until_date"] = converted_until_date.strftime("%Y-%m-%d")
        if type is not None:
            params["type"] = type

        # 2. Take the first of month, payee_id, category_id, or account_id that is not none
        if converted_month is not None:
            params["month"] = converted_month.replace(day=1).strftime("%Y-%m-%d")
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
        Updates a category's budgeted amount or balance for a specific month.

        Args:
            month_date: datetime object or ISO format string representing the month.
                       Accepts both 'YYYY-MM-DD' and 'YYYY-MM' formats. Day is ignored.
            category_id: ID of the category to update
            budgeted_amount: New budgeted amount in milliunits (optional)
            balance_adjustment: Amount to adjust balance by in milliunits (optional)

        Returns:
            CategoryResponse containing the updated category data

        Raises:
            ValueError: If inputs are invalid
            RuntimeError: If there are issues with the YNAB API call
        """
        # Validate inputs
        if not category_id or not isinstance(category_id, str):
            raise ValueError("category_id must be a non-empty string")

        if budgeted_amount is None and balance_adjustment is None:
            raise ValueError(
                "At least one of budgeted_amount or balance_adjustment must be provided"
            )

        # Validate and convert month_date
        if isinstance(month_date, str):
            try:
                # Handle both 'YYYY-MM' and 'YYYY-MM-DD' formats
                if len(month_date) == 7 and month_date[4] == "-":  # YYYY-MM format
                    # Append '-01' to make it a valid date string
                    month_date = datetime.fromisoformat(month_date + "-01")
                else:
                    # Full date format YYYY-MM-DD
                    month_date = datetime.fromisoformat(month_date)
            except ValueError as e:
                raise ValueError(
                    f"Invalid month_date format: {str(e)}. Expected 'YYYY-MM' or 'YYYY-MM-DD' format"
                ) from e
        elif not isinstance(month_date, datetime):
            raise ValueError(
                "month_date must be a datetime object or ISO format string ('YYYY-MM' or 'YYYY-MM-DD')"
            )

        # Build the update payload
        payload = {}
        if budgeted_amount is not None:
            payload["budgeted"] = budgeted_amount

        try:
            # Format month as YYYY-MM-DD with day=01 (YNAB API expects full date format)
            month_str = month_date.replace(day=1).strftime("%Y-%m-%d")

            # Get current category data to calculate new balance if needed
            current_category = self.get_month_category(month_date, category_id)
            current_balance = current_category.data.category.balance

            if balance_adjustment is not None:
                # Calculate new balance
                new_balance = current_balance + balance_adjustment
                # For balance adjustments, we need to create a transaction
                # This is a simplified approach - real implementation would need proper transaction handling
                payload["balance"] = new_balance

            return self._call_api(
                ynab.CategoriesApi,
                lambda api: api.update_month_category(
                    str(self.plan_id), month_str, category_id, payload
                ),
            )
        except Exception as e:
            debug_exception(f"Error updating month category: {str(e)}")
            raise RuntimeError(f"Failed to update month category data: {str(e)}") from e

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
        # Validate inputs
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

        # Validate and convert date
        if isinstance(date, str):
            try:
                date = datetime.fromisoformat(date)
            except ValueError as e:
                raise ValueError(f"Invalid date format: {str(e)}") from e
        elif not isinstance(date, datetime):
            raise ValueError("date must be a datetime object or ISO format string")

        # Build transaction payload
        transaction_data = {
            "transaction": {
                "account_id": account_id,
                "date": date.strftime("%Y-%m-%d"),
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

    def validate_write_operation(self, operation_type: str, **kwargs) -> Dict[str, Any]:
        """
        Validates write operation parameters and returns normalized data.

        Args:
            operation_type: Type of write operation (e.g., 'update_category', 'create_transaction')
            **kwargs: Operation-specific parameters

        Returns:
            Dict containing validated and normalized parameters

        Raises:
            ValueError: If validation fails
        """
        validated_data : Dict[str, Any]= {}

        if operation_type == "update_category":
            # Validate month_date
            month_date = kwargs.get("month_date")
            if not month_date:
                raise ValueError("month_date is required for update_category")

            if isinstance(month_date, str):
                try:
                    if len(month_date) == 7 and month_date[4] == "-":  # YYYY-MM format
                        validated_data["month_date"] = datetime.fromisoformat(
                            month_date + "-01"
                        )
                    else:
                        validated_data["month_date"] = datetime.fromisoformat(
                            month_date
                        )
                except ValueError as e:
                    raise ValueError(f"Invalid month_date format: {str(e)}") from e
            elif isinstance(month_date, datetime):
                validated_data["month_date"] = month_date
            else:
                raise ValueError(
                    "month_date must be a datetime object or ISO format string"
                )

            # Validate category_id
            category_id = kwargs.get("category_id")
            if not category_id or not isinstance(category_id, str):
                raise ValueError("category_id must be a non-empty string")
            validated_data["category_id"] = category_id

            # Validate budgeted_amount or balance_adjustment
            budgeted_amount = kwargs.get("budgeted_amount")
            balance_adjustment = kwargs.get("balance_adjustment")

            if budgeted_amount is None and balance_adjustment is None:
                raise ValueError(
                    "At least one of budgeted_amount or balance_adjustment must be provided"
                )

            if budgeted_amount is not None:
                if not isinstance(budgeted_amount, int):
                    raise ValueError("budgeted_amount must be an integer")
                validated_data["budgeted_amount"] = budgeted_amount

            if balance_adjustment is not None:
                if not isinstance(balance_adjustment, int):
                    raise ValueError("balance_adjustment must be an integer")
                validated_data["balance_adjustment"] = balance_adjustment

        elif operation_type == "create_transaction":
            # Validate account_id
            account_id = kwargs.get("account_id")
            if not account_id or not isinstance(account_id, str):
                raise ValueError("account_id must be a non-empty string")
            validated_data["account_id"] = account_id

            # Validate date
            date = kwargs.get("date")
            if not date:
                raise ValueError("date is required for create_transaction")

            if isinstance(date, str):
                try:
                    validated_data["date"] = datetime.fromisoformat(date)
                except ValueError as e:
                    raise ValueError(f"Invalid date format: {str(e)}") from e
            elif isinstance(date, datetime):
                validated_data["date"] = date
            else:
                raise ValueError("date must be a datetime object or ISO format string")

            # Validate amount
            amount = kwargs.get("amount")
            if not isinstance(amount, int):
                raise ValueError("amount must be an integer")
            if amount == 0:
                raise ValueError("amount cannot be zero")
            validated_data["amount"] = amount

            # Validate payee
            payee_id = kwargs.get("payee_id")
            payee_name = kwargs.get("payee_name")

            if not payee_id and not payee_name:
                raise ValueError("Either payee_id or payee_name must be provided")

            if payee_id:
                if not isinstance(payee_id, str):
                    raise ValueError("payee_id must be a string")
                validated_data["payee_id"] = payee_id
            else:
                if not isinstance(payee_name, str):
                    raise ValueError("payee_name must be a string")
                validated_data["payee_name"] = payee_name

            # Validate optional fields
            category_id = kwargs.get("category_id")
            if category_id:
                if not isinstance(category_id, str):
                    raise ValueError("category_id must be a string")
                validated_data["category_id"] = category_id

            memo = kwargs.get("memo")
            if memo:
                if not isinstance(memo, str):
                    raise ValueError("memo must be a string")
                validated_data["memo"] = memo

            cleared = kwargs.get("cleared", "cleared")
            if cleared not in ["cleared", "uncleared", "reconciled"]:
                raise ValueError(
                    "cleared must be one of: cleared, uncleared, reconciled"
                )
            validated_data["cleared"] = cleared

            approved = kwargs.get("approved", True)
            if not isinstance(approved, bool):
                raise ValueError("approved must be a boolean")
            validated_data["approved"] = approved

            flag_color = kwargs.get("flag_color")
            if flag_color:
                if flag_color not in [
                    "red",
                    "orange",
                    "yellow",
                    "green",
                    "blue",
                    "purple",
                ]:
                    raise ValueError(
                        "flag_color must be one of: red, orange, yellow, green, blue, purple"
                    )
                validated_data["flag_color"] = flag_color

        else:
            raise ValueError(f"Unknown operation_type: {operation_type}")

        return validated_data

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
