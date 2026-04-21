"""Tests fuer cron_mode_guard.assess_cron_mode()."""
from __future__ import annotations

import pytest

from core.orchestrator_modules.policy.cron_mode_guard import (
    CronModeConfirmation,
    assess_cron_mode,
)


class TestAssessCronMode:
    def test_hourly_sync_is_persistent(self):
        r = assess_cron_mode("Starte jede Stunde einen Sync")
        assert r.is_persistent is True
        assert r.is_cron_intent is True

    def test_daily_report_is_persistent(self):
        r = assess_cron_mode("Erstelle täglich um 8 einen Bericht")
        assert r.is_persistent is True

    def test_nightly_job_is_persistent(self):
        r = assess_cron_mode("Run the nightly cleanup job")
        assert r.is_persistent is True

    def test_one_shot_container_not_persistent(self):
        r = assess_cron_mode("Starte einen Python-Container fuer den Parser")
        assert r.is_persistent is False
        assert r.is_cron_intent is False

    def test_explain_not_persistent(self):
        r = assess_cron_mode("Erklaer mir kurz den Unterschied")
        assert r.is_persistent is False

    def test_empty_text_returns_zero_confidence(self):
        r = assess_cron_mode("")
        assert r.confidence == 0.0
        assert r.is_persistent is False

    def test_returns_dataclass(self):
        r = assess_cron_mode("Starte jede Stunde einen Sync")
        assert isinstance(r, CronModeConfirmation)

    def test_confidence_in_range(self):
        r = assess_cron_mode("Starte jede Stunde einen Sync")
        assert 0.0 <= r.confidence <= 1.0

    def test_rationale_not_empty_for_real_intent(self):
        r = assess_cron_mode("Starte jede Stunde einen Sync")
        assert len(r.rationale) > 0

    def test_execution_mode_persistent_string(self):
        r = assess_cron_mode("Starte jede Stunde einen Sync")
        assert r.execution_mode == "persistent"

    def test_execution_mode_one_shot_string(self):
        r = assess_cron_mode("Fuehre das einmal sofort aus")
        assert r.execution_mode == "one_shot"

    def test_einmalig_not_persistent(self):
        r = assess_cron_mode("Einmalig diesen Report erzeugen")
        assert r.is_persistent is False


class TestCronObjectiveIntegration:
    """Sichert dass _build_cron_objective das one_shot_intent-Praefix setzt."""

    def _build(self, text: str) -> str:
        from core.orchestrator_modules.policy.cron_intent import (
            build_cron_objective,
            looks_like_self_state_request,
        )
        from core.orchestrator_modules.policy.cron_mode_guard import assess_cron_mode

        mode = assess_cron_mode(text)
        base = build_cron_objective(
            text,
            looks_like_self_state_request_fn=looks_like_self_state_request,
        )
        if not mode.is_persistent and mode.confidence >= 0.3:
            return f"one_shot_intent::{base}"
        return base

    def test_recurring_intent_no_prefix(self):
        obj = self._build("Starte jede Stunde einen Sync")
        assert not obj.startswith("one_shot_intent::")

    def test_one_shot_intent_gets_prefix(self):
        # Container + einmalig: klare Capability + one_shot → Confidence > 0.3 → Prefix
        obj = self._build("Starte den Python-Container einmalig und beende ihn danach")
        assert obj.startswith("one_shot_intent::")

    def test_objective_still_contains_base(self):
        obj = self._build("Fuehre das einmal sofort aus")
        assert "::" in obj
