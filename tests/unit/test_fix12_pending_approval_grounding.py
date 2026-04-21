"""
Fix #12: Pending-Approval Grounding Bug

Problem: request_container returns {"status": "pending_approval", ...}.
Two bugs prevented the output layer from handling this gracefully:

Bug A — Wrong evidence status:
  Grounding evidence was built with status="ok" even for pending_approval results.
  output.py _has_pending_approval bypass requires status="pending_approval" → never fired.

Bug B — persist_execution_result wipe:
  execution_result_stream is created with metadata={} at plan-start.
  set_runtime_grounding_evidence writes to plan["_execution_result"]["metadata"]["grounding_evidence"].
  persist_execution_result REPLACES plan["_execution_result"] with execution_result_stream.to_dict()
  where to_dict()["metadata"] = {} → grounding evidence wiped.
  Output layer then sees empty evidence → successful_extractable=0 → grounding fails.

Fix:
A) Stream + Sync flow: detect pending_approval result for request_container → use status="pending_approval"
B) Stream + Sync flow: re-apply set_runtime_grounding_evidence after persist_execution_result
"""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def _src(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8")


# ── Fix A: pending_approval status detection ─────────────────────────────────

def test_stream_flow_detects_pending_approval_status():
    """Stream-Flow TOOL SUCCESS block muss pending_approval für request_container erkennen."""
    src = _src("core/orchestrator_stream_flow_utils.py")
    assert "_result_status_raw" in src
    assert "_is_pending_approval" in src
    assert "_evidence_status" in src
    assert 'tool_name == "request_container"' in src
    assert '_result_status_raw == "pending_approval"' in src


def test_stream_flow_uses_evidence_status_variable():
    """Stream-Flow muss _evidence_status statt hartkodiertem 'ok' für grounding-Eintrag nutzen."""
    src = _src("core/orchestrator_stream_flow_utils.py")
    # Find TOOL SUCCESS block
    success_idx = src.find("# TOOL SUCCESS (no error, no retry needed)")
    assert success_idx != -1
    block = src[success_idx:success_idx + 1200]
    # Must use _evidence_status variable in the grounding evidence call
    assert 'status=_evidence_status' in block
    evidence_idx = block.find("_build_grounding_evidence_entry(")
    assert evidence_idx != -1
    evidence_block = block[evidence_idx:evidence_idx + 200]
    assert "status=_evidence_status" in evidence_block


def test_sync_flow_detects_pending_approval_status():
    """Sync-Flow TOOL SUCCESS block muss pending_approval für request_container erkennen."""
    src = _src("core/orchestrator_tool_execution_sync_utils.py")
    assert "_result_status_raw_s" in src
    assert "_is_pending_approval_s" in src
    assert "_evidence_status_s" in src
    assert 'tool_name == "request_container"' in src
    assert '_result_status_raw_s == "pending_approval"' in src


def test_sync_flow_uses_evidence_status_variable():
    """Sync-Flow muss _evidence_status_s für grounding-Eintrag nutzen."""
    src = _src("core/orchestrator_tool_execution_sync_utils.py")
    success_idx = src.find("# Fix #12A: detect pending_approval for request_container")
    assert success_idx != -1
    block = src[success_idx:success_idx + 1000]
    assert "status=_evidence_status_s" in block
    evidence_idx = block.find("build_grounding_evidence_entry_fn(")
    assert evidence_idx != -1
    evidence_block = block[evidence_idx:evidence_idx + 200]
    assert "status=_evidence_status_s" in evidence_block


# ── Fix B: Re-apply after persist ────────────────────────────────────────────

def test_stream_flow_reapplies_evidence_after_persist():
    """Stream-Flow muss grounding evidence nach persist_execution_result neu setzen."""
    src = _src("core/orchestrator_stream_flow_utils.py")
    persist_idx = src.find("persist_execution_result(verified_plan, execution_result_stream)")
    assert persist_idx != -1
    # Check that re-apply comes right after persist (within 300 chars)
    after_persist = src[persist_idx:persist_idx + 400]
    assert "Fix #12B" in after_persist
    assert "set_runtime_grounding_evidence(verified_plan, grounding_evidence_stream)" in after_persist
    assert "set_runtime_successful_tool_runs(verified_plan, successful_tool_runs_stream)" in after_persist


def test_sync_flow_reapplies_evidence_after_persist():
    """Sync-Flow muss grounding evidence nach persist_execution_result neu setzen."""
    src = _src("core/orchestrator_tool_execution_sync_utils.py")
    persist_idx = src.find("persist_execution_result(verified, execution_result)")
    assert persist_idx != -1
    after_persist = src[persist_idx:persist_idx + 400]
    assert "Fix #12B" in after_persist
    assert "set_runtime_grounding_evidence(verified, _merged_evidence_sync)" in after_persist
    assert "set_runtime_successful_tool_runs(verified, _merged_runs_sync)" in after_persist


def test_sync_flow_stores_merged_evidence_before_persist():
    """Sync-Flow muss merged evidence in Variable speichern bevor persist sie löscht."""
    src = _src("core/orchestrator_tool_execution_sync_utils.py")
    assert "_merged_evidence_sync" in src
    assert "_merged_runs_sync" in src
    # Merged vars must be defined before persist
    merged_idx = src.find("_merged_evidence_sync =")
    persist_idx = src.find("persist_execution_result(verified, execution_result)")
    assert merged_idx != -1
    assert persist_idx != -1
    assert merged_idx < persist_idx, "merged evidence must be stored BEFORE persist_execution_result"


# ── Output layer: _has_pending_approval bypass ───────────────────────────────

def test_output_layer_has_pending_approval_bypass():
    """Output-Layer muss Interactive-Status-Bypass für mode='pass' haben."""
    src = _src("core/layers/output/layer.py")
    # Implementation uses _all_failed_are_interactive (renamed from _has_pending_approval)
    assert "_all_failed_are_interactive" in src
    assert "pending_approval" in src
    assert '"pass"' in src or "'pass'" in src


def test_output_layer_pending_approval_status_check():
    """Output-Layer prüft auf pending_approval in interactive status routing."""
    src = _src("core/layers/output/layer.py")
    assert '"pending_approval" in _interactive_statuses' in src


def test_output_layer_pending_approval_returns_pass_mode():
    """Output-Layer interactive bypass gibt mode=pass zurück."""
    src = _src("core/layers/output/layer.py")
    pending_idx = src.find("_all_failed_are_interactive and require_evidence")
    assert pending_idx != -1
    block = src[pending_idx:pending_idx + 800]
    assert '"pass"' in block or "'pass'" in block


# ── Integration: full pipeline trace ─────────────────────────────────────────

def test_pending_approval_not_counted_as_successful_extractable():
    """pending_approval status soll NICHT als successful_extractable zählen
    (bleibt < min_successful), damit _has_pending_approval Bypass greift."""
    src = _src("core/layers/output/layer.py")
    # allowed_statuses must contain "ok" but NOT "pending_approval"
    allowed_idx = src.find('allowed_statuses')
    assert allowed_idx != -1
    block = src[allowed_idx:allowed_idx + 200]
    assert '"ok"' in block or "'ok'" in block
    assert "pending_approval" not in block[:200] or block.count("pending_approval") == 0


def test_stream_flow_fix12_comment_present():
    """Fix #12 Kommentar muss in stream flow vorhanden sein."""
    src = _src("core/orchestrator_stream_flow_utils.py")
    assert "Fix #12" in src


def test_sync_flow_fix12_comment_present():
    """Fix #12 Kommentar muss in sync flow vorhanden sein."""
    src = _src("core/orchestrator_tool_execution_sync_utils.py")
    assert "Fix #12" in src
