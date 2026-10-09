"""Strict Pydantic v2 telemetry contract for zero-tolerance audit trail enforcement."""

from datetime import datetime
from typing import Any, Dict, Literal

from pydantic import BaseModel, Field, model_serializer


class TelemetryEvent(BaseModel, extra="forbid", strict=True):
    """
    Immutable telemetry record emitted per governed LLM transaction.

    All four fields are mandatory; any extra key causes a ``ValidationError``
    so that the audit trail can never be silently corrupted.
    """

    timestamp: datetime = Field(description="RFC 3339 UTC timestamp of the transaction")
    wbsElement: str = Field(description="Billing WBS element identifier")
    promptComplexity: Literal["low", "high"] = Field(
        description="Complexity classification derived from prompt content"
    )
    tokenCount: int = Field(ge=1, description="Total token count for the transaction")

    def to_dict(self) -> Dict[str, Any]:
        """Serialise the event to a plain dictionary with an ISO-formatted timestamp."""
        return {
            "timestamp": self.timestamp.isoformat(),
            "wbsElement": self.wbsElement,
            "promptComplexity": self.promptComplexity,
            "tokenCount": self.tokenCount,
        }
