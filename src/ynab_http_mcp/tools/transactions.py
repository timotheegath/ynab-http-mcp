# All transaction actions.
from ynab_http_mcp.ynab_service import YnabService
from typing import Annotated, Literal
from ynab_http_mcp.schemas.transactions import (
    MCPTransactions,
    MCPTransaction,
)
import json


def register(mcp, ynab_service: YnabService):

    @mcp.resource(
        uri="data://transactions{?since_date,until_date,type,limit}",
        mime_type="application/json",
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
            Literal["all", "uncleared", "cleared", "reconciled"] | None,
            "Transaction type filter. Must be one of: 'all', 'uncleared', 'cleared', 'reconciled'.",
        ] = "all",
        limit: Annotated[
            int | None,
            "Maximum number of transactions to return. Leave blank for no limit.",
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

        # Get raw YNAB response - validation is now handled by the service method
        try:
            raw_response = ynab_service.get_transactions(
                since_date=since_date,
                until_date=until_date,
                type=type if type else "all",
            )
        except ValueError as e:
            error_response = {"error": f"Invalid parameter format: {str(e)}"}
            return json.dumps(error_response)

        validated_response = MCPTransactions.from_ynab(raw_response)
        # Return as JSON string for MCP resource compatibility
        return validated_response.model_dump_json()

    @mcp.resource(uri="data://transactions/{id}", mime_type="application/json")
    async def get_single_transaction(
        id: Annotated[
            str,
            "UUID of the transaction to retrieve.",
        ],
    ) -> str:
        """
        Get a single transaction by its UUID

        Example:
        - data://transactions/fd6bb67d-b77f-4dee-a2f5-47ef2bd8613c
        """
        # Parse filter parameters from the path

        # Get raw YNAB response
        raw_response = ynab_service.get_transaction(id)

        validated_response = MCPTransaction.from_ynab(raw_response)

        # Return as JSON string for MCP resource compatibility
        return validated_response.model_dump_json()

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

        # Get raw YNAB response - validation is now handled by the service method
        try:
            raw_response = ynab_service.get_transactions(
                since_date=since_date,
                until_date=until_date,
                type=type if type else "all",
                account_id=account_id,
            )
        except ValueError as e:
            error_response = {"error": f"Invalid parameter format: {str(e)}"}
            return json.dumps(error_response)

        validated_response = MCPTransactions.from_ynab(raw_response)
        # Return as JSON string for MCP resource compatibility
        return validated_response.model_dump_json()

    @mcp.resource(
        uri="data://months/{month_date}/transactions{?since_date,until_date,type}",
        mime_type="application/json",
    )
    async def get_transactions_by_month(
        month_date: Annotated[
            str,
            "ISO-format date within the month of choice. For instance, '2023-12-11' targets December 2023. Leave blank to select current month",
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
        Get transactions within a specific month.

        Filtering is specified via filter_params in the format:
        since_date=YYYY-MM-DD&until_date=YYYY-MM-DD&type=cleared

        Examples:
        - data://accounts/44b436fd-149a-4901-b00f-d34e244eedcf/transactions/since_date=2024-01-01&until_date=2024-01-31
        """
        # Parse filter parameters from the path

        # Get raw YNAB response - validation is now handled by the service method
        try:
            raw_response = ynab_service.get_transactions(
                since_date=since_date,
                until_date=until_date,
                type=type if type else "all",
                month=month_date,
            )
        except ValueError as e:
            error_response = {"error": f"Invalid parameter format: {str(e)}"}
            return json.dumps(error_response)

        validated_response = MCPTransactions.from_ynab(raw_response)
        # Return as JSON string for MCP resource compatibility
        return validated_response.model_dump_json()
    
    @mcp.resource(
        uri="data://payees/{payee_id}/transactions{?since_date,until_date,type}",
        mime_type="application/json",
    )
    async def get_transactions_by_payee(
        payee_id: Annotated[
            str,
            "Payee ID to filter transactions by specific payee.",
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
        Get transactions related a specific payee.

        Filtering is specified via filter_params in the format:
        since_date=YYYY-MM-DD&until_date=YYYY-MM-DD&type=cleared

        Examples:
        - data://payees/2211a810-42bf-435d-974b-35fc8cdfdf8a/transactions/since_date=2024-01-01&until_date=2024-01-31
        """
        # Parse filter parameters from the path

        # Get raw YNAB response - validation is now handled by the service method
        try:
            raw_response = ynab_service.get_transactions(
                since_date=since_date,
                until_date=until_date,
                type=type if type else "all",
                payee_id=payee_id,
            )
        except ValueError as e:
            error_response = {"error": f"Invalid parameter format: {str(e)}"}
            return json.dumps(error_response)

        validated_response = MCPTransactions.from_ynab(raw_response)
        # Return as JSON string for MCP resource compatibility
        return validated_response.model_dump_json()
    
    @mcp.resource(
        uri="data://categories/{category_id}/transactions{?since_date,until_date,type}",
        mime_type="application/json",
    )
    async def get_transactions_by_category(
        category_id: Annotated[
            str,
            "Category ID to filter transactions by specific category.",
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
        Get transactions related a specific category.

        Filtering is specified via filter_params in the format:
        since_date=YYYY-MM-DD&until_date=YYYY-MM-DD&type=cleared

        Examples:
        - data://category/f7ab4ff3-99c3-44db-b060-2c2df8d9384b/transactions/since_date=2024-01-01&until_date=2024-01-31
        """
        # Parse filter parameters from the path

        # Get raw YNAB response - validation is now handled by the service method
        try:
            raw_response = ynab_service.get_transactions(
                since_date=since_date,
                until_date=until_date,
                type=type if type else "all",
                category_id=category_id,
            )
        except ValueError as e:
            error_response = {"error": f"Invalid parameter format: {str(e)}"}
            return json.dumps(error_response)

        validated_response = MCPTransactions.from_ynab(raw_response)
        # Return as JSON string for MCP resource compatibility
        return validated_response.model_dump_json()
