# All transaction actions.
from ynab_http_mcp.ynab_service import YnabService
import ynab
from typing import Any, Annotated
from datetime import datetime
from ynab_http_mcp.debug import debug_exception, debug_string


def register(mcp, ynab_service: YnabService):
    
    @mcp.tool(
            annotations={
                "title":"Get transactions with flexible filtering.",
                "destructiveHint":False,
                "readOnlyHint": True,
                "idempotentHint":True
            }
    )
    async def get_transactions(
        since_date: Annotated[
            str | None,
            "ISO-format date (YYYY-MM-DD) to filter transactions starting from this date. Leave blank for no start date filter.",
        ] = None,
        until_date: Annotated[
            str | None,
            "ISO-format date (YYYY-MM-DD) to filter transactions up to this date. Leave blank for no end date filter.",
        ] = None,
        type: Annotated[
            str,
            "Transaction type filter. Common values: 'uncleared', 'cleared', 'reconciled'.",
        ] = "all",
        account_id: Annotated[
            str | None,
            "Account ID to filter transactions by specific account. Takes precedence over month, payee, and category filters.",
        ] = None,
        month: Annotated[
            str | None,
            "ISO-format date (YYYY-MM-DD) to filter transactions by month. Only used if account_id is not provided.",
        ] = None,
        payee_id: Annotated[
            str | None,
            "Payee ID to filter transactions by specific payee. Only used if account_id and month are not provided.",
        ] = None,
        category_id: Annotated[
            str | None,
            "Category ID to filter transactions by specific category. Only used if account_id, month, and payee_id are not provided.",
        ] = None,
    ) -> dict[str, Any]:
        """
        Get transactions with flexible filtering options.
        
        Filtering Rules:
        - since_date, until_date, and type are always applied when provided
        - Only ONE of account_id, month, payee_id, or category_id is used (in that priority order)
        - If none of the scope filters (account_id, month, payee_id, category_id) are provided, returns all transactions matching the date/type filters
        
        Examples:
        - All transactions in January 2024: month="2024-01-15"
        - Cleared transactions from account XYZ: account_id="XYZ", type="cleared"
        - Transactions from Jan 1 to Jan 31, 2024: since_date="2024-01-01", until_date="2024-01-31"
        """
        # Convert string parameters to appropriate types
        converted_since_date = datetime.fromisoformat(since_date) if since_date else None
        converted_until_date = datetime.fromisoformat(until_date) if until_date else None
        converted_month = datetime.fromisoformat(month) if month else None

        return ynab_service.get_transactions(
            since_date=converted_since_date,
            until_date=converted_until_date,
            type=type,
            account_id=account_id,
            month=converted_month,
            payee_id=payee_id,
            category_id=category_id
        ).to_dict()


