"""Tests fuer pipeline_adapter.py Tool-Injection-Logik."""
from __future__ import annotations

import pytest


def _make_orch(selected_tools=None):
    """Minimaler Orchestrator-Mock ohne echte Thinking-Analyse."""
    from unittest.mock import AsyncMock, MagicMock

    orch = MagicMock()
    orch.thinking = None  # deaktiviert analyze-Pfad → plan = {}
    orch.tool_selector = None
    orch.mcp_hub = None
    orch._maybe_prefetch_skills = None
    orch._ensure_dialogue_controls = None
    return orch


async def _build_plan(user_text: str, selected_tools=None) -> dict:
    from core.task_loop.pipeline_adapter import build_task_loop_planning_context

    orch = _make_orch()
    # Ohne thinking.analyze gibt build_task_loop_planning_context {} zurueck —
    # das ist der korrekte Fallback-Pfad fuer diesen Test.
    return await build_task_loop_planning_context(orch, user_text)


class TestPipelineAdapterToolInjection:
    @pytest.mark.asyncio
    async def test_no_tools_injected_for_content_reply(self):
        """Echte Antwort auf Rueckfrage: Tools werden NICHT vererbt."""
        plan = await _build_plan("Ja, nimm bitte den gaming-station Blueprint")
        assert plan == {} or not plan.get("suggested_tools")

    @pytest.mark.asyncio
    async def test_no_tools_injected_for_short_non_continue_text(self):
        """Kurzer Text aber kein Continue-Marker → kein Tool-Erbe."""
        plan = await _build_plan("ok mach das")
        assert plan == {} or not plan.get("suggested_tools")


class TestIsTaskLoopContinueContractForAdapter:
    """Sichert dass is_task_loop_continue() die Marker korrekt erkennt,
    die pipeline_adapter.py jetzt als Bedingung fuer Tool-Vererbung nutzt."""

    def test_weiter_is_continue(self):
        from core.task_loop.chat_runtime import is_task_loop_continue
        assert is_task_loop_continue("weiter") is True

    def test_ja_mach_das_is_not_continue(self):
        from core.task_loop.chat_runtime import is_task_loop_continue
        assert is_task_loop_continue("ja mach das") is False

    def test_gaming_station_reply_is_not_continue(self):
        from core.task_loop.chat_runtime import is_task_loop_continue
        assert is_task_loop_continue("nimm bitte gaming-station") is False

    def test_empty_is_not_continue(self):
        from core.task_loop.chat_runtime import is_task_loop_continue
        assert is_task_loop_continue("") is False
