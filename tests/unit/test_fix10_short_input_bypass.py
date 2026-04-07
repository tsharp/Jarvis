"""
Fix #10: Container Fallback Bug — Short-Input Bypass + Context-Enrichment

Problem: Kurze Inputs wie "ja bitte" haben keine semantische Überlappung mit
Tool-Beschreibungen wie "request_container". ToolSelector gibt [] zurück,
ThinkingLayer überspringt Execution, Control Layer crasht (grounding policy).

Fix:
A) tool_selector.py: context_summary wird bei < 5 Wörtern an search_query angehängt.
B) orchestrator_*_flow_utils.py: letzter Assistenten-Message als context_summary übergeben.
C) orchestrator_*_flow_utils.py: Short-Input Bypass — wenn immer noch leer, core tools injizieren.
"""
import ast
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
import pytest


ROOT = Path(__file__).resolve().parents[2]


def _src(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8")


# ── Fix A: ToolSelector context-enrichment ──────────────────────────────────

def test_tool_selector_uses_context_summary_when_short_input():
    """select_tools muss context_summary nutzen wenn user_text < 5 Wörter."""
    src = _src("core/tool_selector.py")
    impl = src.split("async def select_tools")[1].split("async def _get_candidates")[0]
    assert "context_summary" in impl
    assert "len(user_text.split()) < 5" in impl
    assert "search_query" in impl
    assert "context_summary[-200:]" in impl


def test_tool_selector_still_uses_full_text_when_long_input():
    """Bei langem Input muss der search_query unverändert user_text sein."""
    src = _src("core/tool_selector.py")
    impl = src.split("async def select_tools")[1].split("async def _get_candidates")[0]
    # search_query = user_text muss als Initialisierung vorhanden sein
    assert "search_query = user_text" in impl


@pytest.mark.asyncio
async def test_tool_selector_enriches_short_input():
    """Semantische Suche erhält bei kurzem Input den angereicherten Query."""
    from core.tool_selector import ToolSelector

    selector = ToolSelector.__new__(ToolSelector)
    selector._semantic_unavailable_logged = False
    captured_queries = []

    async def fake_get_candidates(query):
        captured_queries.append(query)
        return []

    selector._get_candidates = fake_get_candidates
    selector.hub = MagicMock()

    with patch("core.tool_selector.ENABLE_TOOL_SELECTOR", True):
        await selector.select_tools("ja bitte", context_summary="Soll ich den Blueprint starten?")

    assert len(captured_queries) == 1
    q = captured_queries[0]
    assert "ja bitte" in q
    assert "Soll ich den Blueprint starten?" in q


@pytest.mark.asyncio
async def test_tool_selector_long_input_not_enriched():
    """Langer Input (>= 5 Wörter) muss nicht angereichert werden."""
    from core.tool_selector import ToolSelector

    selector = ToolSelector.__new__(ToolSelector)
    selector._semantic_unavailable_logged = False
    captured_queries = []

    async def fake_get_candidates(query):
        captured_queries.append(query)
        return []

    selector._get_candidates = fake_get_candidates
    selector.hub = MagicMock()

    with patch("core.tool_selector.ENABLE_TOOL_SELECTOR", True):
        await selector.select_tools(
            "Trion kannst du einen Gaming steam Container erstellen",
            context_summary="irrelevant context here"
        )

    assert captured_queries[0] == "Trion kannst du einen Gaming steam Container erstellen"


# ── Fix B: Orchestrator context_summary weitergabe ──────────────────────────

def test_stream_flow_extracts_last_assistant_message():
    """run_tool_selection_stage (pipeline_stages) muss letzten Assistenten-Message extrahieren."""
    src = _src("core/orchestrator_pipeline_stages.py")
    assert "last_assistant_msg" in src
    assert 'msg.get("role") == "assistant"' in src
    assert "context_summary=last_assistant_msg" in src


def test_sync_flow_extracts_last_assistant_message():
    """Sync-Flow muss run_tool_selection_stage aus pipeline_stages aufrufen."""
    src = _src("core/orchestrator_sync_flow_utils.py")
    assert "run_tool_selection_stage" in src
    assert "_last_assistant_msg" in src


# ── Fix C: Short-Input Bypass ────────────────────────────────────────────────

def test_stream_flow_has_short_input_bypass():
    """pipeline_stages muss Short-Input Bypass implementieren; Stream-Flow muss ihn aufrufen."""
    stages_src = _src("core/orchestrator_pipeline_stages.py")
    assert "not selected_tools" in stages_src
    assert "len(user_text.split()) < 5" in stages_src
    assert "request_container" in stages_src
    assert "run_skill" in stages_src
    assert "home_write" in stages_src
    assert "Short-Input Bypass" in stages_src
    # Stream-Flow ruft die Stage auf
    stream_src = _src("core/orchestrator_stream_flow_utils.py")
    assert "run_tool_selection_stage" in stream_src


def test_sync_flow_has_short_input_bypass():
    """pipeline_stages muss Short-Input Bypass implementieren; Sync-Flow muss ihn aufrufen."""
    stages_src = _src("core/orchestrator_pipeline_stages.py")
    assert "Short-Input Bypass" in stages_src
    assert "request_container" in stages_src
    # Sync-Flow ruft die Stage auf
    sync_src = _src("core/orchestrator_sync_flow_utils.py")
    assert "run_tool_selection_stage" in sync_src


def test_bypass_injects_exactly_core_tools():
    """Bypass muss request_container, run_skill, home_write enthalten (home_write im else-Zweig)."""
    src = _src("core/orchestrator_pipeline_stages.py")
    # home_write muss im else-Zweig (ohne Konversationskontext) vorhanden sein
    bypass_idx = src.find('selected_tools = ["request_container", "run_skill", "home_write"]')
    assert bypass_idx != -1, "Bypass injection list (else-Zweig) not found in pipeline_stages"
    # Und der Kontext-aware Zweig muss auch existieren
    ctx_bypass_idx = src.find('selected_tools = ["request_container", "run_skill"]')
    assert ctx_bypass_idx != -1, "Context-aware bypass (ohne home_write) not found in pipeline_stages"


def test_stream_flow_has_plan_bypass_after_thinking():
    """pipeline_stages muss Short-Input Plan Bypass enthalten; Stream-Flow muss run_plan_finalization aufrufen."""
    stages_src = _src("core/orchestrator_pipeline_stages.py")
    assert "Short-Input Plan Bypass" in stages_src
    assert 'thinking_plan["suggested_tools"] = list(selected_tools)' in stages_src
    stream_src = _src("core/orchestrator_stream_flow_utils.py")
    assert "run_plan_finalization" in stream_src


def test_sync_flow_has_plan_bypass_after_thinking():
    """pipeline_stages muss Short-Input Plan Bypass enthalten; Sync-Flow muss run_plan_finalization aufrufen."""
    stages_src = _src("core/orchestrator_pipeline_stages.py")
    assert "Short-Input Plan Bypass" in stages_src
    assert 'thinking_plan["suggested_tools"] = list(selected_tools)' in stages_src
    sync_src = _src("core/orchestrator_sync_flow_utils.py")
    assert "run_plan_finalization" in sync_src


def test_stream_flow_enriches_thinking_user_text():
    """Variante A: analyze_stream muss bei kurzem Input angereicherten user_text erhalten."""
    src = _src("core/orchestrator_stream_flow_utils.py")
    assert "A-Enrichment" in src
    assert "_thinking_user_text" in src
    assert "[Kontext:" in src
    assert "_last_assistant_msg" in src
    # analyze_stream muss _thinking_user_text bekommen, nicht user_text
    analyze_idx = src.find("orch.thinking.analyze_stream(")
    assert analyze_idx != -1
    # The first argument after the opening paren should be _thinking_user_text
    call_block = src[analyze_idx:analyze_idx + 200]
    assert "_thinking_user_text" in call_block


def test_sync_flow_enriches_thinking_user_text():
    """Variante A: analyze muss bei kurzem Input angereicherten user_text erhalten."""
    src = _src("core/orchestrator_sync_flow_utils.py")
    assert "A-Enrichment" in src
    assert "_thinking_user_text" in src
    assert "[Kontext:" in src
    analyze_idx = src.find("orch.thinking.analyze(")
    assert analyze_idx != -1
    call_block = src[analyze_idx:analyze_idx + 200]
    assert "_thinking_user_text" in call_block
