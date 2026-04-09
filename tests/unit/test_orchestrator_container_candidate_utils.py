from core.orchestrator_container_candidate_utils import (
    prepare_container_candidate_evidence,
)


def _message_content(msg):
    if isinstance(msg, dict):
        return str(msg.get("content") or "")
    return str(getattr(msg, "content", "") or "")


def test_prepare_container_candidate_evidence_injects_history_hint_and_candidates():
    thinking_plan = {
        "intent": "container starten",
        "suggested_tools": ["request_container"],
    }
    captured_intents = []

    def _route(user_text, plan):
        captured_intents.append(plan.get("intent"))
        return {
            "blueprint_id": "gaming-station",
            "score": "0.91",
            "suggest": True,
            "candidates": [
                {"id": "gaming-station", "score": 0.91},
                {"id": "desktop-streamer", "score": 0.62},
            ],
        }

    prepare_container_candidate_evidence(
        "starte bitte einen container",
        thinking_plan,
        chat_history=[{"role": "assistant", "content": "Nimm gaming-station fuer Steam und Sunshine."}],
        message_content_fn=_message_content,
        route_blueprint_request_fn=_route,
        log_info_fn=lambda _msg: None,
    )

    assert thinking_plan["needs_chat_history"] is True
    assert thinking_plan["intent"].endswith("gaming-station")
    assert captured_intents[-1].endswith("gaming-station")
    assert thinking_plan["_container_resolution"]["decision"] == "suggest_blueprint"
    assert thinking_plan["_container_resolution"]["blueprint_id"] == "gaming-station"
    assert len(thinking_plan["_container_candidates"]) == 2


def test_prepare_container_candidate_evidence_marks_resolver_error_when_router_blocks():
    thinking_plan = {
        "intent": "container starten",
        "suggested_tools": ["request_container"],
    }

    prepare_container_candidate_evidence(
        "container starten",
        thinking_plan,
        chat_history=[],
        message_content_fn=_message_content,
        route_blueprint_request_fn=lambda *_args, **_kwargs: {
            "blocked": True,
            "reason": "blueprint_router_unavailable",
        },
        log_info_fn=lambda _msg: None,
    )

    assert thinking_plan["_container_resolution"]["decision"] == "resolver_error"
    assert thinking_plan["_container_resolution"]["reason"] == "blueprint_router_unavailable"
    assert thinking_plan["_container_candidates"] == []
