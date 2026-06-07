from __future__ import annotations

from typing import Optional
from pydantic import BaseModel, ConfigDict, Field


class GuardrailCheckRequest(BaseModel):
    text: str = Field(
        ...,
        min_length=1,
        max_length=10000,
        description="Property listing input or generated property report text to validate.",
    )


class GuardrailCheckResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    passed: bool = Field(..., alias="pass", description="Whether validation approved the text.")
    reason: Optional[str] = Field(default=None, description="Policy reason when validation rejects text.")
    safe_text: Optional[str] = Field(
        default=None,
        description="Whitespace-normalized approved text, or null when rejected.",
    )
