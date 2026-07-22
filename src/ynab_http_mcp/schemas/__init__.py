"""
Public API for YNAB HTTP MCP schemas.
"""

from .base import get_json_schema
from .transactions import MCPTransaction, MCPTransactions
from .categories import (
    MCPCategory,
    MCPCategoryGoal,
    MCPCategoryGroup,
    MCPCategories,
)
from .planning import (
    MonthCategory,
    PlanMonth,
    PlanMonthResponse,
    PlanMonthSummary,
    AllPlanMonthsResponse,
)

__all__ = [
    "get_json_schema",
    "MCPTransaction",
    "MCPTransactions",
    "MCPCategory",
    "MCPCategoryGoal",
    "MCPCategoryGroup",
    "MCPCategories",
    "MonthCategory",
    "PlanMonth",
    "PlanMonthResponse",
    "PlanMonthSummary",
    "AllPlanMonthsResponse",
]
