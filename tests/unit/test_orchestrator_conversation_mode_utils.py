from core.orchestrator_policy_signal_utils import resolve_conversation_mode


def test_resolve_conversation_mode_marks_name_introduction_as_conversational_social_memory():
    plan = {"dialogue_act": "smalltalk", "is_fact_query": False}
    out = resolve_conversation_mode(
        plan,
        user_text="mein name ist danny",
        selected_tools=["request_container"],
        contains_explicit_tool_intent_fn=lambda text: False,
        has_non_memory_tool_runtime_signal_fn=lambda text: False,
    )
    assert out["conversation_mode"] == "conversational"
    assert out["social_memory_candidate"] is True
    assert out["grounding_relaxed_for_conversation"] is True


def test_resolve_conversation_mode_marks_runtime_request_as_tool_grounded():
    plan = {"dialogue_act": "request", "is_fact_query": False}
    out = resolve_conversation_mode(
        plan,
        user_text="prüf bitte die gpu",
        selected_tools=["run_skill"],
        contains_explicit_tool_intent_fn=lambda text: False,
        has_non_memory_tool_runtime_signal_fn=lambda text: "gpu" in text,
    )
    assert out["conversation_mode"] == "tool_grounded"
    assert out["social_memory_candidate"] is False
    assert out["grounding_relaxed_for_conversation"] is False


def test_resolve_conversation_mode_marks_social_plus_runtime_as_mixed():
    plan = {"dialogue_act": "smalltalk", "is_fact_query": False}
    out = resolve_conversation_mode(
        plan,
        user_text="hey, kannst du mal meine container checken?",
        selected_tools=["request_container"],
        contains_explicit_tool_intent_fn=lambda text: True,
        has_non_memory_tool_runtime_signal_fn=lambda text: True,
    )
    assert out["conversation_mode"] == "mixed"
    assert out["grounding_relaxed_for_conversation"] is False
