#!/usr/bin/env sh
set -eu

GUARDRAILS_URL="${GUARDRAILS_URL:-http://127.0.0.1:8003}"
RAG_URL="${RAG_URL:-http://127.0.0.1:8001}"
IMAGE_URL="${IMAGE_URL:-http://127.0.0.1:8002}"
AGENT_URL="${AGENT_URL:-http://127.0.0.1:8004}"

post_json() {
  url="$1"
  body="$2"
  printf 'REQUEST %s\n%s\n' "$url" "$body"
  printf 'RESPONSE\n'
  curl -sS -H "Content-Type: application/json" -d "$body" "$url"
  printf '\n\n'
}

wait_for_url() {
  url="$1"
  name="$2"
  attempts=60

  while [ "$attempts" -gt 0 ]; do
    if curl -fsS "$url" >/dev/null 2>&1; then
      return 0
    fi

    attempts=$((attempts - 1))
    sleep 1
  done

  printf 'Timed out waiting for %s at %s\n' "$name" "$url" >&2
  return 1
}

wait_for_url "$GUARDRAILS_URL/health" "guardrails-service"
wait_for_url "$RAG_URL/health" "rag-service"
wait_for_url "$IMAGE_URL/health" "image-service"
wait_for_url "$AGENT_URL/health" "langgraph-agent"

printf '== Health checks ==\n'
curl -sS "$GUARDRAILS_URL/health"
printf '\n'
curl -sS "$RAG_URL/health"
printf '\n'
curl -sS "$IMAGE_URL/health"
printf '\n'
curl -sS "$AGENT_URL/health"
printf '\n\n'

printf '== Guardrails input: valid property listing ==\n'
post_json "$GUARDRAILS_URL/check/input" '{"text":"Renovated 3-room apartment in Haifa with balcony and parking."}'

printf '== Guardrails output: unsafe certainty claim ==\n'
post_json "$GUARDRAILS_URL/check/output" '{"text":"This apartment has guaranteed profit and no legal risk."}'

printf '== RAG query ==\n'
post_json "$RAG_URL/query" '{"description":"Renovated 3-room apartment in Haifa with balcony, parking, bright kitchen, and sea view."}'

printf '== Image analysis: invalid URL handled as per-item error ==\n'
post_json "$IMAGE_URL/analyse" '{"image_urls":["not-a-url"]}'

printf '== Agent run ==\n'
post_json "$AGENT_URL/agent/run" '{"query":"Give a concise market insight using similar listings for this property.","description":"Renovated 3-room apartment in Haifa with balcony, parking, bright kitchen, and sea view.","image_urls":[]}'
