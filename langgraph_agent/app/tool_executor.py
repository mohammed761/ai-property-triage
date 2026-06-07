from __future__ import annotations
from typing import Any
from .schemas import AgentRunRequest
from .service_clients import DownstreamServiceClient

async def execute_tools(request: AgentRunRequest, plan: dict[str, Any]) -> tuple[dict[str, Any], list[str], list[str]]:
    reasoning_steps = ["Tool executor started."]
    tools_used: list[str] = []
    tool_results: dict[str, Any] = {}
    client = DownstreamServiceClient()

    # ==========================================
    # 1. EXECUTE RAG TOOL
    # ==========================================
    if plan.get("use_rag"):
        description = request.description or request.query
        tool_results["rag"] = await client.query_rag(description)
        tools_used.append("rag")
        if tool_results["rag"]["ok"]:
            reasoning_steps.append("RAG Service returned similar listing context.")
        else:
            reasoning_steps.append(f"RAG Service failed: {tool_results['rag']['error']}")

    # ==========================================
    # 2. EXECUTE IMAGE ANALYSER TOOL (MULTI-IMAGE FIXED)
    # ==========================================
    if plan.get("use_image_analyser"):
        image_urls = request.image_urls or []
        if not image_urls:
            reasoning_steps.append("Image Analyser was not called because no image URLs were provided.")
            return tool_results, tools_used, reasoning_steps
        
        # Ensure image_urls is handled cleanly as a list
        if isinstance(image_urls, str):
            image_urls = [image_urls]
            
        image_results = []
        
        for image_url in image_urls:
            # Query the microservice for this specific image URL string
            api_response = await client.analyse_image(image_url)
            
            # Normalize the nested payload wrapper structures 
            if api_response.get("ok"):
                image_results.append(api_response)
            else:
                # Capture clean error structures for individual failed image items
                image_results.append({
                    "ok": False,
                    "error": api_response.get("error", "Unknown API error connection"),
                    "data": {"results": [{"image_url": image_url, "error": "Service call failed"}]}
                })
                
        tool_results["image_analyser"] = image_results
        tools_used.append("image_analyser")
        
        if any(result.get("ok") for result in image_results):
            reasoning_steps.append("Image Analyser returned visual signals.")
        else:
            errors = "; ".join(str(result.get("error")) for result in image_results)
            reasoning_steps.append(f"Image Analyser failed: {errors}")

    if not tools_used:
        reasoning_steps.append("No external tools were required for this query.")

    return tool_results, tools_used, reasoning_steps
