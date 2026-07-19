"""
Simplified transaction schemas for YNAB HTTP MCP.

This module defines simplified Pydantic models for validating
YNAB transaction data using basic data types suitable for agents.
"""

from typing import Optional, List, Dict, Any
from datetime import date as date_type
from pydantic import BaseModel, Field, ConfigDict


class CleanTransaction(BaseModel):
    """
    Simplified transaction model using basic data types.

    This represents a YNAB transaction with all essential fields
    using simple types that are easily consumable by AI agents.
    """
    model_config = ConfigDict(json_encoders={date_type: str})

    # Required fields
    id: str = Field(..., description="Unique transaction identifier")
    date: date_type = Field(..., description="Transaction date")
    amount: int = Field(..., description="Transaction amount in milliunits (1/1000 of currency unit)")
    memo: Optional[str] = Field(None, description="Transaction memo/note")
    cleared: str = Field(
        ..., description="Cleared status (cleared/uncleared/reconciled). Values: 'cleared', 'uncleared', 'reconciled'"
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
        None, description="Transfer account identifier if applicable. Used in subtransactions to specify target account for transfers"
    )
    transfer_transaction_id: Optional[str] = Field(
        None, description="Transfer transaction ID if applicable. Used in subtransactions to link to reverse transfer transaction"
    )
    matched_transaction_id: Optional[str] = Field(
        None, description="Matched transaction ID if applicable. Used for imported transactions to link to existing records"
    )
    flag_color: Optional[str] = Field(None, description="Flag color if flagged. Possible values: red, orange, yellow, green, blue, purple")
    flag_name: Optional[str] = Field(None, description="Flag name if flagged")
    debt_transaction_type: Optional[str] = Field(
        None, description="Debt transaction type if applicable. Possible values: loan_payment, loan_principal, loan_interest, credit_card_payment, credit_card_principal, credit_card_fee"
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



