from __future__ import annotations
import json
import re
from typing import Any
from .llm_client import LLMClient, env_flag
from .schemas import AgentRunRequest

async def synthesise_answer(
    request: AgentRunRequest,
    plan: dict[str, Any],
    tool_results: dict[str, Any],
    tools_used: list[str],
) -> tuple[Any, list[str]]:
    reasoning_steps = ["Synthesiser started."]

    if env_flag("ENABLE_LLM", False):
        print("Attempting LLM synthesiser...", flush=True)
        llm_answer = await _try_llm_synthesiser(request, plan, tool_results)
        if llm_answer:
            reasoning_steps.append("LLM synthesiser generated the final answer.")
            return llm_answer, reasoning_steps

    reasoning_steps.append("Used request facts and RAG output only.")
    return _template_synthesise(request, plan, tool_results, tools_used), reasoning_steps

async def _try_llm_synthesiser(
    request: AgentRunRequest,
    plan: dict[str, Any],
    tool_results: dict[str, Any],
) -> str | None:
    prompt = {
        "query": request.query,
        "planner_decision": plan,
        "tool_results": tool_results,
        "instruction": (
            "Write only the final answer text. Do not return JSON. "
            "Synthesize and present the real computer vision metrics if present "
            "(like predicted room type, confidence, and condition scores)."
        ),
    }
    
    try:
        return await LLMClient().complete(
            [
                {
                    "role": "system",
                    "content": (
                        "You synthesize property triage answers from tool outputs. "
                        "Be concise, honest, incorporate computer vision image analyser statistics cleanly, and do not invent facts."
                    ),
                },
                {"role": "user", "content": json.dumps(prompt, ensure_ascii=False)},
            ]
        )
    except Exception:
        return None

def _template_synthesise(
    request: AgentRunRequest,
    plan: dict[str, Any],
    tool_results: dict[str, Any],
    tools_used: list[str],
) -> dict[str, Any]:
    if not tools_used:
        return {"error": "No external tool was needed for this query."}

    processed_scores: list[dict[str, Any]] = []
    image_results = tool_results.get("image_analyser") or []

    if isinstance(image_results, dict):
        image_results = [image_results]

    for res in image_results:
        if res.get("ok"):
            api_data = res.get("data") or {}
            inner_results = api_data.get("results", [])
            
            for img in inner_results:
                if "error" not in img:
                    processed_scores.append({
                        "url": img.get("image_url", ""),
                        "room_type": img.get("room_type", "unknown"),
                        "condition_score": float(img.get("condition_score", 0.0)),
                        "confidence": float(img.get("confidence", 0.0))
                    })
                else:
                    processed_scores.append({
                        "url": img.get("image_url", ""),
                        "room_type": "unknown",
                        "condition_score": 0.0,
                        "confidence": 0.0
                    })
        else:
            try:
                failed_url = res.get("data", {}).get("results", [{}])[0].get("image_url", "unknown_url")
            except Exception:
                failed_url = "unknown_url"
                
            processed_scores.append({
                "url": failed_url,
                "room_type": "unknown",
                "condition_score": 0.0,
                "confidence": 0.0
            })

    rag_insight_text = ""
    similar_listings: list[dict[str, Any]] = []
    rag_result = tool_results.get("rag")
    if rag_result and rag_result.get("ok"):
        rag_data = rag_result.get("data") or {}
        rag_insight_text = rag_data.get("insight", "")
        similar_listings = _normalise_similar_listings(rag_data.get("similar_listings", []))

    description = request.description or request.query
    property_type = _extract_property_type(description)
    output_payload: dict[str, Any] = {
        "property_type": property_type,
        "routing_decision": _routing_decision(property_type),
        "location": _extract_location(description),
        "price_ils": _extract_price_ils(description),
        "num_rooms": _extract_num_rooms(description),
        "key_features": _extract_key_features(description),
        "image_scores": processed_scores,
        "similar_listings": similar_listings,
        "rag_insight": rag_insight_text or None,
        "enrichment_notes": _enrichment_notes(request, tools_used, processed_scores),
        "confidence": _confidence(tools_used, similar_listings, processed_scores),
    }

    return output_payload


