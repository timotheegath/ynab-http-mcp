# All transaction actions.
from ynab_http_mcp.ynab_service import YnabService
from typing import Any, Annotated
from datetime import datetime
from ynab_http_mcp.debug import debug_exception, debug_string
from ynab_http_mcp.schemas.transactions import CleanTransaction, TransactionsResponse
from ynab_http_mcp.schemas.base import validate_and_clean_data, filter_import_fields
from ynab_http_mcp.utils.schema_utils import transform_schema
import os


def register(mcp, ynab_service: YnabService):

    @mcp.tool(
        annotations={
            "title": "Get transactions with flexible filtering.",
            "destructiveHint": False,
            "readOnlyHint": True,
            "idempotentHint": True,
            "returnSchema": transform_schema(TransactionsResponse.model_json_schema()),
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
        converted_since_date = (
            datetime.fromisoformat(since_date) if since_date else None
        )
        converted_until_date = (
            datetime.fromisoformat(until_date) if until_date else None
        )
        converted_month = datetime.fromisoformat(month) if month else None

        # Get raw YNAB response
        raw_response = ynab_service.get_transactions(
            since_date=converted_since_date,
            until_date=converted_until_date,
            type=type,
            account_id=account_id,
            month=converted_month,
            payee_id=payee_id,
            category_id=category_id,
        )
        
        # Convert to dict and filter import fields
        raw_data = raw_response.to_dict()
        
        # Clean each transaction by filtering import fields
        cleaned_transactions = []
        for transaction_data in raw_data.get('data', {}).get('transactions', []):
            # Filter out import-related fields
            filtered_data = filter_import_fields(transaction_data)
            
            # Validate and clean using schema
            try:
                cleaned_transaction = validate_and_clean_data(
                    CleanTransaction,
                    filtered_data,
                    debug_mode=os.getenv('DEBUG_MODE', 'false').lower() in ('true', '1', 'yes')
                )
                cleaned_transactions.append(cleaned_transaction.model_dump())
            except Exception as e:
                debug_exception(f"Failed to validate transaction {transaction_data.get('id', 'unknown')}")
                # Skip invalid transactions but continue processing others
                continue
        
        # Create final response with schema validation
        final_response = {
            'transactions': cleaned_transactions,
            'server_knowledge': raw_data.get('data', {}).get('server_knowledge', 0)
        }
        
        # Validate the complete response structure
        validated_response = validate_and_clean_data(
            TransactionsResponse,
            final_response,
            debug_mode=os.getenv('DEBUG_MODE', 'false').lower() in ('true', '1', 'yes')
        )
        
        return validated_response.model_dump()
