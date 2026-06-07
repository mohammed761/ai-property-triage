# Project State

## n8n Layer 2 Orchestration

- n8n is configured in `docker-compose.yml` on port `5678`.
- The n8n container name is `ai_property_n8n`.
- Local Safari HTTP is supported with `N8N_SECURE_COOKIE=false`.
- The importable workflow is `n8n_flow/ai_property_triage_workflow.json`.
- The workflow can be imported with `docker exec ai_property_n8n n8n import:workflow --input=/files/ai_property_triage_workflow.json`.
- Workflow input shape:

```json
{
  "description": "...",
  "image_urls": [],
  "listing_agent_name": "..."
}
```

## Workflow Pipeline

1. Webhook receives listing JSON.
2. Guardrails validates input text.
3. Failed input returns a rejection response.
4. Deterministic Set node extracts simple structured fields.
5. LangGraph Agent runs final reasoning and service orchestration.
6. Set node adds residential/commercial route.
7. Guardrails validates output.
8. Failed output returns `needs_human_review`.
9. Safe output returns final JSON response.

## Local Service URLs

- RAG: `http://127.0.0.1:8001`
- Image Analyser: `http://127.0.0.1:8002`
- Guardrails: `http://127.0.0.1:8003`
- LangGraph Agent: `http://127.0.0.1:8004`
- n8n: `http://localhost:5678`

## Layer 1 WebUI

- Layer 1 WebUI is runnable locally with Gradio from `webui/app.py`.
- Conversational Assistant tab calls local Ollama at `OLLAMA_BASE_URL`, using `OLLAMA_MODEL`.
- Listing Submission tab posts `listing_agent_name`, `description`, and `image_urls` to `N8N_WEBHOOK_URL`.
- Default WebUI port is `7860`.
- Required local settings are documented in `.env.example`.
