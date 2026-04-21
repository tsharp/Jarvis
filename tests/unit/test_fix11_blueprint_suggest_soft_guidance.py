"""
Fix #11: Blueprint Suggest Zone Hallucination Fix

Problem: Blueprint Router gibt SUGGEST zurück (score in [0.68, 0.85)).
Aktueller Code: status="unavailable" → Output-Layer sieht grounding_missing_evidence
→ LLM kann nicht antworten → halluziniert stattdessen.

Fix: Suggest-Zone → status="needs_clarification" (nicht in der unavailable-Menge der Output-Layer)
→ LLM sieht Clarification-Message in tool_context + darf frei antworten → fragt Nutzer nach.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def _src(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8")


# ── Stream Flow ──────────────────────────────────────────────────────────────

def test_stream_suggest_uses_needs_clarification_status():
    """Stream-Flow: _suggest_data-Branch muss needs_clarification statt unavailable verwenden."""
    src = _src("core/orchestrator_stream_flow_utils.py")
    suggest_block_start = src.find("if _suggest_data:")
    assert suggest_block_start != -1
    suggest_block = src[suggest_block_start:suggest_block_start + 1200]
    assert 'status="needs_clarification"' in suggest_block
    assert 'status="unavailable"' not in suggest_block


def test_stream_suggest_removes_hard_block_unavailable():
    """Stream-Flow: suggest_data-Branch darf kein unavailable mehr haben."""
    src = _src("core/orchestrator_stream_flow_utils.py")
    suggest_idx = src.find("if _suggest_data:")
    assert suggest_idx != -1
    # bis zum nächsten `else:` Block
    block = src[suggest_idx:suggest_idx + 800]
    # unavailable darf hier nicht mehr im status= vorkommen
    import re
    bad = re.findall(r'status="unavailable"', block)
    assert not bad, f"Found status=unavailable in suggest block: {bad}"


def test_stream_suggest_clarification_msg_content():
    """Stream-Flow: Clarification-Msg muss Kandidaten + Nutzeranfrage enthalten."""
    src = _src("core/orchestrator_stream_flow_utils.py")
    suggest_idx = src.find("if _suggest_data:")
    block = src[suggest_idx:suggest_idx + 800]
    assert "Mögliche Kandidaten" in block
    assert "Bitte den Nutzer" in block
    assert "_clarification_msg" in block


def test_stream_suggest_tool_context_uses_clarification_msg():
    """Stream-Flow: tool_context soll den clarification_msg enthalten (nicht RÜCKFRAGE)."""
    src = _src("core/orchestrator_stream_flow_utils.py")
    suggest_idx = src.find("if _suggest_data:")
    block = src[suggest_idx:suggest_idx + 800]
    # Neue Version: _clarification_msg in tool_context
    assert "tool_context += f" in block or 'tool_context +=' in block
    assert "_clarification_msg" in block


# ── Sync Flow ────────────────────────────────────────────────────────────────

def test_sync_suggest_uses_needs_clarification_status():
    """Sync-Flow: Suggest-Zweig muss needs_clarification verwenden."""
    src = _src("core/orchestrator_tool_execution_sync_utils.py")
    assert 'status="needs_clarification"' in src


def test_sync_no_match_uses_routing_block():
    """Sync-Flow: No-Match-Zweig (kein blueprint_suggest_msg) muss routing_block verwenden."""
    src = _src("core/orchestrator_tool_execution_sync_utils.py")
    # Both statuses must exist — needs_clarification for suggest, routing_block for no-match
    assert 'status="needs_clarification"' in src
    assert 'status="routing_block"' in src


def test_sync_suggest_conditioned_on_blueprint_suggest_msg():
    """Sync-Flow: needs_clarification darf nur gesetzt werden wenn blueprint_suggest_msg gesetzt ist."""
    src = _src("core/orchestrator_tool_execution_sync_utils.py")
    # Find the new if/else block
    cond_idx = src.find("if blueprint_suggest_msg:")
    assert cond_idx != -1, "Missing `if blueprint_suggest_msg:` condition in sync flow"
    block = src[cond_idx:cond_idx + 800]
    assert "needs_clarification" in block
    assert "else:" in block
    assert "routing_block" in block


# ── Output-Layer: needs_clarification nicht in der Blocking-Menge ────────────

def test_output_layer_blocking_set_excludes_needs_clarification():
    """Output-Layer darf needs_clarification nicht als Blocking-Status behandeln."""
    src = _src("core/layers/output/layer.py")
    # Find the set that determines grounding failures
    blocking_set_idx = src.find('"unavailable"')
    assert blocking_set_idx != -1
    # Extract the set context
    block = src[max(0, blocking_set_idx - 100):blocking_set_idx + 200]
    assert "needs_clarification" not in block, (
        "needs_clarification must NOT be in the output layer grounding blocking set"
    )
