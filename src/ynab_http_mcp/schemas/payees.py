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


class CleanPayee(MCPResponse[ynab.Payee]):
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
        for field_name, field_info in CleanPayee.model_fields.items():
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
        """Build a ``CleanPayee`` from a raw ``ynab.Payee``."""
        return cls(
            id=str(raw.id),
            name=raw.name,
            deleted=raw.deleted,
            transfer_account_id=(
                str(raw.transfer_account_id) if raw.transfer_account_id else None
            ),
        )


class CleanPayeeFull(CleanPayee):
    """Full sibling of ``CleanPayee`` — same lean fields plus ``full_details``.

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
        lean = CleanPayee.from_ynab(raw)
        return cls(
            **lean.model_dump(),
            full_details=clean_ynab_data(raw.to_dict()),
        )


class PayeesResponse(BaseModel):
    """
    Simplified response structure for payees endpoint.

    Wraps the list of payee groups.
    """

    payees: List[CleanPayee] = Field(..., description="List of payees")
    hints: Optional[Dict[str, str]] = Field(
        None, description="Contextual hints for complex fields"
    )

    @staticmethod
    def from_ynab_response(ynab_response: ynab.PayeesResponse) -> "PayeesResponse":
        cleaned_payees: List[CleanPayee] = []
        for payee in ynab_response.data.payees or []:
            try:
                cleaned_payees.append(CleanPayee.from_ynab(payee))
            except Exception:
                debug_exception(
                    f"Failed to validate payee {getattr(payee, 'id', 'unknown')}"
                )
                continue

        hints = CleanPayee._extract_hints()
        return PayeesResponse(payees=cleaned_payees, hints=hints)


class PayeeResponse(BaseModel):
    """
    Simplified response structure for payee endpoint.

    For a single payee object.
    """

    payee: CleanPayee = Field(..., description="Payee")
    hints: Optional[Dict[str, str]] = Field(
        None, description="Contextual hints for complex fields"
    )

    @staticmethod
    def from_ynab_response(ynab_reponse: ynab.PayeeResponse) -> "PayeeResponse":
        try:
            validated_payee = CleanPayee.from_ynab(ynab_reponse.data.payee)
        except Exception:
            debug_exception(
                f"Failed to validate payee {getattr(ynab_reponse.data.payee, 'id', 'unknown')}"
            )
            validated_payee = CleanPayee(
                id="", name="", deleted=False, transfer_account_id=None
            )

        hints = CleanPayee._extract_hints()
        return PayeeResponse(payee=validated_payee, hints=hints)


class PayeeResponseFull(BaseModel):
    """
    Drill-in response shape for a single payee, including the cleaned raw
    ``ynab.Payee`` under ``full_details``. Sibling to ``PayeeResponse``;
    chosen as the minimum-churn option (no changes to ``PayeeResponse`` /
    ``PayeesResponse`` wiring).
    """

    payee: CleanPayeeFull = Field(..., description="Payee (Full layer)")
    hints: Optional[Dict[str, str]] = Field(
        None, description="Contextual hints for complex fields"
    )

    @staticmethod
    def from_ynab_response(ynab_reponse: ynab.PayeeResponse) -> "PayeeResponseFull":
        try:
            validated_payee = CleanPayeeFull.from_ynab(ynab_reponse.data.payee)
        except Exception:
            debug_exception(
                f"Failed to validate payee (full) {getattr(ynab_reponse.data.payee, 'id', 'unknown')}"
            )
            validated_payee = CleanPayeeFull(
                id="",
                name="",
                deleted=False,
                transfer_account_id=None,
                full_details={},
            )

        hints = CleanPayee._extract_hints()
        return PayeeResponseFull(payee=validated_payee, hints=hints)
