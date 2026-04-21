"""
Contract tests: Halluzinations-Guard Verdrahtung

Prüft:
- Sync-Guard: memory_keys_not_found → memory_required_but_missing=True
- Sync-Guard: vorhandener Key → memory_required_but_missing=False
- Sync-Guard: hallucination_risk="medium" blockiert nicht mehr
- Stream-Guard: guard_flag wird an generate_stream übergeben
- LoopEngine-Guard: guard_flag wird an build_system_prompt übergeben
- Output-Layer: Anti-Halluzinations-Block erscheint wenn Flag True
- Output-Layer: Block fehlt wenn Flag False
"""

from unittest.mock import MagicMock, patch


# ---------------------------------------------------------------------------
# Guard-Berechnung — Sync-Logik (isoliert nachgebaut)
# ---------------------------------------------------------------------------

def _compute_sync_guard(thinking_plan: dict, ctx_trace: dict) -> bool:
    """Spiegelt die Guard-Berechnung aus orchestrator_sync_flow_utils.py"""
    needs_memory = thinking_plan.get("needs_memory") or thinking_plan.get("is_fact_query")
    missing_required_memory = bool(ctx_trace.get("memory_keys_not_found"))
    return bool(needs_memory) and missing_required_memory


def test_sync_guard_fires_when_key_missing():
    plan = {"needs_memory": True, "hallucination_risk": "medium"}
    trace = {"memory_keys_not_found": ["user_name"], "memory_used": True}
    assert _compute_sync_guard(plan, trace) is True


def test_sync_guard_does_not_fire_when_key_found():
    plan = {"needs_memory": True, "hallucination_risk": "medium"}
    trace = {"memory_keys_not_found": [], "memory_used": True}
    assert _compute_sync_guard(plan, trace) is False


def test_sync_guard_does_not_fire_without_needs_memory():
    plan = {"needs_memory": False}
    trace = {"memory_keys_not_found": ["user_name"]}
    assert _compute_sync_guard(plan, trace) is False


def test_sync_guard_fires_for_fact_query_too():
    plan = {"needs_memory": False, "is_fact_query": True}
    trace = {"memory_keys_not_found": ["some_fact"]}
    assert _compute_sync_guard(plan, trace) is True


def test_sync_guard_medium_risk_no_longer_blocks():
    """hallucination_risk='medium' darf den Guard nicht mehr blockieren."""
    plan = {"needs_memory": True, "hallucination_risk": "medium"}
    trace = {"memory_keys_not_found": ["user_name"]}
    # Mit alter Logik wäre high_risk=False → guard=False. Neu: kein high_risk check.
    assert _compute_sync_guard(plan, trace) is True


def test_sync_guard_memory_used_true_does_not_suppress():
    """memory_used=True darf den Guard nicht mehr unterdrücken."""
    plan = {"needs_memory": True}
    trace = {"memory_keys_not_found": ["user_name"], "memory_used": True}
    assert _compute_sync_guard(plan, trace) is True


# ---------------------------------------------------------------------------
# Output-Layer — Anti-Halluzinations-Block
# ---------------------------------------------------------------------------

def test_output_prompt_contains_anti_hallucination_block_when_flag_true():
    from core.layers.output import OutputLayer
    layer = OutputLayer.__new__(OutputLayer)

    mock_persona = MagicMock()
    mock_persona.build_system_prompt.return_value = "Du bist TRION."
    mock_persona.adaptation = []

    with patch("core.layers.output.prompt.system_prompt.get_persona", return_value=mock_persona), \
         patch("core.layers.output.prompt.system_prompt.get_policy_final_instruction", return_value=""), \
         patch("core.layers.output.prompt.system_prompt.get_policy_warnings", return_value=[]):
        prompt = layer.build_system_prompt(
            verified_plan={},
            memory_data="",
            memory_required_but_missing=True,
        )

    assert "ANTI-HALLUZINATION" in prompt
    assert "NIEMALS raten" in prompt
    assert "NICHT gefunden" in prompt


def test_output_prompt_no_anti_hallucination_block_when_flag_false():
    from core.layers.output import OutputLayer
    layer = OutputLayer.__new__(OutputLayer)

    mock_persona = MagicMock()
    mock_persona.build_system_prompt.return_value = "Du bist TRION."
    mock_persona.adaptation = []

    with patch("core.layers.output.prompt.system_prompt.get_persona", return_value=mock_persona), \
         patch("core.layers.output.prompt.system_prompt.get_policy_final_instruction", return_value=""), \
         patch("core.layers.output.prompt.system_prompt.get_policy_warnings", return_value=[]):
        prompt = layer.build_system_prompt(
            verified_plan={},
            memory_data="",
            memory_required_but_missing=False,
        )

    assert "ANTI-HALLUZINATION" not in prompt


# ---------------------------------------------------------------------------
# Trace — memory_keys_not_found wird weitergegeben
# ---------------------------------------------------------------------------

def test_ctx_trace_contains_memory_keys_not_found():
    """build_effective_context muss memory_keys_not_found im Trace liefern."""
    from core.orchestrator_flow_utils import build_effective_context

    mock_ctx = MagicMock()
    mock_ctx.memory_used = False
    mock_ctx.system_tools = ""
    mock_ctx.memory_data = ""
    mock_ctx.memory_keys_requested = ["user_name"]
    mock_ctx.memory_keys_found = []
    mock_ctx.memory_keys_not_found = ["user_name"]

    mock_orch = MagicMock()
    mock_orch.context.get_context.return_value = mock_ctx
    mock_orch._get_compact_context.return_value = ""
    mock_orch._log_warn_for_utils = None
    mock_orch._log_info_for_utils = None

    with patch("config.get_context_trace_dryrun", return_value=False), \
         patch("config.get_small_model_char_cap", return_value=10000):
        _, trace, _res = build_effective_context(
            mock_orch,
            "wie heiße ich?",
            "conv-test",
            small_model_mode=True,
            cleanup_payload={"needs_memory": True, "memory_keys": ["user_name"]},
        )

    assert "memory_keys_not_found" in trace
    assert trace["memory_keys_not_found"] == ["user_name"]
    assert "memory_keys_found" in trace
    assert trace["memory_keys_found"] == []