def _normalise_similar_listings(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []

    listings: list[dict[str, Any]] = []
    for item in value:
        if not isinstance(item, dict):
            continue
        listings.append(
            {
                "listing_id": item.get("listing_id"),
                "title": item.get("title"),
                "property_type": item.get("property_type"),
                "location": item.get("location"),
                "price": item.get("price"),
                "similarity_score": item.get("similarity_score"),
                "source_excerpt": item.get("source_excerpt"),
            }
        )
    return listings


def _extract_property_type(text: str) -> str | None:
    lowered = text.lower()
    for property_type in ("apartment", "house", "villa", "penthouse", "studio", "office", "warehouse", "retail"):
        if re.search(rf"\b{re.escape(property_type)}\b", lowered):
            return property_type
    return None


def _routing_decision(property_type: str | None) -> str | None:
    if property_type in {"apartment", "house", "villa", "penthouse", "studio"}:
        return "residential"
    if property_type in {"office", "warehouse", "retail"}:
        return "commercial"
    return None


def _extract_location(text: str) -> str | None:
    known_locations = (
        "Haifa",
        "Tel Aviv",
        "Jerusalem",
        "Kiryat Ata",
        "Caesarea",
        "Nazareth",
        "Netanya",
        "Modiin",
        "Ashdod",
        "Rishon LeZion",
        "Herzliya",
        "Eilat",
        "Beer Sheva",
    )
    for location in known_locations:
        if re.search(rf"\b{re.escape(location)}\b", text, flags=re.IGNORECASE):
            return location

    match = re.search(r"\bin\s+([A-Z][A-Za-z]+(?:\s+[A-Z][A-Za-z]+)?)\b", text)
    if match:
        return match.group(1)
    return None


def _extract_price_ils(text: str) -> float | None:
    match = re.search(r"(?:₪\s*([\d,]+(?:\.\d+)?)|([\d,]+(?:\.\d+)?)\s*(?:nis|ils|shekels?))", text, flags=re.IGNORECASE)
    if not match:
        return None
    raw = match.group(1) or match.group(2)
    try:
        return float(raw.replace(",", ""))
    except ValueError:
        return None


def _extract_num_rooms(text: str) -> int | None:
    match = re.search(r"\b(\d+)(?:\.\d+)?\s*[- ]?room\b", text, flags=re.IGNORECASE)
    if not match:
        return None
    return int(match.group(1))


def _extract_key_features(text: str) -> list[str]:
    patterns = (
        ("renovated", r"\brenovated\b"),
        ("balcony", r"\bbalcony\b"),
        ("parking", r"\bparking\b"),
        ("bright kitchen", r"\bbright kitchen\b"),
        ("modern kitchen", r"\bmodern kitchen\b"),
        ("kitchen", r"\bkitchen\b"),
        ("sea view", r"\bsea view\b"),
        ("garden", r"\bgarden\b"),
        ("terrace", r"\bterrace\b"),
        ("storage", r"\bstorage\b"),
    )
    features: list[str] = []
    for label, pattern in patterns:
        if re.search(pattern, text, flags=re.IGNORECASE) and label not in features:
            features.append(label)
    if "bright kitchen" in features or "modern kitchen" in features:
        features = [feature for feature in features if feature != "kitchen"]
    return features


def _enrichment_notes(
    request: AgentRunRequest,
    tools_used: list[str],
    processed_scores: list[dict[str, Any]],
) -> str:
    if "image_analyser" in tools_used:
        return "Image analysis was performed for the provided image URLs."
    if not request.image_urls:
        return "No image analysis was performed because no image URLs were provided."
    if request.image_urls and not processed_scores:
        return "No image analysis results were available."
    return "No additional enrichment was performed."


def _confidence(
    tools_used: list[str],
    similar_listings: list[dict[str, Any]],
    processed_scores: list[dict[str, Any]],
) -> float:
    confidence = 0.6
    if "rag" in tools_used and similar_listings:
        confidence += 0.15
    if "image_analyser" in tools_used and processed_scores:
        confidence += 0.1
    return round(min(confidence, 0.9), 2)
