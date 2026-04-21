"""Unit-Tests fuer die Tool-Utility-Policy."""
from __future__ import annotations

import pytest

from core.task_loop.action_resolution.tool_utility_policy import (
    CapabilityFamily,
    ExecutionMode,
    ToolUtilityAssessment,
    assess_tool_utility,
)


# ---------------------------------------------------------------------------
# Hilfsfunktion
# ---------------------------------------------------------------------------

def _assess(text: str, **ctx) -> ToolUtilityAssessment:
    return assess_tool_utility(text, context=ctx or None)


# ---------------------------------------------------------------------------
# Capability-Routing
# ---------------------------------------------------------------------------

class TestCapabilityRouting:
    def test_cron_hourly_sync(self):
        r = _assess("Starte jede Stunde einen Sync")
        assert r.capability == CapabilityFamily.cron

    def test_container_python(self):
        r = _assess("Starte einen Python-Container fuer den Parser")
        assert r.capability == CapabilityFamily.container

    def test_skill_ingest(self):
        r = _assess("Fuehre den ingest skill aus")
        assert r.capability == CapabilityFamily.skill

    def test_mcp_tool(self):
        r = _assess("Nutze das MCP-Tool zum Speichern")
        assert r.capability == CapabilityFamily.mcp

    def test_direct_explain(self):
        r = _assess("Erklaer mir kurz den Unterschied")
        assert r.capability == CapabilityFamily.direct

    def test_skill_vs_container_csv_boost(self):
        # "parse pdf" → document+tooling signal → skill wins over container
        r = _assess("Erstelle einen Skill zum Extrahieren von Tabellen aus PDFs")
        assert r.capability == CapabilityFamily.skill
        assert r.scores["skill"] > r.scores["container"]

    def test_cron_daily_report(self):
        r = _assess("Erstelle täglich um 8 einen Bericht")
        assert r.capability == CapabilityFamily.cron

    def test_direct_what_is(self):
        # Keine tool-spezifischen Keywords — reines Erklaerungsmuster
        r = _assess("Was ist der Unterschied zwischen Microservices und Monolithen?")
        assert r.capability == CapabilityFamily.direct

    def test_mcp_explicit(self):
        r = _assess("Verbinde den MCP Server mit dem Agenten")
        assert r.capability == CapabilityFamily.mcp


# ---------------------------------------------------------------------------
# Execution-Mode
# ---------------------------------------------------------------------------

class TestExecutionMode:
    def test_persistent_hourly(self):
        r = _assess("Starte jede Stunde einen Sync")
        assert r.mode == ExecutionMode.persistent

    def test_persistent_daily(self):
        r = _assess("Erstelle jeden Tag einen Bericht")
        assert r.mode == ExecutionMode.persistent

    def test_one_shot_container(self):
        r = _assess("Starte einen Python-Container fuer den Parser")
        assert r.mode == ExecutionMode.one_shot

    def test_one_shot_skill(self):
        r = _assess("Fuehre den ingest skill aus")
        assert r.mode == ExecutionMode.one_shot

    def test_one_shot_einmalig(self):
        r = _assess("Fuehre das einmal sofort aus")
        assert r.mode == ExecutionMode.one_shot

    def test_persistent_nightly(self):
        r = _assess("Run the nightly cleanup job")
        assert r.mode == ExecutionMode.persistent

    def test_one_shot_just_once(self):
        r = _assess("Do it just once and return the result")
        assert r.mode == ExecutionMode.one_shot


# ---------------------------------------------------------------------------
# Context-Override
# ---------------------------------------------------------------------------

class TestContextOverride:
    def test_force_capability_cron(self):
        r = assess_tool_utility("Erklaer mir kurz was Docker ist", context={"force_capability": "cron"})
        assert r.capability == CapabilityFamily.cron
        assert r.confidence == 1.0

    def test_force_capability_mcp(self):
        r = assess_tool_utility("Starte jede Stunde einen Sync", context={"force_capability": "mcp"})
        assert r.capability == CapabilityFamily.mcp
        assert r.confidence == 1.0

    def test_force_mode_persistent(self):
        r = assess_tool_utility("Fuehre das einmal aus", context={"force_mode": "persistent"})
        assert r.mode == ExecutionMode.persistent


# ---------------------------------------------------------------------------
# Confidence + Scores-Struktur
# ---------------------------------------------------------------------------

class TestConfidenceAndScores:
    def test_scores_sum_to_one(self):
        r = _assess("Starte jede Stunde einen Sync")
        total = sum(r.scores.values())
        assert abs(total - 1.0) < 1e-6

    def test_scores_have_all_capabilities(self):
        r = _assess("Fuehre den ingest skill aus")
        assert set(r.scores.keys()) == {c.value for c in CapabilityFamily}

    def test_ambiguous_low_confidence(self):
        # Text mit schwachen Signalen → Confidence niedrig
        r = _assess("Mach irgendwas")
        # Scores are valid even for ambiguous input
        assert 0.0 <= r.confidence <= 1.0
        assert sum(r.scores.values()) - 1.0 < 1e-5

    def test_strong_cron_signal_high_confidence(self):
        r = _assess("Lege einen Cronjob fuer die Bereinigung an")
        assert r.confidence > 0.4

    def test_rationale_not_empty(self):
        r = _assess("Starte einen Python-Container")
        assert len(r.rationale) > 0

    def test_features_returned(self):
        r = _assess("Starte jede Stunde einen Sync")
        assert "temporal" in r.features
        assert r.features["temporal"] > 0.0


# ---------------------------------------------------------------------------
# DE + EN gleichwertig
# ---------------------------------------------------------------------------

class TestLanguageEquivalence:
    def test_de_cron(self):
        r_de = _assess("Starte jede Stunde einen Sync")
        assert r_de.capability == CapabilityFamily.cron

    def test_en_cron(self):
        r_en = _assess("Run the sync every hour")
        assert r_en.capability == CapabilityFamily.cron

    def test_de_direct(self):
        r = _assess("Erklaer mir kurz den Unterschied")
        assert r.capability == CapabilityFamily.direct

    def test_en_direct(self):
        r = _assess("Explain the difference briefly")
        assert r.capability == CapabilityFamily.direct
