"""
Simplified transaction schemas for YNAB HTTP MCP.

This module defines simplified Pydantic models for validating
YNAB transaction data using basic data types suitable for agents.
"""

from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from . import registry


class CleanTransaction(BaseModel):
    """
    Simplified transaction model using basic data types.

    This represents a YNAB transaction with all essential fields
    using simple types that are easily consumable by AI agents.
    """

    # Required fields
    id: str = Field(..., description="Unique transaction identifier")
    date: str = Field(..., description="Transaction date in ISO format (YYYY-MM-DD)")
    amount: int = Field(..., description="Transaction amount in milliunits")
    memo: Optional[str] = Field(None, description="Transaction memo/note")
    cleared: str = Field(
        ..., description="Cleared status (cleared/uncleared/reconciled)"
    )
    approved: bool = Field(..., description="Whether transaction is approved")
    account_id: str = Field(..., description="Account identifier")
    account_name: str = Field(..., description="Account name")

    # Optional fields
    payee_id: Optional[str] = Field(None, description="Payee identifier if applicable")
    payee_name: Optional[str] = Field(None, description="Payee name")
    category_id: Optional[str] = Field(
        None, description="Category identifier if applicable"
    )
    category_name: Optional[str] = Field(None, description="Category name")
    transfer_account_id: Optional[str] = Field(
        None, description="Transfer account identifier if applicable"
    )
    transfer_transaction_id: Optional[str] = Field(
        None, description="Transfer transaction ID if applicable"
    )
    matched_transaction_id: Optional[str] = Field(
        None, description="Matched transaction ID if applicable"
    )
    flag_color: Optional[str] = Field(None, description="Flag color if flagged")
    flag_name: Optional[str] = Field(None, description="Flag name if flagged")
    debt_transaction_type: Optional[str] = Field(
        None, description="Debt transaction type if applicable"
    )
    amount_formatted: Optional[str] = Field(None, description="Formatted amount string")
    amount_currency: Optional[float] = Field(
        None, description="Amount in currency units"
    )
    subtransactions: List[Dict[str, Any]] = Field(
        default_factory=list, description="Subtransactions if split transaction"
    )


class TransactionsResponse(BaseModel):
    """
    Simplified response structure for transactions endpoint.

    Wraps the list of simplified transactions with metadata.
    """

    transactions: List[CleanTransaction] = Field(
        ..., description="List of simplified transactions"
    )
    server_knowledge: int = Field(
        ..., description="Server knowledge version for pagination"
    )


# Register schemas with the global registry
registry.register("CleanTransaction", CleanTransaction)
registry.register("TransactionsResponse", TransactionsResponse)
