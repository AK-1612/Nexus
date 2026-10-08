"""Strict Pattern B telemetry contract for NEXUS gateway events."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class TelemetryEvent(BaseModel):
    """A validated event containing only the required audit fields."""

    model_config = ConfigDict(extra="forbid", strict=True)

    timestamp: datetime
    wbsElement: str = Field(pattern=r"^WBS-[A-Z0-9_-]+$")
    promptComplexity: Literal["low", "high"]
    tokenCount: int = Field(ge=1)

    @field_validator("timestamp", mode="before")
    @classmethod
    def parse_timestamp(cls, value: object) -> object:
        if isinstance(value, str):
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        return value

    def to_dict(self) -> dict[str, object]:
        return self.model_dump(mode="json", by_alias=True)
