# AI Property Triage

Local Docker Compose stack for the AI Property Triage services and n8n Layer 2 orchestration.

## Service Ports

- RAG: `http://127.0.0.1:8001`
- Image Analyser: `http://127.0.0.1:8002`
- Guardrails: `http://127.0.0.1:8003`
- LangGraph Agent: `http://127.0.0.1:8004`
- n8n: `http://localhost:5678`

## Run Locally

```bash
docker compose up -d
```

Seed RAG data when needed:

```bash
make seed-rag
```

## n8n Workflow

The importable workflow is:

```text
n8n_flow/ai_property_triage_workflow.json
```

Open n8n in Safari:

```bash
open -a Safari http://localhost:5678
```

Start n8n and import the workflow by CLI:

```bash
docker compose up -d n8n
docker exec ai_property_n8n n8n import:workflow --input=/files/ai_property_triage_workflow.json
```

See [n8n_flow/README.md](n8n_flow/README.md) for webhook test commands.

## Layer 1 WebUI

The WebUI is a local Gradio app with:

- Conversational Assistant tab backed by local Ollama.
- Listing Submission tab that posts listing data to the n8n webhook.

Start backend services:

```bash
docker compose up -d
```

Start Ollama:

```bash
ollama serve
```

Pull the model if needed:

```bash
ollama pull llama3
```

Run the WebUI:

```bash
cd webui
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python app.py
```

Open:

```text
http://localhost:7860
```

Configuration defaults are documented in `.env.example`.
