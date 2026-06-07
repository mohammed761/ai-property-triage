from __future__ import annotations
import os
import sys
from typing import Any
import httpx

class DownstreamServiceClient:
    def __init__(self) -> None:
        # Base URLs for local microservices
        self.rag_base_url = os.getenv(
            "RAG_SERVICE_URL",
            "http://rag-service:8000"
        ).rstrip("/")

        self.image_base_url = os.getenv(
            "IMAGE_ANALYSER_SERVICE_URL",
            "http://image-service:8000"
        ).rstrip("/")
        self.timeout_seconds = float(os.getenv("DOWNSTREAM_TIMEOUT_SECONDS", "30"))

    async def query_rag(self, description: str) -> dict[str, Any]:
        payload = {"description": _ensure_minimum_description(description)}
        return await self._post_json(f"{self.rag_base_url}/query", payload)

    async def analyse_image(self, image_url: str) -> dict[str, Any]:
        # 🟢 CHANGE: Change the payload key to 'image_urls' and make it a list [image_url]
        payload = {"image_urls": [image_url]}
        return await self._post_json(f"{self.image_base_url}/analyse", payload)

    async def _post_json(self, url: str, payload: dict[str, Any]) -> dict[str, Any]:
        try:
            async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                response = await client.post(url, json=payload)
                response.raise_for_status()
                return {"ok": True, "data": response.json(), "error": None}
        except Exception as exc:
            # Enhanced Local Debug Logging Console Outputs
            print(f"\n[DEBUG ERROR] --- DOWNSTREAM SERVICE TRACE ---", file=sys.stderr)
            print(f"[DEBUG ERROR] Endpoint: {url}", file=sys.stderr)
            print(f"[DEBUG ERROR] Payload Sent: {payload}", file=sys.stderr)
            print(f"[DEBUG ERROR] Exception Class: {type(exc).__name__}", file=sys.stderr)
            print(f"[DEBUG ERROR] Error Message: {str(exc)}", file=sys.stderr)
            
            # If the service responded with an error HTTP code (e.g., 400, 404, 422, 500)
            if hasattr(exc, 'response') and exc.response is not None:
                print(f"[DEBUG ERROR] HTTP Status Code: {exc.response.status_code}", file=sys.stderr)
                print(f"[DEBUG ERROR] Response Body: {exc.response.text}", file=sys.stderr)
            print("[DEBUG ERROR] -----------------------------------\n", file=sys.stderr)
            
            # Fallback handling to ensure tool_executor never returns an empty error string
            error_msg = str(exc).strip()
            if not error_msg:
                error_msg = f"Internal connection failure error: {type(exc).__name__}"
                
            return {"ok": False, "data": None, "error": error_msg}

def _ensure_minimum_description(text: str) -> str:
    normalized = " ".join(text.split())
    if len(normalized) >= 20:
        return normalized
    return f"{normalized} Property listing analysis request."