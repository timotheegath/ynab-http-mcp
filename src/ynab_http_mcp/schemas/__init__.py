"""
Public API for YNAB HTTP MCP schemas.
"""

from .base import get_json_schema
from .transactions import (
    MCPTransaction,
    MCPTransactionFull,
    MCPTransactions,
)
from .categories import (
    MCPCategory,
    MCPCategoryFull,
    MCPCategoryGoal,
    MCPCategoryGroup,
    MCPCategories,
)
from .accounts import MCPAccount, MCPAccountFull, MCPAccounts
from .payees import (
    MCPPayee,
    MCPPayeeFull,
    MCPPayees,
)
from .planning import (
    MonthCategory,
    MonthCategoryFull,
    PlanMonth,
    PlanMonthFull,
    PlanMonthResponse,
    PlanMonthFullResponse,
    PlanMonthSummary,
    AllPlanMonthsResponse,
)
from .transaction_aggregate import (
    ClearedBreakdown,
    MonthlyTransactionBucket,
    PayeeAggregate,
    CategoryAggregate,
    TransactionInsightsResponse,
)
from .money_movement_aggregate import (
    MonthlyMoneyMovementBucket,
    SourceCategoryAggregate,
    DestinationCategoryAggregate,
    RecurringMovementPair,
    MoneyMovementInsightsResponse,
)

__all__ = [
    "get_json_schema",
    "MCPTransaction",
    "MCPTransactionFull",
    "MCPTransactions",
    "MCPCategory",
    "MCPCategoryFull",
    "MCPCategoryGoal",
    "MCPCategoryGroup",
    "MCPCategories",
    "MCPAccount",
    "MCPAccountFull",
    "MCPAccounts",
    "MCPPayee",
    "MCPPayeeFull",
    "MCPPayees",
    "MonthCategory",
    "MonthCategoryFull",
    "PlanMonth",
    "PlanMonthFull",
    "PlanMonthResponse",
    "PlanMonthFullResponse",
    "PlanMonthSummary",
    "AllPlanMonthsResponse",
    "ClearedBreakdown",
    "MonthlyTransactionBucket",
    "PayeeAggregate",
    "CategoryAggregate",
    "TransactionInsightsResponse",
    "MonthlyMoneyMovementBucket",
    "SourceCategoryAggregate",
    "DestinationCategoryAggregate",
    "RecurringMovementPair",
    "MoneyMovementInsightsResponse",
]
