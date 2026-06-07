from fastapi import FastAPI

from .agent_graph import run_agent_graph
from .schemas import AgentRunRequest, AgentRunResponse
from pydantic import BaseModel, Field


app = FastAPI(
    title="LangGraph Agent Service",
    description="Final-style LangGraph workflow service for property triage orchestration.",
    version="0.5.0",
)



class AgentRunRequest(BaseModel):
    query: str
    description: str | None = None
    image_urls: list[str] = Field(default_factory=list)

@app.get("/health")
def health_check():
    return {
        "service": "langgraph_agent",
        "status": "ok",
        "phase": "5-real-langgraph-agent",
        "workflow": "planner -> tool_executor -> synthesiser",
    }


@app.post("/agent/run", response_model=AgentRunResponse)
async def run_agent(request: AgentRunRequest) -> AgentRunResponse:
    result = await run_agent_graph(request)
    return AgentRunResponse(**result)
