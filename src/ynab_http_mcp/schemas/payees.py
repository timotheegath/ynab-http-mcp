"""
Simplified payee schemas for YNAB HTTP MCP.

This module defines simplified Pydantic models for validating
YNAB payee data using basic data types suitable for agents.
"""

from typing import Optional, List, Dict
from pydantic import BaseModel, Field
from ynab import (
    PayeesResponse as ynabPayeesResponse,
    PayeeResponse as ynabPayeeResponse,
)
from ynab_http_mcp.utils.schema_utils import clean_ynab_data, simple_validate
from ynab_http_mcp.debug import debug_exception


class CleanPayee(BaseModel):
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


class PayeesResponse(BaseModel):
    """
    Simplified response structure for payees endpoint.

    Wraps the list of payee groups.
    """

    payees: List[CleanPayee] = Field(..., description="List of payees")
    _hints: Optional[Dict[str, str]] = Field(
        None, description="Contextual hints for complex fields"
    )

    @staticmethod
    def from_ynab_response(ynab_response: ynabPayeesResponse) -> "PayeesResponse":
        raw_data = ynab_response.to_dict()

        # Clean each transaction using unified data cleaning
        cleaned_payees = []
        for payee_data in raw_data.get("data", {}).get("payees", []):
            # Clean data using unified function (handles UUID→string, import field filtering, etc.)
            cleaned_data = clean_ynab_data(payee_data)

            # Validate using simplified approach
            try:
                validated_payee = simple_validate(cleaned_data, CleanPayee)
                cleaned_payees.append(validated_payee.model_dump())
            except Exception:
                debug_exception(
                    f"Failed to validate payee {payee_data.get('id', 'unknown')}"
                )
                # Skip invalid transactions but continue processing others
                continue

        # Create final response with contextual hints extracted from schema
        hints = CleanPayee._extract_hints()

        final_response = {
            "payees": cleaned_payees,
            "server_knowledge": raw_data.get("data", {}).get("server_knowledge", 0),
            "_hints": hints,
        }

        # Validate the complete response structure using simplified approach
        validated_response = simple_validate(final_response, PayeesResponse)
        return validated_response


class PayeeResponse(BaseModel):
    """
    Simplified response structure for payee endpoint.

    For a single payee object.
    """

    payee: CleanPayee = Field(..., description="Payee")
    _hints: Optional[Dict[str, str]] = Field(
        None, description="Contextual hints for complex fields"
    )

    @staticmethod
    def from_ynab_response(ynab_reponse: ynabPayeeResponse) -> "PayeeResponse":
        # Convert to dict and clean data using unified function
        raw_data = ynab_reponse.to_dict()
        payee_data = raw_data.get("data", {})["payee"]

        # Clean each transaction using unified data cleaning
        cleaned_payee = {}

        # Clean data using unified function (handles UUID→string, import field filtering, etc.)
        cleaned_data = clean_ynab_data(payee_data)

        # Validate using simplified approach
        try:
            validated_payee = simple_validate(cleaned_data, CleanPayee)
            cleaned_payee = validated_payee.model_dump()
        except Exception:
            debug_exception(
                f"Failed to validate transaction {payee_data.get('id', 'unknown')}"
            )

        # Create final response with contextual hints extracted from schema
        hints = CleanPayee._extract_hints()

        final_response = {
            "payee": cleaned_payee,
            "server_knowledge": raw_data.get("data", {}).get("server_knowledge", 0),
            "_hints": hints,
        }

        # Validate the complete response structure using simplified approach
        validated_response = simple_validate(final_response, PayeeResponse)
        return validated_response
