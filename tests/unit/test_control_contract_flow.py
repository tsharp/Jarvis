from dataclasses import FrozenInstanceError
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from core.control_contract import ControlDecision
from core.layers.control import ControlLayer
from core.layers.output import OutputLayer


def _make_orchestrator():
    from core.orchestrator import PipelineOrchestrator

    with patch("core.orchestrator.ThinkingLayer", return_value=MagicMock()), \
         patch("core.orchestrator.ControlLayer", return_value=MagicMock()), \
         patch("core.orchestrator.OutputLayer", return_value=MagicMock()), \
         patch("core.orchestrator.ToolSelector", return_value=MagicMock()), \
         patch("core.orchestrator.ContextManager", return_value=MagicMock()), \
         patch("core.orchestrator.get_hub", return_value=MagicMock()), \
         patch("core.orchestrator.get_registry", return_value=MagicMock()), \
         patch("core.orchestrator.get_master_orchestrator", return_value=MagicMock()):
        return PipelineOrchestrator()


def test_control_decision_is_immutable():
    decision = ControlDecision.from_verification(
        {
            "approved": True,
            "decision_class": "allow",
            "warnings": ["ok"],
        }
    )
    with pytest.raises(FrozenInstanceError):
        decision.approved = False


def test_control_container_candidate_resolution_skips_trion_home_fast_path():
    layer = ControlLayer()
    verification = {
        "approved": True,
        "hard_block": False,
        "decision_class": "allow",
        "corrections": {},
        "warnings": [],
        "final_instruction": "",
    }
    thinking_plan = {
        "suggested_tools": ["home_start"],
        "_trion_home_start_fast_path": True,
    }

    out = layer._apply_container_candidate_resolution(
        verification,
        thinking_plan,
        user_text="starte bitte den TRION Home Workspace",
    )

    assert out["approved"] is True
    assert out["decision_class"] == "allow"
    assert out.get("suggested_tools") is None


@pytest.mark.asyncio
async def test_execute_control_layer_persists_typed_contracts():
    orch = _make_orchestrator()
    orch.control.verify = AsyncMock(
        return_value={
            "approved": True,
            "hard_block": False,
            "decision_class": "allow",
            "block_reason_code": "",
            "reason": "ok",
            "corrections": {},
            "warnings": [],
            "final_instruction": "",
        }
    )
    orch.control.apply_corrections = MagicMock(side_effect=lambda tp, _: dict(tp))

    verification, verified_plan = await orch._execute_control_layer(
        user_text="Bitte nutze tools",
        thinking_plan={"intent": "tool", "hallucination_risk": "medium", "suggested_tools": ["list_skills"]},
        memory_data="",
        conversation_id="conv-1",
    )

    assert verification["approved"] is True
    assert isinstance(verified_plan.get("_control_decision"), dict)
    assert verified_plan["_control_decision"]["approved"] is True
    assert isinstance(verified_plan.get("_execution_result"), dict)
    assert verified_plan["_execution_result"]["done_reason"] == "stop"


@pytest.mark.asyncio
async def test_execute_control_layer_materializes_skill_catalog_policy_contract():
    orch = _make_orchestrator()
    orch.control.verify = AsyncMock(
        return_value={
            "approved": True,
            "hard_block": False,
            "decision_class": "allow",
            "block_reason_code": "",
            "reason": "ok",
            "corrections": {
                "resolution_strategy": "skill_catalog_context",
                "_authoritative_resolution_strategy": "skill_catalog_context",
            },
            "warnings": [],
            "final_instruction": "",
        }
    )
    orch.control.apply_corrections = MagicMock(
        side_effect=lambda tp, verification: {
            **tp,
            **verification.get("corrections", {}),
        }
    )

    _, verified_plan = await orch._execute_control_layer(
        user_text="Welche Draft-Skills gibt es gerade und warum list_skills sie nicht anzeigt?",
        thinking_plan={
            "intent": "skill catalog",
            "hallucination_risk": "low",
            "is_fact_query": True,
            "resolution_strategy": "skill_catalog_context",
            "strategy_hints": ["draft_skills", "tools_vs_skills", "answering_rules"],
            "suggested_tools": ["list_draft_skills", "list_skills"],
        },
        memory_data="",
        conversation_id="conv-skill-policy",
    )

    assert verified_plan["_skill_catalog_policy"]["mode"] == "inventory_read_only"
    assert verified_plan["_skill_catalog_policy"]["required_tools"] == [
        "list_draft_skills",
        "list_skills",
    ]
    assert verified_plan["_skill_catalog_policy"]["force_sections"] == [
        "Runtime-Skills",
        "Einordnung",
    ]
    assert verified_plan["_skill_catalog_policy"]["draft_explanation_required"] is True
    assert verified_plan["_skill_catalog_policy"]["allow_sequential"] is False


