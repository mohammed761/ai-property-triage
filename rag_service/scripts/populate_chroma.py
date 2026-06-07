from __future__ import annotations

import json
import os
from pathlib import Path

import chromadb
from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction


CHROMA_DB_PATH = os.getenv("CHROMA_DB_PATH", "/data/chroma")
COLLECTION_NAME = os.getenv("CHROMA_COLLECTION_NAME", "property_listings")
EMBEDDING_MODEL_NAME = os.getenv("EMBEDDING_MODEL_NAME", "all-MiniLM-L6-v2")
SYNTHETIC_LISTINGS_PATH = os.getenv(
    "SYNTHETIC_LISTINGS_PATH",
    "/seed_data/property_listings.json",
)


def format_listing_text(listing: dict) -> str:
    features = ", ".join(listing.get("features", []))

    return (
        f"Title: {listing.get('title')}\n"
        f"Property type: {listing.get('property_type')}\n"
        f"Location: {listing.get('location')}\n"
        f"Price: {listing.get('price')} NIS\n"
        f"Rooms: {listing.get('rooms')}\n"
        f"Size: {listing.get('size_sqm')} sqm\n"
        f"Condition: {listing.get('condition')}\n"
        f"Features: {features}\n"
        f"Description: {listing.get('description')}"
    )


def main() -> None:
    listings_path = Path(SYNTHETIC_LISTINGS_PATH)

    if not listings_path.exists():
        raise FileNotFoundError(
            f"Synthetic listings file not found: {listings_path}"
        )

    with listings_path.open("r", encoding="utf-8") as file:
        listings = json.load(file)

    if len(listings) < 20:
        raise ValueError("At least 20 synthetic listings are required.")

    embedding_function = SentenceTransformerEmbeddingFunction(
        model_name=EMBEDDING_MODEL_NAME
    )

    client = chromadb.PersistentClient(path=CHROMA_DB_PATH)

    try:
        client.delete_collection(COLLECTION_NAME)
        print(f"Deleted old collection: {COLLECTION_NAME}")
    except Exception:
        print(f"No existing collection to delete: {COLLECTION_NAME}")

    collection = client.get_or_create_collection(
        name=COLLECTION_NAME,
        embedding_function=embedding_function,
        metadata={"hnsw:space": "cosine"},
    )

    ids = []
    documents = []
    metadatas = []

    for listing in listings:
        listing_id = str(listing["listing_id"])

        ids.append(listing_id)
        documents.append(format_listing_text(listing))
        metadatas.append(
            {
                "listing_id": listing_id,
                "title": str(listing.get("title", "")),
                "property_type": str(listing.get("property_type", "")),
                "location": str(listing.get("location", "")),
                "price": float(listing.get("price", 0)),
                "rooms": int(listing.get("rooms", 0)),
                "size_sqm": int(listing.get("size_sqm", 0)),
                "condition": str(listing.get("condition", "")),
                "features": ", ".join(listing.get("features", [])),
            }
        )

    collection.upsert(
        ids=ids,
        documents=documents,
        metadatas=metadatas,
    )

    print("ChromaDB population complete.")
    print(f"Collection: {COLLECTION_NAME}")
    print(f"Database path: {CHROMA_DB_PATH}")
    print(f"Inserted listings: {collection.count()}")


if __name__ == "__main__":
    main()
