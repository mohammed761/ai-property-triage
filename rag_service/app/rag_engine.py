from __future__ import annotations

import os
from collections import Counter
from typing import Any

import chromadb
from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction

from .schemas import SimilarListing


CHROMA_DB_PATH = os.getenv("CHROMA_DB_PATH", "/data/chroma")
COLLECTION_NAME = os.getenv("CHROMA_COLLECTION_NAME", "property_listings")
EMBEDDING_MODEL_NAME = os.getenv("EMBEDDING_MODEL_NAME", "all-MiniLM-L6-v2")


_embedding_function = SentenceTransformerEmbeddingFunction(
    model_name=EMBEDDING_MODEL_NAME
)

_client = chromadb.PersistentClient(path=CHROMA_DB_PATH)

_collection = _client.get_or_create_collection(
    name=COLLECTION_NAME,
    embedding_function=_embedding_function,
    metadata={"hnsw:space": "cosine"},
)


def get_collection_count() -> int:
    return _collection.count()


def _as_float(value: Any) -> float | None:
    if value is None:
        return None

    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _similarity_from_distance(distance: float | None) -> float:
    if distance is None:
        return 0.0

    # Chroma cosine distance is lower when more similar.
    # Convert it to a friendly 0..1 score.
    score = 1 / (1 + max(distance, 0.0))
    return round(score, 4)


def search_similar_listings(description: str, top_k: int = 3) -> list[SimilarListing]:
    if get_collection_count() == 0:
        raise RuntimeError(
            "RAG vector store is empty. Run scripts/populate_chroma.py first."
        )

    results = _collection.query(
        query_texts=[description],
        n_results=top_k,
        include=["documents", "metadatas", "distances"],
    )

    ids = results.get("ids", [[]])[0]
    documents = results.get("documents", [[]])[0]
    metadatas = results.get("metadatas", [[]])[0]
    distances = results.get("distances", [[]])[0]

    similar_listings: list[SimilarListing] = []

    for index, listing_id in enumerate(ids):
        metadata = metadatas[index] or {}
        document = documents[index] or ""
        distance = distances[index] if index < len(distances) else None

        similar_listings.append(
            SimilarListing(
                listing_id=str(metadata.get("listing_id", listing_id)),
                title=str(metadata.get("title", "")),
                property_type=str(metadata.get("property_type", "")),
                location=str(metadata.get("location", "")),
                price=_as_float(metadata.get("price")),
                similarity_score=_similarity_from_distance(distance),
                source_excerpt=document[:280],
            )
        )

    return similar_listings


def build_insight(description: str, similar_listings: list[SimilarListing]) -> str:
    if not similar_listings:
        return (
            "No similar listings were found in the current vector store. "
            "Add more listings and repopulate ChromaDB."
        )

    property_types = Counter(
        item.property_type for item in similar_listings if item.property_type
    )
    locations = Counter(item.location for item in similar_listings if item.location)

    top_match = similar_listings[0]
    main_type = property_types.most_common(1)[0][0] if property_types else "property"
    main_location = locations.most_common(1)[0][0] if locations else "the same market"

    prices = [
        item.price
        for item in similar_listings
        if item.price is not None and item.price > 0
    ]

    price_text = ""
    if prices:
        avg_price = sum(prices) / len(prices)
        price_text = f" The average price of the retrieved matches is about {avg_price:,.0f} NIS."

    return (
        f"Real RAG insight: The closest retrieved listing is '{top_match.title}' "
        f"with similarity score {top_match.similarity_score}. "
        f"The submitted description is most similar to {main_type} listings around {main_location}."
        f"{price_text} This insight is based only on the retrieved ChromaDB listings, "
        f"not on external market data."
    )
