# All transaction actions.
from ynab_http_mcp.ynab_service import YnabService
from typing import Annotated, Literal
from ynab_http_mcp.schemas.transactions import (
    MCPTransactions,
    MCPTransaction,
    MCPTransactionFull,
)
from ynab_http_mcp.schemas.transaction_aggregate import (
    _default_window,
    build_transaction_insights,
    ClearedBreakdown,
    TransactionInsightsResponse,
)
from ynab_http_mcp.utils.dates import parse_date
import json


def register(mcp, ynab_service: YnabService):

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

    @mcp.resource(
        uri="data://transactions/insights{?since_date,until_date,account_id}",
        mime_type="application/json",
    )
    async def get_transaction_insights(
        since_date: Annotated[
            str | None,
            "ISO date YYYY-MM-DD. Defaults to first day of (current month - 2 months).",
        ] = None,
        until_date: Annotated[
            str | None,
            "ISO date YYYY-MM-DD (exclusive). Defaults to first day of month after current.",
        ] = None,
        account_id: Annotated[
            str | None,
            "Optional account UUID to scope aggregate to a single account.",
        ] = None,
    ) -> str:
        """Get pre-computed aggregate transaction insights: monthly buckets,
        inflow/outflow/net, top-5 payees/categories, cleared breakdown, and
        spending_trend. Default window is the last 3 calendar months."""
        try:
            if since_date is None and until_date is None:
                since, until = _default_window()
            else:
                if since_date is None:
                    since, _ = _default_window()
                else:
                    since = parse_date(since_date).date()
                if until_date is None:
                    _, until = _default_window()
                else:
                    until = parse_date(until_date).date()
        except ValueError as exc:
            err = TransactionInsightsResponse(
                period_start="",
                period_end="",
                monthly_buckets=[],
                total_inflow_formatted="$0.00",
                total_outflow_formatted="$0.00",
                net_formatted="$0.00",
                average_monthly_spending_formatted="$0.00",
                average_transaction_formatted="$0.00",
                spending_trend="stable",
                top_payees=[],
                top_categories=[],
                by_cleared_status=ClearedBreakdown(
                    cleared=0, uncleared=0, reconciled=0
                ),
                transaction_count=0,
                error=f"Invalid date: {exc}",
            )
            return err.model_dump_json(exclude_none=True)

        try:
            raw_response = ynab_service.get_transactions(
                since_date=since.isoformat(),
                until_date=until.isoformat(),
                type="all",
                account_id=account_id,
            )
        except ValueError as e:
            err = TransactionInsightsResponse(
                period_start=since.isoformat(),
                period_end=until.isoformat(),
                monthly_buckets=[],
                total_inflow_formatted="$0.00",
                total_outflow_formatted="$0.00",
                net_formatted="$0.00",
                average_monthly_spending_formatted="$0.00",
                average_transaction_formatted="$0.00",
                spending_trend="stable",
                top_payees=[],
                top_categories=[],
                by_cleared_status=ClearedBreakdown(
                    cleared=0, uncleared=0, reconciled=0
                ),
                transaction_count=0,
                error=f"Invalid parameter: {e}",
            )
            return err.model_dump_json(exclude_none=True)
        except Exception as e:
            err = TransactionInsightsResponse(
                period_start=since.isoformat(),
                period_end=until.isoformat(),
                monthly_buckets=[],
                total_inflow_formatted="$0.00",
                total_outflow_formatted="$0.00",
                net_formatted="$0.00",
                average_monthly_spending_formatted="$0.00",
                average_transaction_formatted="$0.00",
                spending_trend="stable",
                top_payees=[],
                top_categories=[],
                by_cleared_status=ClearedBreakdown(
                    cleared=0, uncleared=0, reconciled=0
                ),
                transaction_count=0,
                error=f"YNAB API failure: {e}",
            )
            return err.model_dump_json(exclude_none=True)

        try:
            insights = build_transaction_insights(
                raw_response.data.transactions or [], since, until
            )
        except Exception as e:
            insights = TransactionInsightsResponse(
                period_start=since.isoformat(),
                period_end=until.isoformat(),
                monthly_buckets=[],
                total_inflow_formatted="$0.00",
                total_outflow_formatted="$0.00",
                net_formatted="$0.00",
                average_monthly_spending_formatted="$0.00",
                average_transaction_formatted="$0.00",
                spending_trend="stable",
                top_payees=[],
                top_categories=[],
                by_cleared_status=ClearedBreakdown(
                    cleared=0, uncleared=0, reconciled=0
                ),
                transaction_count=0,
                error=f"Aggregate computation failed: {e}",
            )
        return insights.model_dump_json(exclude_none=True)

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

    @mcp.resource(uri="data://transactions/{id}/full", mime_type="application/json")
    async def get_single_transaction_full(
        id: Annotated[
            str,
            "UUID of the transaction to retrieve.",
        ],
    ) -> str:
        """Get a transaction with full_details for integer amount in
        milliunits and raw subtransactions. Use when arithmetic or
        SDK-fidelity access is required beyond the lean endpoint."""
        raw_response = ynab_service.get_transaction(id)
        validated_response = MCPTransactionFull.from_ynab(raw_response)
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
        uri="data://months/{month_date}/transactions{?since_date,until_date,type}",
        mime_type="application/json",
    )
    async def get_transactions_by_month(
        month_date: Annotated[
            str,
            "ISO date YYYY-MM-DD or YYYY-MM. Day is ignored.",
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
        """Get transactions within a specific month."""
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
