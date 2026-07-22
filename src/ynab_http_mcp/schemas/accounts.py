"""
Simplified account schemas for YNAB HTTP MCP.

This module defines simplified Pydantic models for validating
YNAB account data using basic data types suitable for agents.
"""

from typing import Any, ClassVar, Dict, Optional, List, Self
from pydantic import Field
from .base import MCPResponse
import ynab
from ..utils.schema_utils import (
    clean_enum_for_MCP_output,
    clean_ynab_data,
)
from .base import uuid_type, date_type


class MCPAccount(MCPResponse[ynab.Account]):
    """
    Simplified account model using basic data types.

    Represents a YNAB account with all essential fields
    using simple types that are easily consumable by AI agents.
    """

    # Required fields
    id: uuid_type = Field(..., description="Unique account identifier")
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
    balance: Optional[str] = Field(None, description="Formatted balance string")

    # Optional fields
    cleared_balance: Optional[str] = Field(
        None, description="Formatted cleared balance string"
    )
    uncleared_balance: Optional[str] = Field(
        None, description="Formatted uncleared balance string"
    )

    # Additional metadata
    transfer_payee_id: uuid_type = Field(
        ...,
        description="The payee id which should be used when transferring to this account",
    )
    last_reconciled_at: Optional[date_type] = Field(
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
            id=raw.id,
            name=raw.name,
            type=clean_enum_for_MCP_output(raw.type),
            on_budget=raw.on_budget,
            closed=raw.closed,
            deleted=raw.deleted,
            balance=raw.balance_formatted,
            cleared_balance=raw.cleared_balance_formatted,
            uncleared_balance=raw.uncleared_balance_formatted,
            transfer_payee_id=raw.transfer_payee_id,
            last_reconciled_at=raw.last_reconciled_at,
            direct_import_linked=raw.direct_import_linked,
            direct_import_in_error=raw.direct_import_in_error,
        )


class MCPAccounts(MCPResponse[ynab.AccountsResponse]):
    """
    Simplified response structure for accounts endpoint.

    Wraps the list of accounts.
    """

    HIDE_DELETED: ClassVar[bool] = True
    accounts: List[MCPAccount] = Field(..., description="List of accounts")

    @classmethod
    def from_ynab(cls, raw: ynab.AccountsResponse) -> Self:
        accounts = []
        for ynab_account in raw.data.accounts:
            if cls.HIDE_DELETED and ynab_account.deleted:
                continue
            accounts.append(MCPAccount.from_ynab(ynab_account))
        return cls(accounts=accounts)


class MCPAccountFull(MCPAccount):
    """Full sibling of ``MCPAccount`` — same lean fields plus ``full_details``.

    ``full_details`` is the cleaned raw ``ynab.Account`` as a dict and
    contains the integer ``balance`` in milliunits, the integer
    ``cleared_balance`` / ``uncleared_balance``, and every other field the
    Lean layer dropped (``note``, ``interest_rate``, ``available_balance``,
    ``debt_escrow_amounts``, etc.). Use this when arithmetic or
    SDK-fidelity access is required.
    """

    full_details: Dict[str, Any] = Field(
        default_factory=dict,
        description=(
            "Cleaned raw ``ynab.Account`` as a dict. Contains every field the "
            "YNAB SDK exposes for an account, including fields the Lean layer "
            "dropped (``note``, integer milliunit balances, ``interest_rate``, "
            "``available_balance``, ``debt_escrow_amounts``, etc.). UUIDs are "
            "strings, datetimes are ISO dates, and YNAB-specific import fields "
            "are removed."
        ),
    )

    @classmethod
    def from_ynab(cls, raw: ynab.Account | ynab.AccountResponse) -> Self:
        if isinstance(raw, ynab.AccountResponse):
            raw_acct: ynab.Account = raw.data.account
        else:
            raw_acct = raw

        lean = MCPAccount.from_ynab(raw_acct)
        return cls(
            **lean.model_dump(),
            full_details=clean_ynab_data(raw_acct.to_dict()),
        )
