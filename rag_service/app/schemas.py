from __future__ import annotations

from typing import Optional
from pydantic import BaseModel, Field


class RAGQueryRequest(BaseModel):
    """
    Future endpoint:
    POST /query

    Input:
    {
      "description": "property listing text"
    }
    """
    description: str = Field(
        ...,
        min_length=20,
        description="Raw property listing description text."
    )


class SimilarListing(BaseModel):
    listing_id: str = Field(..., description="Internal ID of the similar listing.")
    title: Optional[str] = Field(default=None, description="Listing title if available.")
    property_type: Optional[str] = Field(default=None, description="Apartment, house, villa, office, etc.")
    location: Optional[str] = Field(default=None, description="Location of the similar listing.")
    price: Optional[float] = Field(default=None, ge=0, description="Price if available.")
    similarity_score: float = Field(..., ge=0.0, le=1.0, description="Similarity score from vector search.")
    source_excerpt: Optional[str] = Field(default=None, description="Short retrieved context excerpt.")


class RAGQueryResponse(BaseModel):
    """
    Output:
    {
      "similar_listings": [...],
      "insight": "generated insight"
    }
    """
    similar_listings: list[SimilarListing]
    insight: str = Field(..., description="Short insight based only on retrieved similar listings.")
