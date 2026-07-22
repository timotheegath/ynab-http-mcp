"""
Simplified account schemas for YNAB HTTP MCP.

This module defines simplified Pydantic models for validating
YNAB account data using basic data types suitable for agents.
"""

from typing import Optional, List, Self, Literal
from pydantic import BaseModel, Field
from .base import MCPResponse
import ynab
from ..utils.schema_utils import simple_validate, clean_ynab_data,clean_date_for_MCP_output, clean_datetime_for_MCP_output, clean_UUID_for_MCP_output, clean_enum_for_MCP_output


class MCPAccount(MCPResponse[ynab.Account]):
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
    # YNAB_BUG ? balance_formatted is said to be an optional return, with possible None ?
    # I have to mark it as optional here as well therefore.
    balance : Optional[str] = Field(None, description="Formatted balance string")

    # Optional fields
    cleared_balance: Optional[str] = Field(
        None, description="Formatted cleared balance string"
    )
    uncleared_balance: Optional[str] = Field(
        None, description="Formatted uncleared balance string"
    )

    # Additional metadata
    transfer_payee_id: str = Field(
        ..., 
        description="The payee id which should be used when transferring to this account")
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
    # debt_escrow_amounts: Optional[dict] = Field(None, description="Debt escrow amounts")
    # debt_interest_rates: Optional[dict] = Field(None, description="Debt interest rates")
    # debt_minimum_payments: Optional[dict] = Field(
    #     None, description="Debt minimum payments"
    # )

    @classmethod
    def from_ynab(cls, raw: ynab.Account | ynab.AccountResponse) -> Self:

        if isinstance(raw, ynab.AccountResponse):
            raw = raw.data.account

        return cls(
            id=clean_UUID_for_MCP_output(raw.id),
            name=raw.name,
            type=clean_enum_for_MCP_output(raw.type),
            on_budget=raw.on_budget,
            closed=raw.closed,
            deleted=raw.deleted,
            balance=raw.balance_formatted if raw.balance_formatted is not None else None,
            cleared_balance=raw.cleared_balance_formatted,
            uncleared_balance=raw.uncleared_balance_formatted,
            transfer_payee_id=clean_UUID_for_MCP_output(raw.transfer_payee_id),
            last_reconciled_at=clean_datetime_for_MCP_output(raw.last_reconciled_at) if raw.last_reconciled_at is not None else None,
            direct_import_linked=raw.direct_import_linked,
            direct_import_in_error=raw.direct_import_in_error,
        )


class MCPAccounts(MCPResponse[ynab.AccountsResponse]):
    """
    Simplified response structure for accounts endpoint.

    Wraps the list of accounts.
    """
    HIDE_DELETED = True
    accounts: List[MCPAccount] = Field(..., description="List of accounts")

    @classmethod
    def from_ynab(cls, raw: ynab.AccountsResponse) -> Self:
        accounts = []
        for ynab_account in raw.data.accounts:
            if cls.HIDE_DELETED and ynab_account.deleted:
                continue
            accounts.append(MCPAccount.from_ynab(ynab_account))
        return cls(
            accounts=accounts
        )
