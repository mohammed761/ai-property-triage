# Guardrails Service

Phase 3 validation service for AI Property Triage System property text.

## Implementation

The service uses FastAPI for its HTTP API and NeMo Guardrails for rail execution.
`rails/config.yml` enables input and output flows, `rails/rails.co` invokes the
registered validation actions, and `app/actions.py` implements deterministic
property-domain checks.

The service does not call an LLM. It rejects known unsafe claim forms and
requires price statements in generated output to identify a submitted or
retrieved listing source.

## Endpoints

| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/health` | Report Phase 3 service readiness |
| POST | `/check/input` | Validate submitted property listing text |
| POST | `/check/output` | Validate generated property report text |

Request:

```json
{"text": "Renovated 3-room apartment in Haifa with balcony and parking."}
```

Response:

```json
{"pass": true, "reason": null, "safe_text": "Renovated 3-room apartment in Haifa with balcony and parking."}
```

## Docker

From the repository root, rebuild and run only this service:

```bash
docker compose build guardrails-service
docker compose up -d guardrails-service
```

Run the curl examples:

```bash
bash code/services/guardrails_service/test_guardrails.sh
```
