"""
Simplified transaction schemas for YNAB HTTP MCP.

This module defines simplified Pydantic models for validating
YNAB transaction data using basic data types suitable for agents.
"""

from typing import Optional, List, Dict, Any
from datetime import date as date_type, datetime as datetime_type
from pydantic import BaseModel, Field, ConfigDict
from ynab import (
    TransactionsResponse as ynabTransactionsResponse,
    TransactionResponse as ynabTransactionResponse,
)
from ynab_http_mcp.utils.schema_utils import clean_ynab_data, simple_validate
from ynab_http_mcp.debug import debug_exception


class CleanTransaction(BaseModel):
    """
    Simplified transaction model using basic data types.

    This represents a YNAB transaction with all essential fields
    using simple types that are easily consumable by AI agents.
    """

    model_config = ConfigDict(json_encoders={date_type: str, datetime_type: str})

    @staticmethod
    def _extract_hints() -> Dict[str, str]:
        """
        Extract contextual hints for complex fields from the schema.
        """
        hints = {}
        for field_name, field_info in CleanTransaction.model_fields.items():
            if field_info.description and any(
                keyword in field_info.description
                for keyword in [
                    "transfer",
                    "matched",
                    "flag",
                    "debt",
                    "amount",
                    "cleared",
                ]
            ):
                hints[field_name] = field_info.description
        return hints

    # Required fields
    id: str = Field(..., description="Unique transaction identifier")
    date: date_type = Field(..., description="Transaction date")
    amount: int = Field(
        ..., description="Transaction amount in milliunits (1/1000 of currency unit)"
    )
    memo: Optional[str] = Field(None, description="Transaction memo/note")
    cleared: str = Field(
        ...,
        description="Cleared status (cleared/uncleared/reconciled). Values: 'cleared', 'uncleared', 'reconciled'",
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
        None,
        description="Transfer account identifier if applicable. Used in subtransactions to specify target account for transfers",
    )
    transfer_transaction_id: Optional[str] = Field(
        None,
        description="Transfer transaction ID if applicable. Used in subtransactions to link to reverse transfer transaction",
    )
    matched_transaction_id: Optional[str] = Field(
        None,
        description="Matched transaction ID if applicable. Used for imported transactions to link to existing records",
    )
    flag_color: Optional[str] = Field(
        None,
        description="Flag color if flagged. Possible values: red, orange, yellow, green, blue, purple",
    )
    flag_name: Optional[str] = Field(None, description="Flag name if flagged")
    debt_transaction_type: Optional[str] = Field(
        None,
        description="Debt transaction type if applicable. Possible values: loan_payment, loan_principal, loan_interest, credit_card_payment, credit_card_principal, credit_card_fee",
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
    hints: Optional[Dict[str, str]] = Field(
        None, description="Contextual hints for complex fields"
    )

    @staticmethod
    def from_ynab_response(
        ynab_reponse: ynabTransactionsResponse,
    ) -> "TransactionsResponse":
        # Convert to dict and clean data using unified function
        raw_data = ynab_reponse.to_dict()

        # Clean each transaction using unified data cleaning
        cleaned_transactions = []
        for transaction_data in raw_data.get("data", {}).get("transactions", []):
            # Clean data using unified function (handles UUID→string, import field filtering, etc.)
            cleaned_data = clean_ynab_data(transaction_data)

            # Validate using simplified approach
            try:
                validated_transaction = simple_validate(cleaned_data, CleanTransaction)
                cleaned_transactions.append(validated_transaction.model_dump())
            except Exception:
                debug_exception(
                    f"Failed to validate transaction {transaction_data.get('id', 'unknown')}"
                )
                # Skip invalid transactions but continue processing others
                continue

        # Create final response with contextual hints extracted from schema
        hints = CleanTransaction._extract_hints()

        final_response = {
            "transactions": cleaned_transactions,
            "server_knowledge": raw_data.get("data", {}).get("server_knowledge", 0),
            "hints": hints,
        }

        # Validate the complete response structure using simplified approach
        validated_response = simple_validate(final_response, TransactionsResponse)
        return validated_response


class TransactionResponse(BaseModel):
    """
    Simplified response structure for transactions endpoint.

    Wraps the list of simplified transactions with metadata.
    """

    transaction: CleanTransaction = Field(
        ..., description="Single simplified transaction"
    )
    server_knowledge: int = Field(
        ..., description="Server knowledge version for pagination"
    )
    hints: Optional[Dict[str, str]] = Field(
        None, description="Contextual hints for complex fields"
    )

    @staticmethod
    def from_ynab_response(
        ynab_reponse: ynabTransactionResponse,
    ) -> "TransactionResponse":
        # Convert to dict and clean data using unified function
        raw_data = ynab_reponse.to_dict()
        transaction_data = raw_data.get("data", {})["transaction"]

        # Clean each transaction using unified data cleaning
        cleaned_transaction = {}

        # Clean data using unified function (handles UUID→string, import field filtering, etc.)
        cleaned_data = clean_ynab_data(transaction_data)

        # Validate using simplified approach
        try:
            validated_transaction = simple_validate(cleaned_data, CleanTransaction)
            cleaned_transaction = validated_transaction.model_dump()
        except Exception:
            debug_exception(
                f"Failed to validate transaction {transaction_data.get('id', 'unknown')}"
            )

        # Create final response with contextual hints extracted from schema
        hints = CleanTransaction._extract_hints()

        final_response = {
            "transaction": cleaned_transaction,
            "server_knowledge": raw_data.get("data", {}).get("server_knowledge", 0),
            "hints": hints,
        }

        # Validate the complete response structure using simplified approach
        validated_response = simple_validate(final_response, TransactionResponse)
        return validated_response
