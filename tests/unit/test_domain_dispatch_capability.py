"""Tests fuer domain_dispatch.dispatch_by_capability() + resolver-Integration."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import pytest

from core.task_loop.action_resolution.contracts import (
    ActionResolutionMode,
    ActionResolutionSource,
)
from core.task_loop.action_resolution.domain_dispatch import dispatch_by_capability
from core.task_loop.action_resolution.resolver import resolve_next_loop_action


# ---------------------------------------------------------------------------
# Minimaler StepRequest-Stub
# ---------------------------------------------------------------------------

@dataclass
class _StepRequest:
    step_title: str = ""
    step_description: str = ""
    objective: str = ""
    suggested_tools: list = field(default_factory=list)
    requested_capability: dict = field(default_factory=dict)
    capability_context: dict = field(default_factory=dict)
    step_type: str = ""


# ---------------------------------------------------------------------------
# dispatch_by_capability — direkt
# ---------------------------------------------------------------------------

class TestDispatchByCapability:
    def test_cron_intent_dispatches_cron(self):
        req = _StepRequest(step_title="Starte jede Stunde einen Sync")
        dec = dispatch_by_capability(req)
        assert dec is not None
        assert dec.source == ActionResolutionSource.DOMAIN_DISPATCH
        assert dec.action.requested_capability["capability_type"] == "cron"

    def test_container_intent_dispatches_container(self):
        req = _StepRequest(step_title="Starte einen Python-Container fuer den Parser")
        dec = dispatch_by_capability(req)
        assert dec is not None
        assert dec.action.requested_capability["capability_type"] == "container_manager"

    def test_skill_intent_dispatches_skill(self):
        req = _StepRequest(step_title="Fuehre den ingest skill aus")
        dec = dispatch_by_capability(req)
        assert dec is not None
        assert dec.action.requested_capability["capability_type"] == "skill"

    def test_mcp_intent_dispatches_mcp(self):
        req = _StepRequest(step_title="Nutze das MCP-Tool zum Speichern")
        dec = dispatch_by_capability(req)
        assert dec is not None
        assert dec.action.requested_capability["capability_type"] == "mcp"

    def test_direct_intent_dispatches_direct(self):
        req = _StepRequest(step_title="Erklaer mir kurz den Unterschied")
        dec = dispatch_by_capability(req)
        assert dec is not None
        assert dec.action.requested_capability["capability_type"] == "direct"
        assert dec.action.step_type == "chat"
        assert dec.action.suggested_tools == []

    def test_empty_title_returns_none(self):
        req = _StepRequest(step_title="")
        assert dispatch_by_capability(req) is None

    def test_decision_carries_assessment_metadata(self):
        req = _StepRequest(step_title="Starte jede Stunde einen Sync")
        dec = dispatch_by_capability(req)
        assert dec is not None
        meta = dec.action.metadata["tool_utility_assessment"]
        assert "capability" in meta
        assert "confidence" in meta
        assert "scores" in meta
        assert "rationale" in meta

    def test_execution_mode_persistent_for_cron(self):
        req = _StepRequest(step_title="Starte jede Stunde einen Sync")
        dec = dispatch_by_capability(req)
        assert dec.action.requested_capability["execution_mode"] == "persistent"

    def test_execution_mode_one_shot_for_container(self):
        req = _StepRequest(step_title="Starte einen Python-Container fuer den Parser")
        dec = dispatch_by_capability(req)
        assert dec.action.requested_capability["execution_mode"] == "one_shot"

    def test_rationale_contains_confidence(self):
        req = _StepRequest(step_title="Starte jede Stunde einen Sync")
        dec = dispatch_by_capability(req)
        assert any("confidence" in r for r in dec.rationale)

    def test_resolved_true(self):
        req = _StepRequest(step_title="Fuehre den ingest skill aus")
        dec = dispatch_by_capability(req)
        assert dec.resolved is True

    def test_mode_is_execute_existing_step(self):
        req = _StepRequest(step_title="Fuehre den ingest skill aus")
        dec = dispatch_by_capability(req)
        assert dec.action.mode == ActionResolutionMode.EXECUTE_EXISTING_STEP

    def test_description_used_as_fallback(self):
        req = _StepRequest(step_title="", step_description="Fuehre den ingest skill aus")
        dec = dispatch_by_capability(req)
        assert dec is not None
        assert dec.action.requested_capability["capability_type"] == "skill"

    def test_force_capability_context(self):
        req = _StepRequest(step_title="Erklaer mir was Docker ist")
        dec = dispatch_by_capability(req, context={"force_capability": "cron"})
        assert dec is not None
        assert dec.action.requested_capability["capability_type"] == "cron"


# ---------------------------------------------------------------------------
# resolver-Integration: dispatch greift wenn kein requested_capability
# ---------------------------------------------------------------------------

class TestResolverDispatchIntegration:
    def _snapshot(self) -> Any:
        class _Snap:
            conversation_id = "test"
            history = []
        return _Snap()

    def test_resolver_dispatches_cron_when_no_capability(self):
        req = _StepRequest(step_title="Starte jede Stunde einen Sync")
        dec = resolve_next_loop_action(snapshot=self._snapshot(), step_request=req)
        assert dec.resolved is True
        assert dec.source == ActionResolutionSource.DOMAIN_DISPATCH
        assert dec.action.requested_capability["capability_type"] == "cron"

    def test_resolver_dispatches_skill_when_no_capability(self):
        req = _StepRequest(step_title="Fuehre den ingest skill aus")
        dec = resolve_next_loop_action(snapshot=self._snapshot(), step_request=req)
        assert dec.resolved is True
        assert dec.action.requested_capability["capability_type"] == "skill"

    def test_resolver_prefers_existing_capability_over_dispatch(self):
        req = _StepRequest(
            step_title="Fuehre den ingest skill aus",
            requested_capability={"capability_type": "container_manager"},
        )
        dec = resolve_next_loop_action(snapshot=self._snapshot(), step_request=req)
        # existing metadata wins — dispatch is never reached
        assert dec.source != ActionResolutionSource.DOMAIN_DISPATCH
        assert dec.action.requested_capability["capability_type"] == "container_manager"

    def test_resolver_auto_clarify_fallback_for_no_intent_and_no_capability(self):
        # Kein Intent + keine Capability → dispatch gibt None, auto_clarify greift als Fallback
        req = _StepRequest(step_title="")
        dec = resolve_next_loop_action(snapshot=self._snapshot(), step_request=req)
        # auto_clarify gibt immer eine Entscheidung (ASK_USER als generischer Fallback)
        assert dec.resolved is True
        assert dec.source == ActionResolutionSource.AUTO_CLARIFY_POLICY
