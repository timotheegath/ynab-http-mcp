from ynab_http_mcp.ynab_service import YnabService
from ynab_http_mcp.schemas.accounts import AccountsResponse, CleanAccount
from ynab_http_mcp.schemas.transactions import CleanTransaction, TransactionsResponse
from ynab_http_mcp.utils.schema_utils import clean_ynab_data
from ynab_http_mcp.utils.schema_utils import simple_validate
from typing import Annotated, Literal
from datetime import datetime
from ynab_http_mcp.debug import debug_exception
import json


def register(mcp, ynab_service: YnabService):

    @mcp.resource(uri="data://accounts", mime_type="application/json")
    async def get_accounts() -> str:
        """Get a list of all YNAB accounts."""
        # Get raw YNAB response
        raw_response = ynab_service.get_accounts()

        # Convert to dict
        raw_data = raw_response.to_dict()

        # Clean and validate accounts using simplified approach
        cleaned_accounts = []

        for account_data in raw_data.get("data", {}).get("accounts", []):
            try:
                # Clean data using unified function
                cleaned_data = clean_ynab_data(account_data)

                # Validate using simplified approach
                validated_account = simple_validate(cleaned_data, CleanAccount)
                cleaned_accounts.append(validated_account.model_dump())
            except Exception:
                from ynab_http_mcp.debug import debug_exception

                debug_exception(
                    f"Failed to validate account {account_data.get('id', 'unknown')}"
                )
                continue

        # Create final response
        final_response = {"accounts": cleaned_accounts}

        # Validate complete response structure using simplified approach
        try:
            validated_response = simple_validate(final_response, AccountsResponse)
            # Return as JSON string for MCP resource compatibility
            return json.dumps(validated_response.model_dump())
        except Exception:
            from ynab_http_mcp.debug import debug_exception

            debug_exception("Failed to validate final accounts response")
            # Return a fallback response if validation fails
            # Convert dicts back to CleanAccount objects for type safety
            fallback_accounts = []
            for account_dict in cleaned_accounts:
                try:
                    fallback_accounts.append(CleanAccount(**account_dict))
                except Exception:
                    # If conversion fails, skip this account
                    continue

            fallback_response = AccountsResponse(accounts=fallback_accounts)
            return json.dumps(fallback_response.model_dump())

    @mcp.resource(
        uri="data://accounts/{account_id}/transactions{?since_date,until_date,type}",
        mime_type="application/json",
    )
    async def get_transactions_by_account(
        account_id: Annotated[
            str,
            "Account ID to filter transactions by specific account. Takes precedence over month, payee, and category filters.",
        ],
        since_date: Annotated[
            str | None,
            "ISO-format date (YYYY-MM-DD) to filter transactions starting from this date. Leave blank for no start date filter.",
        ] = None,
        until_date: Annotated[
            str | None,
            "ISO-format date (YYYY-MM-DD) to filter transactions up to this date. Leave blank for no end date filter.",
        ] = None,
        type: Annotated[
            Literal["all", "uncleared", "cleared", "reconciled"] | None,
            "Transaction type filter. Must be one of: 'all', 'uncleared', 'cleared', 'reconciled'.",
        ] = "all",
    ) -> str:
        """
        Get transactions related a specific account.

        Filtering is specified via filter_params in the format:
        since_date=YYYY-MM-DD&until_date=YYYY-MM-DD&type=cleared

        Examples:
        - data://accounts/44b436fd-149a-4901-b00f-d34e244eedcf/transactions/since_date=2024-01-01&until_date=2024-01-31
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
        except ValueError as e:
            error_response = {"error": f"Invalid parameter format: {str(e)}"}
            return json.dumps(error_response)

        # Get raw YNAB response
        raw_response = ynab_service.get_transactions(
            since_date=converted_since_date,
            until_date=converted_until_date,
            type=type if type else "all",
            account_id=account_id,
        )

        validated_response = TransactionsResponse.from_ynab_response(raw_response)
        # Return as JSON string for MCP resource compatibility
        return validated_response.model_dump_json()
