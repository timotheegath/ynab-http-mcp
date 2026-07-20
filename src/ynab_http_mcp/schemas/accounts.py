"""
Simplified account schemas for YNAB HTTP MCP.

This module defines simplified Pydantic models for validating
YNAB account data using basic data types suitable for agents.
"""

from typing import Optional, List
from pydantic import BaseModel, Field


class CleanAccount(BaseModel):
    """
    Simplified account model using basic data types.

    Represents a YNAB account with all essential fields
    using simple types that are easily consumable by AI agents.
    """

    # Required fields
    id: str = Field(..., description="Unique account identifier")
    name: str = Field(..., description="Account name")
    type: str = Field(
        ..., description="Account type (checking, savings, creditCard, etc.)"
    )
    on_budget: bool = Field(..., description="Whether account is on budget")
    closed: bool = Field(..., description="Whether account is closed")
    deleted: bool = Field(..., description="Whether account is deleted")

    # Balance fields
    balance: int = Field(..., description="Current balance in milliunits")
    balance_currency: float = Field(
        ..., description="Current balance in currency units"
    )
    balance_formatted: str = Field(..., description="Formatted balance string")

    # Optional fields
    cleared_balance: Optional[int] = Field(
        None, description="Cleared balance in milliunits"
    )
    cleared_balance_currency: Optional[float] = Field(
        None, description="Cleared balance in currency units"
    )
    cleared_balance_formatted: Optional[str] = Field(
        None, description="Formatted cleared balance string"
    )
    uncleared_balance: Optional[int] = Field(
        None, description="Uncleared balance in milliunits"
    )
    uncleared_balance_currency: Optional[float] = Field(
        None, description="Uncleared balance in currency units"
    )
    uncleared_balance_formatted: Optional[str] = Field(
        None, description="Formatted uncleared balance string"
    )

    # Additional metadata
    transfer_payee_id: Optional[str] = Field(None, description="Transfer payee ID")
    last_reconciled_at: Optional[str] = Field(
        None, description="Last reconciliation timestamp"
    )
    direct_import_linked: Optional[bool] = Field(
        None, description="Whether account is linked for direct import"
    )
    direct_import_in_error: Optional[bool] = Field(
        None, description="Whether direct import is in error"
    )

    # Debt-related fields (optional)
    debt_escrow_amounts: Optional[dict] = Field(None, description="Debt escrow amounts")
    debt_interest_rates: Optional[dict] = Field(None, description="Debt interest rates")
    debt_minimum_payments: Optional[dict] = Field(
        None, description="Debt minimum payments"
    )


class AccountsResponse(BaseModel):
    """
    Simplified response structure for accounts endpoint.

    Wraps the list of accounts.
    """

    accounts: List[CleanAccount] = Field(..., description="List of accounts")
