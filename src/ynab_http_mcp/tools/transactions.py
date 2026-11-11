# All transaction actions.
from ynab_http_mcp.ynab_service import YnabService
from typing import Annotated, Any, Dict, Literal
from mcp.types import ToolAnnotations
from ynab_http_mcp.schemas.transactions import (
    CreateTransactionRequest,
    MCPTransactions,
    MCPTransaction,
)
import json


def register(mcp, ynab_service: YnabService):

    @mcp.tool(annotations=ToolAnnotations(read_only_hint=False))
    def create_transaction(request: CreateTransactionRequest) -> Dict[str, Any]:
        """Create a new transaction."""
        result = ynab_service.create_transaction(
            request.account_id,
            request.date,
            request.amount,
            request.payee_id,
            request.payee_name,
            request.category_id,
            request.memo,
            request.cleared,
            request.approved,
            request.flag_color,
        )
        return {
            "success": True,
            "transaction": clean_ynab_data(result.data.transaction.to_dict()),
        }

    @mcp.resource(
        uri="data://transactions{?since_date,until_date,type,limit}",
        mime_type="application/json",
    )
    async def get_transactions_resource(
        since_date: Annotated[
            str | None,
            "ISO date YYYY-MM-DD. Leave blank for no start filter.",
        ] = None,
        until_date: Annotated[
            str | None,
            "ISO date YYYY-MM-DD. Leave blank for no end filter.",
        ] = None,
        type: Annotated[
            Literal["all", "uncleared", "cleared", "reconciled"] | None,
            "Filter: all, uncleared, cleared, reconciled.",
        ] = "all",
        limit: Annotated[
            int | None,
            "Max transactions to return. Leave blank for no limit.",
        ] = None,
    ) -> str:
        """Get transactions with flexible filtering options."""
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
        return validated_response.model_dump_json(exclude_none=True)

    @mcp.resource(uri="data://transactions/{id}", mime_type="application/json")
    async def get_single_transaction(
        id: Annotated[
            str,
            "UUID of the transaction to retrieve.",
        ],
    ) -> str:
        """Get a single transaction by its UUID."""
        raw_response = ynab_service.get_transaction(id)
        validated_response = MCPTransaction.from_ynab(raw_response)
        return validated_response.model_dump_json(exclude_none=True)

    @mcp.resource(
        uri="data://accounts/{account_id}/transactions{?since_date,until_date,type}",
        mime_type="application/json",
    )
    async def get_transactions_by_account(
        account_id: Annotated[
            str,
            "Account ID to filter by.",
        ],
        since_date: Annotated[
            str | None,
            "ISO date YYYY-MM-DD. Leave blank for no start filter.",
        ] = None,
        until_date: Annotated[
            str | None,
            "ISO date YYYY-MM-DD. Leave blank for no end filter.",
        ] = None,
        type: Annotated[
            Literal["all", "uncleared", "cleared", "reconciled"] | None,
            "Filter: all, uncleared, cleared, reconciled.",
        ] = "all",
    ) -> str:
        """Get transactions for a specific account."""
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
        return validated_response.model_dump_json()

    @mcp.resource(
        uri="data://months/{month_date}/transactions{?type}",
        mime_type="application/json",
    )
    async def get_transactions_by_month(
        month_date: Annotated[
            str,
            "ISO date YYYY-MM-DD or YYYY-MM. Day is ignored.",
        ],
        type: Annotated[
            Literal["all", "uncleared", "cleared", "reconciled"] | None,
            "Filter: all, uncleared, cleared, reconciled.",
        ] = "all",
    ) -> str:
        """Get transactions within a specific month.

        The URI path scopes the result to a single month, so free-range
        `since_date` / `until_date` query parameters are intentionally not
        accepted here — pass them to the unscoped `data://transactions`
        endpoint instead.
        """
        try:
            raw_response = ynab_service.get_transactions(
                since_date=None,
                until_date=None,
                type=type if type else "all",
                month=month_date,
            )
        except ValueError as e:
            error_response = {"error": f"Invalid parameter format: {str(e)}"}
            return json.dumps(error_response)

        validated_response = MCPTransactions.from_ynab(raw_response)
        return validated_response.model_dump_json()

    @mcp.resource(
        uri="data://payees/{payee_id}/transactions{?since_date,until_date,type}",
        mime_type="application/json",
    )
    async def get_transactions_by_payee(
        payee_id: Annotated[
            str,
            "Payee ID to filter by.",
        ],
        since_date: Annotated[
            str | None,
            "ISO date YYYY-MM-DD. Leave blank for no start filter.",
        ] = None,
        until_date: Annotated[
            str | None,
            "ISO date YYYY-MM-DD. Leave blank for no end filter.",
        ] = None,
        type: Annotated[
            Literal["all", "uncleared", "cleared", "reconciled"] | None,
            "Filter: all, uncleared, cleared, reconciled.",
        ] = "all",
    ) -> str:
        """Get transactions for a specific payee."""
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
        return validated_response.model_dump_json()

    @mcp.resource(
        uri="data://categories/{category_id}/transactions{?since_date,until_date,type}",
        mime_type="application/json",
    )
    async def get_transactions_by_category(
        category_id: Annotated[
            str,
            "Category ID to filter by.",
        ],
        since_date: Annotated[
            str | None,
            "ISO date YYYY-MM-DD. Leave blank for no start filter.",
        ] = None,
        until_date: Annotated[
            str | None,
            "ISO date YYYY-MM-DD. Leave blank for no end filter.",
        ] = None,
        type: Annotated[
            Literal["all", "uncleared", "cleared", "reconciled"] | None,
            "Filter: all, uncleared, cleared, reconciled.",
        ] = "all",
    ) -> str:
        """Get transactions for a specific category."""
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
        return validated_response.model_dump_json(exclude_none=True)
