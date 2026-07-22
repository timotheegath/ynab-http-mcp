"""
Simplified transaction schemas for YNAB HTTP MCP.

This module defines simplified Pydantic models for validating
YNAB transaction data using basic data types suitable for agents.
"""

from typing import Optional, List, Self
from pydantic import Field
import ynab
from ynab_http_mcp.utils.schema_utils import (
    clean_enum_for_MCP_output,
)
from .base import MCPResponse, date_type, uuid_type


class MCPTransaction(MCPResponse[ynab.TransactionDetail]):
    """
    A transaction indicates a movement of money between accounts, or between an account and a payee.
    """

    class MCPSubTransaction(MCPResponse[ynab.SubTransaction]):
        """
        A transaction may be split into multiple sub-transactions. This is to:
        - Split-assigning a real-life transaction to different categories,
        - ?
        """

        id: uuid_type = Field(..., description="Unique transaction identifier")
        parent_transaction_id: uuid_type = Field(
            ..., description="Unique identifier of the parent transaction"
        )
        amount: Optional[str] = Field(None, description="Formatted amount string")
        milli_amount: int = Field(..., description="Amount in milliunits")

        memo: Optional[str] = Field(None, description="Subtransaction memo/note")

        payee_id: Optional[uuid_type] = Field(
            None, description="Payee identifier if applicable"
        )
        payee_name: Optional[str] = Field(None, description="Payee name")
        category_id: Optional[uuid_type] = Field(
            None, description="Category identifier if applicable"
        )
        category_name: Optional[str] = Field(None, description="Category name")
        transfer_account_id: Optional[uuid_type] = Field(
            None,
            description="If a transfer, the account_id which the subtransaction transfers to",
        )
        transfer_transaction_id: Optional[uuid_type] = Field(
            None,
            description="If a transfer, the id of transaction on the other side of the transfer",
        )
        deleted: bool = Field(
            ..., description="Whether the sub-transaction has been deleted"
        )

        @classmethod
        def from_ynab(cls, raw: ynab.SubTransaction):

            return cls(
                id=uuid_type(raw.id),
                parent_transaction_id=uuid_type(raw.transaction_id),
                amount=raw.amount_formatted,
                milli_amount=raw.amount,
                memo=raw.memo,
                payee_id=raw.payee_id,
                payee_name=raw.payee_name,
                category_id=raw.category_id,
                category_name=raw.category_name,
                transfer_account_id=raw.transfer_account_id,
                transfer_transaction_id=uuid_type(raw.transfer_transaction_id)
                if raw.transfer_transaction_id
                else None,
                deleted=raw.deleted,
            )

    # @staticmethod
    # def _extract_hints() -> Dict[str, str]:
    #     """
    #     Extract contextual hints for complex fields from the schema.
    #     """
    #     hints = {}
    #     for field_name, field_info in MCPTransaction.model_fields.items():
    #         if field_info.description and any(
    #             keyword in field_info.description
    #             for keyword in [
    #                 "transfer",
    #                 "matched",
    #                 "flag",
    #                 "debt",
    #                 "amount",
    #                 "cleared",
    #             ]
    #         ):
    #             hints[field_name] = field_info.description
    #     return hints

    # Required fields
    id: uuid_type = Field(..., description="Unique transaction identifier")
    date: date_type = Field(..., description="Transaction date")
    amount: Optional[str] = Field(None, description="Formatted amount string")
    milli_amount: int = Field(..., description="Amount in milliunits")
    memo: Optional[str] = Field(None, description="Transaction memo/note")
    cleared: str = Field(
        ...,
        description="Cleared status (cleared/uncleared/reconciled). Values: 'cleared', 'uncleared', 'reconciled'",
    )
    approved: bool = Field(..., description="Whether transaction is approved")
    account_id: uuid_type = Field(..., description="Account identifier")
    account_name: str = Field(..., description="Account name")

    # Optional fields
    payee_id: Optional[uuid_type] = Field(
        None, description="Payee identifier if applicable"
    )
    payee_name: Optional[str] = Field(None, description="Payee name")
    category_id: Optional[uuid_type] = Field(
        None, description="Category identifier if applicable"
    )
    category_name: Optional[str] = Field(
        None,
        description="The name of the category. If a split transaction, this will be 'Split'.",
    )
    transfer_account_id: Optional[uuid_type] = Field(
        None,
        description="If a transfer transaction, the account to which it transfers",
    )
    transfer_transaction_id: Optional[uuid_type] = Field(
        None,
        description="If a transfer transaction, the id of transaction on the other side of the transfer",
    )
    import_payee_name_original: Optional[str] = Field(
        None,
        description="If the transaction was imported, the original payee name as it appeared on the statement",
    )
    flag_color: Optional[str] = Field(
        None,
        description="Flag color if flagged. Possible values: red, orange, yellow, green, blue, purple",
    )
    debt_transaction_type: Optional[str] = Field(
        None,
        description="Debt transaction type if applicable. Possible values: loan_payment, loan_principal, loan_interest, credit_card_payment, credit_card_principal, credit_card_fee",
    )
    subtransactions: List[MCPSubTransaction] = Field(
        default_factory=list, description="Subtransactions if split transaction"
    )

    @classmethod
    def from_ynab(cls, raw: ynab.TransactionDetail | ynab.TransactionResponse) -> Self:
        if isinstance(raw, ynab.TransactionResponse):
            raw = raw.data.transaction

        return cls(
            id=uuid_type(raw.id),
            date=raw.var_date,
            amount=raw.amount_formatted,
            milli_amount=raw.amount,
            memo=raw.memo,
            cleared=clean_enum_for_MCP_output(raw.cleared),
            approved=raw.approved,
            account_id=raw.account_id,
            account_name=raw.account_name,
            payee_id=raw.payee_id,
            payee_name=raw.payee_name,
            category_id=raw.category_id,
            category_name=raw.category_name,
            transfer_account_id=raw.transfer_account_id,
            transfer_transaction_id=uuid_type(raw.transfer_transaction_id)
            if raw.transfer_transaction_id
            else None,
            import_payee_name_original=raw.import_payee_name_original,
            flag_color=clean_enum_for_MCP_output(raw.flag_color),
            debt_transaction_type=raw.debt_transaction_type,
            subtransactions=[
                cls.MCPSubTransaction.from_ynab(sub) for sub in raw.subtransactions
            ],
        )


class MCPTransactions(MCPResponse[ynab.TransactionsResponse]):
    """
    Simplified response structure for transactions endpoint.

    Wraps the list of simplified transactions with metadata.
    """

    HIDE_DELETED = True
    transactions: List[MCPTransaction] = Field(
        ..., description="List of simplified transactions"
    )

    @classmethod
    def from_ynab(
        cls,
        raw: ynab.TransactionsResponse,
    ) -> Self:
        transactions = []
        for transaction in raw.data.transactions:
            if transaction.deleted and cls.HIDE_DELETED:
                continue
            transactions.append(MCPTransaction.from_ynab(transaction))
        # Convert to dict and clean data using unified function
        return cls(transactions=transactions)
