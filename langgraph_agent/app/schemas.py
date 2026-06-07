from __future__ import annotations

from typing import Any, Optional
from pydantic import BaseModel, Field


class AgentRunRequest(BaseModel):
    query: str = Field(
        ...,
        min_length=5,
        description="Complex question about the property listing."
    )
    description: Optional[str] = Field(
        default=None,
        description="Optional listing description to send to the RAG service."
    )
    image_urls: list[str] = Field(
        default_factory=list,
        description="Optional property image URLs to send to the Image Analyser service."
    )
    listing_id: Optional[str] = Field(
        default=None,
        description="Optional listing ID for future stateful workflows."
    )


class AgentRunResponse(BaseModel):
    answer: Any
    tools_used: list[str] = Field(default_factory=list)
    reasoning_steps: list[str] = Field(default_factory=list)
