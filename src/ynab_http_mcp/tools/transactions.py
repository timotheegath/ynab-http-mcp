# All transaction actions.
from ynab_http_mcp.ynab_service import YnabService
from typing import Annotated
from datetime import datetime
from ynab_http_mcp.debug import debug_exception
from ynab_http_mcp.schemas.transactions import CleanTransaction, TransactionsResponse
from ynab_http_mcp.utils.schema_utils import clean_ynab_data
from ynab_http_mcp.utils.simple_validation import simple_validate
import json


def register(mcp, ynab_service: YnabService):

    @mcp.resource(
        uri="data://transactions{?since_date,until_date,type,account_id,payee_id,category_id,limit,month}",
        mime_type="application/json"
    )
    async def get_transactions_resource(
         since_date: Annotated[
            str | None,
            "ISO-format date (YYYY-MM-DD) to filter transactions starting from this date. Leave blank for no start date filter.",
        ] = None,
        until_date: Annotated[
            str | None,
            "ISO-format date (YYYY-MM-DD) to filter transactions up to this date. Leave blank for no end date filter.",
        ] = None,
        type: Annotated[
            str | None,
            "Transaction type filter. Common values: 'uncleared', 'cleared', 'reconciled'.",
        ] = "all",
        account_id: Annotated[
            str | None,
            "Account ID to filter transactions by specific account. Takes precedence over month, payee, and category filters.",
        ] = None,
        payee_id: Annotated[
            str | None,
            "Payee ID to filter transactions by specific payee.",
        ] = None,
        category_id: Annotated[
            str | None,
            "Category ID to filter transactions by specific category.",
        ] = None,
        limit: Annotated[
            int | None,
            "Maximum number of transactions to return. Leave blank for no limit.",
        ] = None,
        month: Annotated[
            str | None,
            "Filter by month (YYYY-MM). Takes precedence over other filters when specified.",
        ] = None,
    ) -> str:
        """
        Get transactions with flexible filtering options as a resource.

        Filtering is specified via filter_params in the format:
        since_date=YYYY-MM-DD&until_date=YYYY-MM-DD&type=cleared&account_id=XXX

        Examples:
        - data://transactions/since_date=2024-01-01&until_date=2024-01-31
        - data://transactions/type=cleared&account_id=XYZ
        """
        # Parse filter parameters from the path
        

        # Implement mandatory filter validation
        if not any([since_date, until_date, type and type != "all"]):
            error_response = {
                "error": "At least one of 'since_date', 'until_date', or 'type' (non-'all') filters must be provided"
            }
        

        # Convert string parameters to appropriate types with error handling
        try:
            converted_since_date = (
                datetime.fromisoformat(since_date) if since_date else None
            )
            converted_until_date = (
                datetime.fromisoformat(until_date) if until_date else None
            )
            converted_month = datetime.fromisoformat(month) if month else None
            if limit:
                int(limit)  # Validate limit format
        except ValueError as e:
            error_response = {
                "error": f"Invalid parameter format: {str(e)}"
            }
            return json.dumps(error_response)

        # Get raw YNAB response
        raw_response = ynab_service.get_transactions(
            since_date=converted_since_date,
            until_date=converted_until_date,
            type=type if type else "all",
            account_id=account_id,
            month=converted_month,
            payee_id=payee_id,
            category_id=category_id,
        )

        # Convert to dict and clean data using unified function
        raw_data = raw_response.to_dict()

        # Clean each transaction using unified data cleaning
        cleaned_transactions = []
        for transaction_data in raw_data.get("data", {}).get("transactions", []):
            # Clean data using unified function (handles UUID→string, import field filtering, etc.)
            cleaned_data = clean_ynab_data(transaction_data)

            # Validate using simplified approach
            try:
                validated_transaction = simple_validate(cleaned_data, CleanTransaction)
                cleaned_transactions.append(validated_transaction.model_dump())
            except Exception:
                debug_exception(
                    f"Failed to validate transaction {transaction_data.get('id', 'unknown')}"
                )
                # Skip invalid transactions but continue processing others
                continue

        # Create final response with contextual hints extracted from schema
        hints = {}
        for field_name, field_info in CleanTransaction.model_fields.items():
            if field_info.description and any(keyword in field_info.description for keyword in ['transfer', 'matched', 'flag', 'debt', 'amount', 'cleared']):
                hints[field_name] = field_info.description
        
        final_response = {
            "transactions": cleaned_transactions,
            "server_knowledge": raw_data.get("data", {}).get("server_knowledge", 0),
            "_hints": hints
        }

        # Validate the complete response structure using simplified approach
        validated_response = simple_validate(final_response, TransactionsResponse)

        # Return as JSON string for MCP resource compatibility
        return json.dumps(validated_response.model_dump())

    
