"""Tests fuer tool_catalog.suggest_tools_for_step()."""
from __future__ import annotations

import pytest

from core.task_loop.action_resolution.tool_utility_policy.tool_catalog import (
    DISCOVERY_TOOLS,
    is_discovery_only,
    suggest_tools_for_step,
)


class TestDiscoveryFallback:
    def test_skill_discovery(self):
        assert suggest_tools_for_step("skill", "") == ["list_skills"]

    def test_container_discovery(self):
        assert suggest_tools_for_step("container_manager", "") == ["container_list"]

    def test_cron_discovery(self):
        result = suggest_tools_for_step("cron", "")
        assert "autonomy_cron_status" in result
        assert "autonomy_cron_list_jobs" in result

    def test_direct_returns_empty(self):
        assert suggest_tools_for_step("direct", "") == []

    def test_mcp_returns_empty(self):
        assert suggest_tools_for_step("mcp", "") == []

    def test_unknown_capability_returns_empty(self):
        assert suggest_tools_for_step("something_unknown", "starte alles") == []


class TestSkillActionIntents:
    def test_run_intent(self):
        assert suggest_tools_for_step("skill", "Fuehre den ingest skill aus") == ["run_skill"]

    def test_create_intent_de(self):
        assert suggest_tools_for_step("skill", "Erstelle einen neuen Skill") == ["create_skill"]

    def test_create_intent_en(self):
        assert suggest_tools_for_step("skill", "Create a new skill for PDF parsing") == ["create_skill"]

    def test_info_intent(self):
        assert suggest_tools_for_step("skill", "Zeige Details zum ingest skill") == ["get_skill_info"]

    def test_validate_intent(self):
        assert suggest_tools_for_step("skill", "Validiere den Skill-Code") == ["validate_skill_code"]

    def test_ambiguous_falls_back_to_discovery(self):
        assert suggest_tools_for_step("skill", "Schau mal was los ist") == ["list_skills"]


class TestContainerActionIntents:
    def test_start_intent(self):
        assert suggest_tools_for_step("container_manager", "Starte einen Python-Container") == ["request_container"]

    def test_stop_intent(self):
        assert suggest_tools_for_step("container_manager", "Stoppe den laufenden Container") == ["stop_container"]

    def test_logs_intent(self):
        assert suggest_tools_for_step("container_manager", "Zeige die Logs des Containers") == ["container_logs"]

    def test_stats_intent(self):
        assert suggest_tools_for_step("container_manager", "Zeige CPU und RAM Statistiken") == ["container_stats"]

    def test_exec_intent(self):
        assert suggest_tools_for_step("container_manager", "Fuehre einen Befehl im Container aus") == ["exec_in_container"]

    def test_blueprint_intent(self):
        assert suggest_tools_for_step("container_manager", "Zeige alle Vorlagen") == ["blueprint_list"]

    def test_inspect_intent(self):
        assert suggest_tools_for_step("container_manager", "Inspect Container Details") == ["container_inspect"]

    def test_ambiguous_falls_back_to_discovery(self):
        assert suggest_tools_for_step("container_manager", "Was ist los?") == ["container_list"]


class TestCronActionIntents:
    def test_create_intent_de(self):
        assert suggest_tools_for_step("cron", "Erstelle einen neuen Cronjob") == ["autonomy_cron_create_job"]

    def test_create_intent_en(self):
        assert suggest_tools_for_step("cron", "Schedule a new recurring job") == ["autonomy_cron_create_job"]

    def test_update_intent(self):
        assert suggest_tools_for_step("cron", "Aktualisiere den Cron-Job") == ["autonomy_cron_update_job"]

    def test_delete_intent(self):
        assert suggest_tools_for_step("cron", "Loesche den Job") == ["autonomy_cron_delete_job"]

    def test_pause_intent(self):
        assert suggest_tools_for_step("cron", "Pausiere den Sync-Job") == ["autonomy_cron_pause_job"]

    def test_resume_intent(self):
        assert suggest_tools_for_step("cron", "Reaktiviere den Job") == ["autonomy_cron_resume_job"]

    def test_run_now_intent(self):
        assert suggest_tools_for_step("cron", "Fuehre den Job sofort aus") == ["autonomy_cron_run_now"]

    def test_validate_intent(self):
        assert suggest_tools_for_step("cron", "Validiere den Cron-Ausdruck") == ["autonomy_cron_validate"]

    def test_ambiguous_falls_back_to_discovery(self):
        result = suggest_tools_for_step("cron", "Was laeuft gerade?")
        assert result == ["autonomy_cron_status", "autonomy_cron_list_jobs"]