@pytest.mark.asyncio
async def test_execute_control_layer_materializes_container_query_policy_contract():
    orch = _make_orchestrator()
    orch.control.verify = AsyncMock(
        return_value={
            "approved": True,
            "hard_block": False,
            "decision_class": "allow",
            "block_reason_code": "",
            "reason": "ok",
            "corrections": {
                "resolution_strategy": "container_inventory",
                "_authoritative_resolution_strategy": "container_inventory",
            },
            "warnings": [],
            "final_instruction": "",
        }
    )
    orch.control.apply_corrections = MagicMock(
        side_effect=lambda tp, verification: {
            **tp,
            **verification.get("corrections", {}),
        }
    )

    _, verified_plan = await orch._execute_control_layer(
        user_text="Welche Container laufen gerade?",
        thinking_plan={
            "intent": "container inventory",
            "hallucination_risk": "low",
            "is_fact_query": True,
            "resolution_strategy": "container_inventory",
            "suggested_tools": ["container_list"],
        },
        memory_data="",
        conversation_id="conv-container-policy",
    )

    assert verified_plan["_container_query_policy"]["query_class"] == "container_inventory"
    assert verified_plan["_container_query_policy"]["required_tools"] == ["container_list"]
    assert verified_plan["_container_query_policy"]["truth_mode"] == "runtime_inventory"


def test_execute_tools_sync_respects_control_tools_allowed():
    orch = _make_orchestrator()

    class _FakeHub:
        def initialize(self):
            return None

        def call_tool(self, *_args, **_kwargs):
            raise AssertionError("tool must not be called when blocked by control_decision")

    with patch("core.orchestrator.get_hub", return_value=_FakeHub()):
        plan = {}
        control_decision = ControlDecision.from_verification(
            {
                "approved": True,
                "decision_class": "allow",
                "tools_allowed": ["list_skills"],
            }
        )
        tool_context = orch._execute_tools_sync(
            ["exec_in_container"],
            "Bitte exec",
            control_tool_decisions={"exec_in_container": {"container_id": "x", "command": "hostname -I"}},
            control_decision=control_decision,
            verified_plan=plan,
            session_id="conv-2",
        )

    assert tool_context == ""
    execution_result = plan.get("_execution_result", {})
    assert execution_result.get("done_reason") == "routing_block"
    statuses = execution_result.get("tool_statuses", [])
    assert statuses and statuses[0].get("reason") == "control_tool_not_allowed"


def test_output_precheck_writes_runtime_grounding_state():
    output = OutputLayer()
    plan = {
        "is_fact_query": True,
        "_tool_results": "TOOL used",
        "_selected_tools_for_prompt": ["container_inspect"],
        "_grounding_evidence": [],
    }
    execution_result = {}

    precheck = output._grounding_precheck(plan, memory_data="", execution_result=execution_result)

    assert precheck["mode"] in {"missing_evidence_fallback", "tool_execution_failed_fallback", "pass", "evidence_summary_fallback"}
    grounding = execution_result.get("grounding", {})
    assert "missing_evidence" in grounding
    assert "successful_evidence" in grounding


def test_control_default_verification_is_fail_closed():
    layer = ControlLayer()
    verification = layer._default_verification({"intent": "x"})
    assert verification["approved"] is False
    assert verification["hard_block"] is True
    assert verification["decision_class"] == "hard_block"


def test_apply_corrections_prefers_authoritative_suggested_tools():
    layer = ControlLayer()
    corrected = layer.apply_corrections(
        {"suggested_tools": ["request_container"]},
        {
            "corrections": {},
            "warnings": [],
            "suggested_tools": ["blueprint_list"],
            "_authoritative_suggested_tools": ["blueprint_list"],
            "final_instruction": "",
        },
    )

    assert corrected["suggested_tools"] == ["blueprint_list"]
    assert corrected["_authoritative_suggested_tools"] == ["blueprint_list"]


