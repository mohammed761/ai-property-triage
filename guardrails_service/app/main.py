from fastapi import FastAPI

from .nemo_runner import get_guardrails_runner
from .schemas import GuardrailCheckRequest, GuardrailCheckResponse


app = FastAPI(
    title="Guardrails Service",
    description="Guardrails validation service for property listing text.",
    version="0.3.0",
)


@app.get("/health")
def health_check():
    runner = get_guardrails_runner()
    return {
        "service": "guardrails_service",
        "status": "ok",
        "phase": "3-real-guardrails",
        "framework": runner.framework,
    }


@app.post("/check/input", response_model=GuardrailCheckResponse)
async def check_input(request: GuardrailCheckRequest) -> GuardrailCheckResponse:
    decision = await get_guardrails_runner().check_input(request.text)
    return GuardrailCheckResponse(**decision)


@app.post("/check/output", response_model=GuardrailCheckResponse)
async def check_output(request: GuardrailCheckRequest) -> GuardrailCheckResponse:
    decision = await get_guardrails_runner().check_output(request.text)
    return GuardrailCheckResponse(**decision)
