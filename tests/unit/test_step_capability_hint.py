"""Tests fuer capability_hint.suggest_capability_for_step()."""
from __future__ import annotations

import pytest

from core.task_loop.step_runtime.capability_hint import suggest_capability_for_step


class TestSuggestCapabilityForStep:
    def test_cron_title_returns_cron(self):
        hint = suggest_capability_for_step("Starte jede Stunde einen Sync", {})
        assert hint is not None
        assert hint["capability_type"] == "cron"
        assert hint["execution_mode"] == "persistent"

    def test_skill_title_returns_skill(self):
        hint = suggest_capability_for_step("Fuehre den ingest skill aus", {})
        assert hint is not None
        assert hint["capability_type"] == "skill"

    def test_container_title_returns_container(self):
        hint = suggest_capability_for_step("Starte einen Python-Container fuer den Parser", {})
        assert hint is not None
        assert hint["capability_type"] == "container_manager"

    def test_mcp_title_returns_mcp(self):
        hint = suggest_capability_for_step("Nutze das MCP-Tool zum Speichern", {})
        assert hint is not None
        assert hint["capability_type"] == "mcp"

    def test_direct_title_returns_direct(self):
        hint = suggest_capability_for_step("Erklaer mir kurz den Unterschied", {})
        assert hint is not None
        assert hint["capability_type"] == "direct"

    def test_existing_capability_returns_none(self):
        meta = {"requested_capability": {"capability_type": "container_manager"}}
        hint = suggest_capability_for_step("Starte jede Stunde einen Sync", meta)
        assert hint is None

    def test_empty_title_returns_none(self):
        assert suggest_capability_for_step("", {}) is None

    def test_hint_source_metadata_present(self):
        hint = suggest_capability_for_step("Fuehre den ingest skill aus", {})
        assert hint is not None
        assert hint["_hint_source"] == "capability_hint_policy"
        assert 0.0 <= hint["_hint_confidence"] <= 1.0

    def test_goal_used_as_fallback(self):
        hint = suggest_capability_for_step("", {"goal": "Fuehre den ingest skill aus"})
        assert hint is not None
        assert hint["capability_type"] == "skill"

    def test_objective_used_as_fallback(self):
        hint = suggest_capability_for_step("", {"objective": "Starte jede Stunde einen Sync"})
        assert hint is not None
        assert hint["capability_type"] == "cron"

    def test_empty_dict_capability_triggers_hint(self):
        # leeres dict gilt als "kein capability"
        meta = {"requested_capability": {}}
        hint = suggest_capability_for_step("Fuehre den ingest skill aus", meta)
        assert hint is not None
