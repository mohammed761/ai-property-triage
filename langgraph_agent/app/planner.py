from __future__ import annotations

import json
import re
from dataclasses import dataclass, field

from .llm_client import LLMClient, env_flag


RAG_PATTERNS = (
    r"\bsimilar listings?\b",
    r"\bcomparable listings?\b",
    r"\bcomps\b",
    r"\bprice comparison\b",
    r"\bmarket insight\b",
    r"\bvaluation\b",
    r"\bpricing\b",
    r"\bmarket\b",
)

IMAGE_PATTERNS = (
    r"\bimages?\b",
    r"\bphotos?\b",
    r"\brooms?\b",
    r"\bkitchen\b",
    r"\bbathrooms?\b",
    r"\bbedrooms?\b",
    r"\bliving room\b",
    r"\bexterior\b",
    r"\bcondition score\b",
    r"\bcondition\b",
    r"\brenovation\b",
    r"\bvisual quality\b",
)

BOTH_PATTERNS = (
    r"\bfull analysis\b",
    r"\bcomplete analysis\b",
    r"\bpublishing recommendation\b",
    r"\bpublish recommendation\b",
    r"\blisting recommendation\b",
    r"\bready to publish\b",
)


@dataclass
class Plan:
    use_rag: bool = False
    use_image_analyser: bool = False
    source: str = "rule_based"
    reasons: list[str] = field(default_factory=list)

    @property
    def tools(self) -> list[str]:
        tools: list[str] = []
        if self.use_rag:
            tools.append("rag")
        if self.use_image_analyser:
            tools.append("image_analyser")
        return tools

    def to_dict(self) -> dict:
        return {
            "use_rag": self.use_rag,
            "use_image_analyser": self.use_image_analyser,
            "source": self.source,
            "reasons": self.reasons,
            "tools": self.tools,
        }


def _matches_any(text: str, patterns: tuple[str, ...]) -> bool:
    return any(re.search(pattern, text, flags=re.IGNORECASE) for pattern in patterns)


def plan_with_rules(query: str) -> Plan:
    use_both = _matches_any(query, BOTH_PATTERNS)
    use_rag = use_both or _matches_any(query, RAG_PATTERNS)
    use_image = use_both or _matches_any(query, IMAGE_PATTERNS)

    reasons: list[str] = []
    if use_both:
        reasons.append("Query asks for a full or publishing-oriented analysis.")
    if use_rag and not use_both:
        reasons.append("Query asks for similar listings, pricing, valuation, or market insight.")
    if use_image and not use_both:
        reasons.append("Query asks about images, rooms, condition, renovation, or visual quality.")
    if not use_rag and not use_image:
        reasons.append("Query does not require an external retrieval or image tool.")

    return Plan(use_rag=use_rag, use_image_analyser=use_image, reasons=reasons)


async def plan_agent_run(query: str) -> tuple[Plan, list[str]]:
    reasoning_steps = ["Planner started."]

    if env_flag("ENABLE_LLM_PLANNER", False):
        llm_plan = await _try_llm_planner(query)
        if llm_plan is not None:
            reasoning_steps.append("LLM-assisted planner selected tools.")
            return llm_plan, reasoning_steps
        reasoning_steps.append("LLM-assisted planner unavailable; used rule-based planner.")

    plan = plan_with_rules(query)
    reasoning_steps.append(
        "Rule-based planner selected: "
        + (", ".join(plan.tools) if plan.tools else "no external tools")
        + "."
    )
    return plan, reasoning_steps


async def _try_llm_planner(query: str) -> Plan | None:
    prompt = (
        "Decide which tools are needed for a real estate agent workflow. "
        "Return only JSON with boolean keys use_rag and use_image_analyser. "
        f"Query: {query}"
    )
    response = await LLMClient().complete(
        [
            {"role": "system", "content": "You are a strict JSON planning assistant."},
            {"role": "user", "content": prompt},
        ]
    )
    if not response:
        return None

    try:
        data = json.loads(response)
    except json.JSONDecodeError:
        return None

    use_rag = data.get("use_rag")
    use_image = data.get("use_image_analyser")
    if not isinstance(use_rag, bool) or not isinstance(use_image, bool):
        return None

    return Plan(
        use_rag=use_rag,
        use_image_analyser=use_image,
        source="llm_assisted",
        reasons=["LLM-assisted planner returned a valid tool decision."],
    )
