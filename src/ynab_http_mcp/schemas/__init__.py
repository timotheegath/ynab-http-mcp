"""
Public API for YNAB HTTP MCP schemas.
"""

from .base import get_json_schema
from .transactions import (
    MCPTransaction,
    MCPTransactions,
)
from .categories import (
    MCPCategory,
    MCPCategoryGoal,
    MCPCategoryGroup,
    MCPCategories,
)
from .accounts import MCPAccount, MCPAccounts
from .payees import (
    MCPPayee,
    MCPPayees,
)
from .planning import (
    MonthCategory,
    PlanMonth,
    PlanMonthResponse,
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
from .planning_aggregate import (
    PlanInsightsMonth,
    PlanInsightsCategoryMonth,
    PlanInsightsGoal,
    PlanInsightsDerived,
    PlanInsightsCategory,
    PlanInsightsResponse,
)

__all__ = [
    "get_json_schema",
    "MCPTransaction",
    "MCPTransactions",
    "MCPCategory",
    "MCPCategoryGoal",
    "MCPCategoryGroup",
    "MCPCategories",
    "MCPAccount",
    "MCPAccounts",
    "MCPPayee",
    "MCPPayees",
    "MonthCategory",
    "PlanMonth",
    "PlanMonthResponse",
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
    "PlanInsightsMonth",
    "PlanInsightsCategoryMonth",
    "PlanInsightsGoal",
    "PlanInsightsDerived",
    "PlanInsightsCategory",
    "PlanInsightsResponse",
]
