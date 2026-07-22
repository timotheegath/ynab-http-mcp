"""
Base schema utilities for YNAB HTTP MCP schemas.

This module provides core utilities for schema management and metadata.

Read-side model convention: Lean / Full / Aggregate
====================================================

Every read resource in this server follows a three-layer convention. The
purpose is to keep the LLM's primary read path (Lean) cheap to read and
reason about, while preserving an escape hatch (Full) for arithmetic and
SDK-fidelity lookups, and a pre-computed view (Aggregate) for the
most-asked questions (top-N, trend, totals).

Lean
----
The default response shape for every read entity
(``MCPCategory``, ``MCPAccount``, ``MCPTransaction``, ``MCPSubTransaction``,
``CleanPayee``, ``PlanMonth``, ``MonthCategory``, etc.).

Lean models expose:

- Identity fields (id, name)
- State booleans (hidden, deleted, internal, approved, closed)
- Minimum-viable raw fields needed for **filter / sort / date math**
  (e.g. ``goal_type``, ``goal_target_date``, ``goal_percentage_complete``)
- Formatted currency strings (e.g. ``"-$45.00"``)
- Derived plain-English strings for opaque nested concepts
  (e.g. ``goal_summary``, ``goal_status``)

Lean models MUST NOT expose:

- Integer milliunit fields when a formatted string twin exists
  (``milli_amount`` / ``amount``, ``budgeted`` / ``budgeted_formatted``, …)
- Formatted strings whose value is fully captured in a derived string
  (e.g. ``goal_target_formatted`` is redundant when ``goal_summary``
  already includes the target prose)
- Any field that is not needed for filter, sort, date math, or quick
  comprehension (``note``, ``import_id``, ``debt_escrow_amounts``, …)

The drop rule for a field is therefore: *if a formatted string captures
the same value, drop the raw field; if a derived string captures the
raw field, drop the raw field; if the LLM never needs it for filter /
sort / date math, drop it.*

Full
----
Every lean model has a ``*Full`` sibling that inherits the lean fields
and adds exactly one new field, ``full_details: dict``. The dict
contains the cleaned raw YNAB SDK object for the same entity — every
field the SDK exposes (including fields the Lean layer dropped) is
reachable by name inside the dict. The dict is a ``dict`` and is not
typed as a Pydantic model (the SDK already has the model). Drill-in
endpoints at ``data://{entity}/{id}/full`` return the ``*Full`` shape.

Lean list responses never carry ``full_details``. The three layers
(Lean / Full / Aggregate) live at distinct URIs and never co-occur in
one response payload.

Aggregate
---------
Pre-computed insights exposed at dedicated URIs (currently only
``data://transactions/insights``). Aggregates are derived server-side
(top-N, trend, totals, breakdown) and embedded in their own response
model. They are never embedded in Lean resources.

Serialization
-------------
Lean models are serialised with ``model_dump_json(exclude_none=True)``
so that ``None`` fields are omitted from the JSON output — no
``"field": null`` noise. The Full layer follows the same convention
for its lean fields; ``full_details`` is itself never ``None``.
"""

from typing import Any, Dict, Type, TypeVar, Generic, Self
from pydantic import BaseModel, ConfigDict
import logging
from datetime import date as date_type, datetime as datetime_type
from uuid import UUID as uuid_type

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)


def get_json_schema(model: Type[BaseModel]) -> Dict[str, Any]:
    """
    Get JSON schema representation of a Pydantic model.

    This is used for FastMCP metadata integration.
    """
    return model.model_json_schema()


YNABNative = TypeVar("YNABNative")


class MCPResponse(BaseModel, Generic[YNABNative]):
    model_config = ConfigDict(
        json_encoders={date_type: str, datetime_type: str, uuid_type: str}
    )

    @classmethod
    def from_ynab(cls, raw: YNABNative) -> Self:
        raise NotImplementedError

    def to_ynab(self) -> YNABNative:
        raise NotImplementedError  # for write tools


class MCPRequest(BaseModel):
    def to_ynab_params(self) -> dict:
        raise NotImplementedError
