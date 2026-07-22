# All transaction actions.
from ynab_http_mcp.ynab_service import YnabService
from typing import Annotated, Literal
from ynab_http_mcp.schemas.transactions import (
    MCPTransactions,
    MCPTransaction,
    MCPTransactionFull,
)
from ynab_http_mcp.schemas.transaction_aggregate import (
    build_transaction_insights,
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
        return validated_response.model_dump_json(exclude_none=True)

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
        return validated_response.model_dump_json(exclude_none=True)

    @mcp.resource(uri="data://transactions/{id}/full", mime_type="application/json")
    async def get_single_transaction_full(
        id: Annotated[
            str,
            "UUID of the transaction to retrieve.",
        ],
    ) -> str:
        """
        Get a single transaction by its UUID, including the cleaned raw
        YNAB SDK payload under ``full_details``.

        The Lean endpoint (``data://transactions/{id}``) returns the
        formatted ``amount`` string only. This drill-in endpoint adds a
        single ``full_details`` dict containing the integer ``amount`` in
        milliunits, the raw ``subtransactions`` array with integer amounts
        per sub, and every other field the Lean layer dropped. Use this
        when arithmetic or SDK-fidelity access is required.
        """
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
        return validated_response.model_dump_json(exclude_none=True)

    @mcp.resource(
        uri="data://transactions/insights{?since_date,until_date,account_id}",
        mime_type="application/json",
    )
    async def get_transaction_insights(
        since_date: Annotated[
            str | None,
            "ISO-format date (YYYY-MM-DD) to start the analysis window. Defaults to the first day of (current month - 2 months).",
        ] = None,
        until_date: Annotated[
            str | None,
            "ISO-format date (YYYY-MM-DD) to end the analysis window (exclusive). Defaults to the first day of the month after the current month.",
        ] = None,
        account_id: Annotated[
            str | None,
            "Optional account UUID to scope the aggregate to a single account.",
        ] = None,
    ) -> str:
        """
        Get a pre-computed aggregate view of transactions over a time window.

        Returns ``TransactionInsightsResponse`` with monthly buckets
        (zero-filled), inflow / outflow / net totals, top-5 payees,
        top-5 categories, cleared-status breakdown, and a directional
        ``spending_trend`` (``"increasing"`` / ``"decreasing"`` /
        ``"stable"``). Default window is the last 3 calendar months
        (current + previous 2) when no ``since_date`` / ``until_date`` are
        given.

        Examples:
        - data://transactions/insights
        - data://transactions/insights?since_date=2024-01-01&until_date=2024-04-01
        - data://transactions/insights?account_id=00000000-0000-0000-0000-000000000000
        """
        from ynab_http_mcp.schemas.transaction_aggregate import (
            _default_window,
            ClearedBreakdown,
        )

        # Resolve the window
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

        # Fetch transactions in the window (one YNAB call)
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

        # Build the aggregate
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
