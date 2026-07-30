"""
Simplified payee schemas for YNAB HTTP MCP.

This module defines simplified Pydantic models for validating
YNAB payee data using basic data types suitable for agents.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Self
from pydantic import BaseModel, Field
import ynab
from ynab_http_mcp.utils.schema_utils import clean_ynab_data
from ynab_http_mcp.debug import debug_exception

from .base import MCPResponse


class MCPPayee(MCPResponse[ynab.Payee]):
    """
    Simplified payee model using basic data types.

    Represents a YNAB payee with all essential fields
    using simple types that are easily consumable by AI agents.
    """

    # Required fields
    id: str = Field(..., description="Unique payee identifier")

    @staticmethod
    def _extract_hints() -> Dict[str, str]:
        """
        Extract contextual hints for complex fields from the schema.
        """
        hints = {}
        for field_name, field_info in MCPPayee.model_fields.items():
            if field_info.description:
                hints[field_name] = field_info.description
        return hints

    name: str = Field(..., description="Payee name")
    deleted: bool = Field(..., description="Whether payee is deleted")

    # Optional fields
    transfer_account_id: Optional[str] = Field(
        None,
        description="If a transfer payee, the `account_id` to which this payee transfers to",
    )

    @classmethod
    def from_ynab(cls, raw: ynab.Payee) -> Self:
        """Build a ``MCPPayee`` from a raw ``ynab.Payee``."""
        return cls(
            id=str(raw.id),
            name=raw.name,
            deleted=raw.deleted,
            transfer_account_id=(
                str(raw.transfer_account_id) if raw.transfer_account_id else None
            ),
        )


class MCPPayeeFull(MCPPayee):
    """Full sibling of ``MCPPayee`` — same lean fields plus ``full_details``.

    ``full_details`` is the cleaned raw ``ynab.Payee`` as a dict and contains
    every field the YNAB SDK exposes for a payee that the Lean layer dropped.
    Use this when SDK-fidelity access is required.
    """

    full_details: Dict[str, Any] = Field(
        default_factory=dict,
        description=(
            "Cleaned raw ``ynab.Payee`` as a dict. Contains every field the "
            "YNAB SDK exposes for a payee, including fields the Lean layer "
            "dropped. UUIDs are strings, datetimes are ISO dates, and "
            "YNAB-specific import fields are removed."
        ),
    )

    @classmethod
    def from_ynab(cls, raw: ynab.Payee) -> Self:
        lean = MCPPayee.from_ynab(raw)
        return cls(
            **lean.model_dump(),
            full_details=clean_ynab_data(raw.to_dict()),
        )


class MCPPayees(BaseModel):
    """
    Overarching list response for the payees endpoint.

    Wraps the list of payees for LLM consumption.
    """

    payees: List[MCPPayee] = Field(..., description="List of payees")

    @staticmethod
    def from_ynab_response(ynab_response: ynab.PayeesResponse) -> "MCPPayees":
        cleaned_payees: List[MCPPayee] = []
        for payee in ynab_response.data.payees or []:
            try:
                cleaned_payees.append(MCPPayee.from_ynab(payee))
            except Exception:
                debug_exception(
                    f"Failed to validate payee {getattr(payee, 'id', 'unknown')}"
                )
                continue

        return MCPPayees(payees=cleaned_payees)