def test_control_stabilize_verification_promotes_authoritative_resolution_strategy():
    layer = ControlLayer()
    verification = layer._stabilize_verification_result(
        {
            "approved": True,
            "hard_block": False,
            "decision_class": "allow",
            "corrections": {},
            "warnings": [],
            "final_instruction": "",
            "suggested_tools": [],
        },
        {
            "intent": "container capabilities",
            "is_fact_query": True,
            "resolution_strategy": "active_container_capability",
            "suggested_tools": ["container_stats", "exec_in_container"],
            "_domain_route": {"domain_tag": "CONTAINER", "domain_locked": True},
        },
        user_text="Was kannst du in diesem container alles tun?",
    )

    assert verification["corrections"]["resolution_strategy"] == "active_container_capability"
    assert verification["corrections"]["_authoritative_resolution_strategy"] == "active_container_capability"
    assert verification["_authoritative_resolution_strategy"] == "active_container_capability"


def test_control_stabilize_verification_promotes_skill_catalog_context_strategy():
    layer = ControlLayer()
    verification = layer._stabilize_verification_result(
        {
            "approved": True,
            "hard_block": False,
            "decision_class": "allow",
            "corrections": {},
            "warnings": [],
            "final_instruction": "",
            "suggested_tools": [],
        },
        {
            "intent": "skill taxonomy",
            "is_fact_query": True,
            "resolution_strategy": "skill_catalog_context",
            "strategy_hints": ["tools_vs_skills", "answering_rules"],
            "suggested_tools": ["list_skills"],
            "_domain_route": {"domain_tag": "SKILL", "domain_locked": True},
        },
        user_text="Was ist der Unterschied zwischen Tools und Skills?",
    )

    assert verification["corrections"]["resolution_strategy"] == "skill_catalog_context"
    assert verification["corrections"]["_authoritative_resolution_strategy"] == "skill_catalog_context"
    assert verification["_authoritative_resolution_strategy"] == "skill_catalog_context"


def test_resolve_execution_suggested_tools_prefers_authoritative_control_set():
    orch = _make_orchestrator()
    orch._normalize_tools = MagicMock(side_effect=lambda tools: list(tools))
    orch._prioritize_home_container_tools = MagicMock(side_effect=lambda *_args, **_kwargs: _args[2])
    plan = {
        "suggested_tools": ["request_container"],
        "_authoritative_suggested_tools": ["blueprint_list"],
    }
    control_decision = ControlDecision.from_verification(
        {
            "approved": True,
            "decision_class": "warn",
            "tools_allowed": ["blueprint_list"],
        }
    )

    out = orch._resolve_execution_suggested_tools(
        user_text="starte bitte den Workspace",
        verified_plan=plan,
        control_tool_decisions={},
        control_decision=control_decision,
        stream=True,
    )

    assert out == ["blueprint_list"]


def test_resolve_execution_suggested_tools_prefers_authoritative_resolution_strategy():
    orch = _make_orchestrator()
    orch._remember_container_state(
        "conv-strategy",
        last_active_container_id="ctr-1",
        known_containers=[
            {
                "container_id": "ctr-1",
                "blueprint_id": "trion-home",
                "status": "running",
                "name": "trion-home",
            }
        ],
    )
    with patch.object(orch, "_normalize_tools", side_effect=lambda tools: list(tools)), \
         patch.object(orch, "_prioritize_home_container_tools", side_effect=lambda *_args, **_kwargs: _args[2]), \
         patch.object(orch, "_apply_query_budget_tool_policy", side_effect=lambda *_args, **_kwargs: _args[2]), \
         patch.object(orch, "_apply_domain_tool_policy", side_effect=lambda *_args, **_kwargs: _args[1]):
        out = orch._resolve_execution_suggested_tools(
            user_text="was kannst du hier alles tun?",
            verified_plan={
                "suggested_tools": ["container_stats", "exec_in_container"],
                "is_fact_query": True,
                "_authoritative_resolution_strategy": "active_container_capability",
            },
            control_tool_decisions={},
            stream=False,
            conversation_id="conv-strategy",
        )

    assert out == ["container_inspect"]
