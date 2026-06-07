from __future__ import annotations

from typing import Any, TypedDict

from langgraph.graph import END, StateGraph

from .planner import plan_agent_run
from .schemas import AgentRunRequest
from .synthesiser import synthesise_answer
from .tool_executor import execute_tools


class AgentState(TypedDict, total=False):
    request: AgentRunRequest
    plan: dict[str, Any]
    tool_results: dict[str, Any]
    tools_used: list[str]
    reasoning_steps: list[str]
    answer: Any


async def planner_node(state: AgentState) -> AgentState:
    request = state["request"]
    plan, steps = await plan_agent_run(request.query)
    reasoning_steps = [*state.get("reasoning_steps", []), *steps]
    for reason in plan.reasons:
        reasoning_steps.append(f"Planner reason: {reason}")
    return {**state, "plan": plan.to_dict(), "reasoning_steps": reasoning_steps}


async def tool_executor_node(state: AgentState) -> AgentState:
    request = state["request"]
    tool_results, tools_used, steps = await execute_tools(request, state["plan"])
    return {
        **state,
        "tool_results": tool_results,
        "tools_used": tools_used,
        "reasoning_steps": [*state.get("reasoning_steps", []), *steps],
    }


async def synthesiser_node(state: AgentState) -> AgentState:
    request = state["request"]
    answer, steps = await synthesise_answer(
        request=request,
        plan=state["plan"],
        tool_results=state.get("tool_results", {}),
        tools_used=state.get("tools_used", []),
    )
    return {
        **state,
        "answer": answer,
        "reasoning_steps": [*state.get("reasoning_steps", []), *steps],
    }


def build_agent_graph():
    graph = StateGraph(AgentState)
    graph.add_node("planner", planner_node)
    graph.add_node("tool_executor", tool_executor_node)
    graph.add_node("synthesiser", synthesiser_node)

    graph.set_entry_point("planner")
    graph.add_edge("planner", "tool_executor")
    graph.add_edge("tool_executor", "synthesiser")
    graph.add_edge("synthesiser", END)

    return graph.compile()


AGENT_GRAPH = build_agent_graph()


async def run_agent_graph(request: AgentRunRequest) -> dict[str, Any]:
    result = await AGENT_GRAPH.ainvoke(
        {
            "request": request,
            "tool_results": {},
            "tools_used": [],
            "reasoning_steps": ["Received agent run request."],
        }
    )
    return {
        "answer": result.get("answer", ""),
        "tools_used": result.get("tools_used", []),
        "reasoning_steps": result.get("reasoning_steps", []),
    }
