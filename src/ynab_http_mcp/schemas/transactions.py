"""
Transaction schemas for YNAB HTTP MCP.

This module defines Pydantic models for validating and cleaning
YNAB transaction data, filtering out import-related fields.
"""

from typing import Optional, List, Dict, Any
from datetime import date as datetime_date
from uuid import UUID
from pydantic import Field
from .base import CleanBaseModel


class CleanTransaction(CleanBaseModel):
    """
    Cleaned transaction model that filters out import-related fields.
    
    This represents a YNAB transaction with all the essential fields
    but without the noisy import-related fields that are only relevant
    during import operations.
    """
    
    # Required fields
    id: str = Field(..., description="Unique transaction identifier")
    date: datetime_date = Field(..., description="Transaction date")
    amount: int = Field(..., description="Transaction amount in milliunits")
    memo: Optional[str] = Field(None, description="Transaction memo/note")
    cleared: str = Field(..., description="Cleared status (cleared/uncleared/reconciled)")
    approved: bool = Field(..., description="Whether transaction is approved")
    account_id: UUID = Field(..., description="Account UUID")
    account_name: str = Field(..., description="Account name")
    
    # Optional fields
    payee_id: Optional[UUID] = Field(None, description="Payee UUID if applicable")
    payee_name: Optional[str] = Field(None, description="Payee name")
    category_id: Optional[UUID] = Field(None, description="Category UUID if applicable")
    category_name: Optional[str] = Field(None, description="Category name")
    transfer_account_id: Optional[UUID] = Field(None, description="Transfer account UUID if applicable")
    transfer_transaction_id: Optional[str] = Field(None, description="Transfer transaction ID if applicable")
    matched_transaction_id: Optional[str] = Field(None, description="Matched transaction ID if applicable")
    flag_color: Optional[str] = Field(None, description="Flag color if flagged")
    flag_name: Optional[str] = Field(None, description="Flag name if flagged")
    debt_transaction_type: Optional[str] = Field(None, description="Debt transaction type if applicable")
    amount_formatted: Optional[str] = Field(None, description="Formatted amount string")
    amount_currency: Optional[float] = Field(None, description="Amount in currency units")
    subtransactions: List[Dict[str, Any]] = Field(default_factory=list, description="Subtransactions if split transaction")
    
    class Config(CleanBaseModel.Config):
        json_schema_extra = {
            'examples': [
                {
                    'description': 'Example cleaned transaction',
                    'value': {
                        'id': '123e4567-e89b-12d3-a456-426614174000',
                        'date': '2023-01-15',
                        'amount': -50000,  # -$500.00 in milliunits
                        'memo': 'Grocery shopping',
                        'cleared': 'cleared',
                        'approved': True,
                        'account_id': 'a1b2c3d4-e5f6-7890-abcd-ef1234567890',
                        'account_name': 'Checking Account',
                        'payee_name': 'Supermarket',
                        'category_name': 'Groceries',
                        'amount_formatted': '-$500.00'
                    }
                }
            ]
        }


class TransactionsResponse(CleanBaseModel):
    """
    Complete response structure for transactions endpoint.
    
    Wraps the list of cleaned transactions with metadata.
    """
    
    transactions: List[CleanTransaction] = Field(..., description="List of cleaned transactions")
    server_knowledge: int = Field(..., description="Server knowledge version for pagination")
    
    class Config(CleanBaseModel.Config):
        json_schema_extra = {
            'examples': [
                {
                    'description': 'Example transactions response',
                    'value': {
                        'transactions': [],
                        'server_knowledge': 123
                    }
                }
            ]
        }


# Register schemas with the global registry
from . import registry

registry.register('CleanTransaction', CleanTransaction)
registry.register('TransactionsResponse', TransactionsResponse)