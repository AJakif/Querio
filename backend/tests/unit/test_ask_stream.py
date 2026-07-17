import json

from fastapi.testclient import TestClient


def _parse_sse(raw_text: str) -> list[tuple[str, dict]]:
    events: list[tuple[str, dict]] = []
    event_name = None
    for line in raw_text.splitlines():
        if line.startswith("event: "):
            event_name = line[len("event: "):]
        elif line.startswith("data: ") and event_name is not None:
            events.append((event_name, json.loads(line[len("data: "):])))
            event_name = None
    return events


def test_ask_stream_emits_step_events_with_real_pipeline_data(client: TestClient) -> None:
    with client.stream(
        "GET", "/api/ask/stream", params={"question": "How many orders were placed?"}
    ) as response:
        assert response.status_code == 200
        raw_text = "".join(response.iter_text())

    events = _parse_sse(raw_text)
    step_events = [e for e in events if e[0] == "step"]
    stages = [e[1]["stage"] for e in step_events]

    assert "planner" in stages
    assert "validator" in stages

    planner_detail = next(e[1]["detail"] for e in step_events if e[1]["stage"] == "planner")
    validator_detail = next(e[1]["detail"] for e in step_events if e[1]["stage"] == "validator")

    # Real Planner/Validator fields, not generic "thinking..." placeholder text.
    assert "ambiguity_score" in planner_detail
    assert "scan_cost" in validator_detail

    done_events = [e for e in events if e[0] == "done"]
    assert len(done_events) == 1
    assert done_events[0][1]["type"] == "answer"


def test_ask_stream_final_done_payload_matches_non_streaming_shape(client: TestClient) -> None:
    with client.stream(
        "GET", "/api/ask/stream", params={"question": "How many orders were placed?"}
    ) as response:
        raw_text = "".join(response.iter_text())

    done_payload = next(data for name, data in _parse_sse(raw_text) if name == "done")

    non_stream_response = client.post("/api/ask", json={"question": "How many orders were placed?"})
    assert non_stream_response.status_code == 200
    non_stream_payload = non_stream_response.json()

    assert set(done_payload.keys()) == set(non_stream_payload.keys())
