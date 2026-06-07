from fastapi import FastAPI, HTTPException

from .rag_engine import build_insight, get_collection_count, search_similar_listings
from .schemas import RAGQueryRequest, RAGQueryResponse


app = FastAPI(
    title="RAG Service",
    description="Phase 2 real RAG retrieval service using ChromaDB and sentence-transformers.",
    version="0.2.0",
)


@app.get("/health")
def health_check():
    return {
        "service": "rag_service",
        "status": "ok",
        "phase": "2-real-rag",
        "vector_store_count": get_collection_count(),
    }


@app.post("/query", response_model=RAGQueryResponse)
def query_similar_listings(request: RAGQueryRequest):
    """
    Real RAG retrieval endpoint.

    Current Phase 2 job:
    - embed the listing description using sentence-transformers
    - query ChromaDB
    - return top similar listings
    - generate a simple deterministic insight from retrieved listings

    Not added yet:
    - Llama.cpp generation
    - LangChain prompt
    - external LLM
    """
    try:
        similar_listings = search_similar_listings(
            description=request.description,
            top_k=3,
        )
    except RuntimeError as error:
        raise HTTPException(status_code=503, detail=str(error)) from error

    insight = build_insight(
        description=request.description,
        similar_listings=similar_listings,
    )

    return RAGQueryResponse(
        similar_listings=similar_listings,
        insight=insight,
    )
