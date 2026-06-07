from __future__ import annotations

import json
from pathlib import Path


REPORT_PATH = Path("test_outputs/service_inputs_outputs.md")


def _extract_response(report: str, section: str) -> dict:
    marker = f"== {section} ==\n"
    start = report.index(marker) + len(marker)
    response_marker = "RESPONSE\n"
    response_start = report.index(response_marker, start) + len(response_marker)
    response_end = report.index("\n\n", response_start)
    return json.loads(report[response_start:response_end])


def main() -> None:
    report = REPORT_PATH.read_text(encoding="utf-8")

    required_urls = (
        "REQUEST http://127.0.0.1:8001/query",
        "REQUEST http://127.0.0.1:8002/analyse",
        "REQUEST http://127.0.0.1:8003/check/input",
        "REQUEST http://127.0.0.1:8003/check/output",
        "REQUEST http://127.0.0.1:8004/agent/run",
    )
    for url in required_urls:
        assert url in report, f"Missing expected URL in report: {url}"

    forbidden = (
        "REQUEST http://127.0.0.1:8002/query",
        "REQUEST http://127.0.0.1:8004/analyse",
        "REQUEST http://127.0.0.1:8001/agent/run",
        "https://example.com/property-kitchen.jpg",
        "2450000",
    )
    for value in forbidden:
        assert value not in report, f"Forbidden value appears in report: {value}"

    agent_response = _extract_response(report, "Agent run")
    answer = agent_response["answer"]

    assert answer["image_scores"] == [], "Agent answer should not include image scores when image_urls is empty."
    assert answer["price_ils"] is None, "Agent answer should use null price when no price exists in the input."
    assert answer["similar_listings"], "Agent answer should include RAG similar listings."
    assert agent_response["tools_used"] == ["rag"], "Agent tools_used should be exactly ['rag'] for this request."
    assert "RAG Service returned similar listing context." in agent_response["reasoning_steps"]
    assert "Used request facts and RAG output only." in agent_response["reasoning_steps"]

    print(f"Validated {REPORT_PATH}")


if __name__ == "__main__":
    main()