class TestIsDiscoveryOnly:
    def test_list_skills_is_discovery(self):
        assert is_discovery_only(["list_skills"]) is True

    def test_container_list_is_discovery(self):
        assert is_discovery_only(["container_list"]) is True

    def test_cron_status_is_discovery(self):
        assert is_discovery_only(["autonomy_cron_status"]) is True

    def test_cron_list_jobs_is_discovery(self):
        assert is_discovery_only(["autonomy_cron_list_jobs"]) is True

    def test_multiple_discovery_tools_is_discovery(self):
        assert is_discovery_only(["autonomy_cron_status", "autonomy_cron_list_jobs"]) is True

    def test_request_container_not_discovery(self):
        assert is_discovery_only(["request_container"]) is False

    def test_run_skill_not_discovery(self):
        assert is_discovery_only(["run_skill"]) is False

    def test_mixed_list_not_discovery(self):
        assert is_discovery_only(["list_skills", "run_skill"]) is False

    def test_empty_list_not_discovery(self):
        assert is_discovery_only([]) is False

    def test_discovery_tools_set_contains_expected(self):
        assert "list_skills" in DISCOVERY_TOOLS
        assert "container_list" in DISCOVERY_TOOLS
        assert "autonomy_cron_status" in DISCOVERY_TOOLS
        assert "autonomy_cron_list_jobs" in DISCOVERY_TOOLS

    def test_action_tools_not_in_discovery_set(self):
        assert "run_skill" not in DISCOVERY_TOOLS
        assert "request_container" not in DISCOVERY_TOOLS
        assert "autonomy_cron_create_job" not in DISCOVERY_TOOLS


class TestPlansIntegration:
    """Sichert dass plans.py Phase-2 Tools korrekt befuellt."""

    def _build_plan(self, step_title: str, step_meta: dict) -> dict:
        from unittest.mock import MagicMock
        from core.task_loop.step_runtime.plans import build_task_loop_step_plan

        snapshot = MagicMock()
        snapshot.pending_step = ""
        snapshot.step_index = 0
        snapshot.completed_steps = []
        return build_task_loop_step_plan(step_title, step_meta, snapshot)

    def test_skill_step_gets_list_skills(self):
        plan = self._build_plan("Verfuegbare Skills auflisten", {})
        assert plan.get("suggested_tools") is not None
        tools = plan["suggested_tools"]
        assert "list_skills" in tools

    def test_cron_step_gets_cron_status(self):
        plan = self._build_plan("Cron-Job erstellen fuer sttündlichen Sync", {})
        tools = plan.get("suggested_tools") or []
        assert any("cron" in t for t in tools)

    def test_container_step_gets_container_list(self):
        plan = self._build_plan("Container-Umgebung prüfen", {})
        tools = plan.get("suggested_tools") or []
        assert "container_list" in tools

    def test_explicit_tools_not_overridden(self):
        meta = {"suggested_tools": ["run_skill"]}
        plan = self._build_plan("Skill ausfuehren", meta)
        assert plan.get("suggested_tools") == ["run_skill"]

    def test_explicit_capability_respected(self):
        meta = {"requested_capability": {"capability_type": "container_manager"}}
        plan = self._build_plan("Etwas tun", meta)
        assert plan["requested_capability"]["capability_type"] == "container_manager"
