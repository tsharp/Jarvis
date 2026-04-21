"""Known gap suite for skill-catalog regressions observed in live traces.

These tests intentionally encode currently failing expectations as strict
xfails. They should flip green one by one as we tighten the semantic validator
and contract execution path instead of layering more prompt-only guardrails.
"""

from unittest.mock import MagicMock, patch

import pytest

from core.layers.control import ControlLayer
from core.layers.output import OutputLayer
from core.orchestrator_plan_schema_utils import coerce_thinking_plan_schema


def _policy():
    return {
        "output": {
            "enforce_evidence_for_fact_query": True,
            "enforce_evidence_when_tools_used": True,
            "enforce_evidence_when_tools_suggested": True,
            "min_successful_evidence": 1,
            "allowed_evidence_statuses": ["ok"],
            "fact_query_response_mode": "model",
            "fallback_mode": "explicit_uncertainty",
            "forbid_new_numeric_claims": True,
            "forbid_unverified_qualitative_claims": True,
            "qualitative_claim_guard": {
                "min_token_length": 5,
                "max_overall_novelty_ratio": 0.72,
                "max_sentence_novelty_ratio": 0.82,
                "min_sentence_tokens": 4,
                "min_assertive_sentence_violations": 1,
                "assertive_cues": ["is", "runs", "uses", "ist", "läuft", "nutzt"],
                "ignored_tokens": ["system", "model", "modell"],
            },
        }
    }


def _precheck(evidence):
    return {
        "policy": _policy()["output"],
        "evidence": evidence,
        "is_fact_query": True,
    }


def _plan(*, hints, policy_required_tools):
    return {
        "is_fact_query": True,
        "resolution_strategy": "skill_catalog_context",
        "strategy_hints": list(hints),
        "_skill_catalog_policy": {
            "mode": "inventory_read_only",
            "required_tools": list(policy_required_tools),
            "force_sections": ["Runtime-Skills", "Einordnung"],
            "draft_explanation_required": "draft_skills" in hints or "tools_vs_skills" in hints,
            "followup_split_required": "fact_then_followup" in hints,
            "allow_sequential": False,
            "semantic_guardrails_only": True,
            "selected_hints": list(hints),
        },
        "_skill_catalog_context": {
            "installed_count": 0,
            "selected_doc_ids": ["skill-overview", "skill-answering-rules"],
        },
        "_ctx_trace": {},
    }


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
        orch = PipelineOrchestrator()
    orch._save_workspace_entry = MagicMock(return_value=None)
    return orch


def test_tools_vs_skills_answer_should_flag_capability_style_core_abilities():
    layer = OutputLayer()
    plan = _plan(
        hints=["runtime_skills", "tools_vs_skills", "overview", "skill_taxonomy", "answering_rules"],
        policy_required_tools=["list_skills"],
    )
    evidence = [
        {
            "tool_name": "list_skills",
            "status": "ok",
            "key_facts": [
                "installed_count: 0",
                "available_count: 0",
            ],
        },
        {
            "tool_name": "skill_addons",
            "status": "ok",
            "key_facts": [
                "Built-in Tools sind keine installierten Runtime-Skills.",
                "Wenn Skills mehrdeutig ist, die Mehrdeutigkeit explizit aufloesen statt still eine Ebene zu raten.",
            ],
        },
    ]
    answer = (
        "Runtime-Skills: Im Runtime-Skill-System sind aktuell keine installierten Skills vorhanden. Die Liste der "
        "installierten Runtime-Skills ist leer.\n\n"
        "Einordnung: Neben Runtime-Skills habe ich Zugriff auf Built-in Tools, die direkt in meiner "
        "Basis-Infrastruktur integriert sind – zum Beispiel Python-Skills erstellen/verwalten, "
        "System-Informationen abrufen oder Memory-Funktionen. Diese sind nicht als separate \"Skills\" "
        "installiert, sondern gehören zu meinen Kernfähigkeiten."
    )

    violation = layer._evaluate_skill_catalog_semantic_leakage(answer, plan, evidence)

    assert violation.get("violated") is True


def test_inventory_read_only_answer_should_flag_unsolicited_skill_creation_offer():
    layer = OutputLayer()
    plan = _plan(
        hints=["runtime_skills", "overview", "capabilities", "skill_taxonomy", "answering_rules"],
        policy_required_tools=["list_skills"],
    )
    evidence = [
        {
            "tool_name": "list_skills",
            "status": "ok",
            "key_facts": [
                "installed_count: 0",
                "available_count: 0",
            ],
        },
    ]
    answer = (
        "Runtime-Skills: Im Runtime-Skill-System sind aktuell keine installierten Skills vorhanden.\n"
        "Einordnung: Das bedeutet, dass noch keine zusätzlichen Funktionen aktiviert wurden.\n\n"
        "Möchtest du, dass ich einen speziellen Skill entwickle oder hast du eine konkrete Aufgabe im Sinn?"
    )

    violation = layer._evaluate_skill_catalog_semantic_leakage(answer, plan, evidence)

    assert violation.get("violated") is True


def test_postcheck_should_repair_unverified_draft_claim_without_list_draft_skills_evidence():
    layer = OutputLayer()
    plan = _plan(
        hints=["runtime_skills", "tools_vs_skills", "overview", "skill_taxonomy", "answering_rules"],
        policy_required_tools=["list_skills"],
    )
    evidence = [
        {
            "tool_name": "list_skills",
            "status": "ok",
            "key_facts": [
                "installed_count: 0",
                "available_count: 0",
            ],
        },
        {
            "tool_name": "skill_addons",
            "status": "ok",
            "key_facts": [
                "Built-in Tools sind keine installierten Runtime-Skills.",
            ],
        },
    ]
    answer = (
        "Runtime-Skills: Im Runtime-Skill-System sind aktuell keine installierten Skills vorhanden.\n\n"
        "Einordnung: Der Befehl list_skills zeigt nur installierte Runtime-Skills an. Draft-Skills oder Built-in "
        "Tools sind hier nicht erfasst, da sie separate Ebenen darstellen. Draft-Skills sind aktuell nicht "
        "verifiziert verfügbar, da die Registry keine verfügbaren Skills anzeigt."
    )

    with patch("core.layers.output.layer.load_grounding_policy", return_value=_policy()):
        checked = layer._grounding_postcheck(answer, plan, _precheck(evidence))

    assert checked != answer


def test_postcheck_should_repair_tools_vs_skills_built_in_capability_drift():
    layer = OutputLayer()
    plan = _plan(
        hints=["runtime_skills", "tools_vs_skills", "overview", "skill_taxonomy", "answering_rules"],
        policy_required_tools=["list_skills"],
    )
    evidence = [
        {
            "tool_name": "list_skills",
            "status": "ok",
            "key_facts": [
                "installed_count: 0",
                "available_count: 0",
            ],
        },
        {
            "tool_name": "skill_addons",
            "status": "ok",
            "key_facts": [
                "Built-in Tools sind keine installierten Runtime-Skills.",
                "Wenn Skills mehrdeutig ist, die Mehrdeutigkeit explizit aufloesen statt still eine Ebene zu raten.",
            ],
        },
    ]
    answer = (
        "Runtime-Skills: Im Runtime-Skill-System sind aktuell keine installierten Skills vorhanden. "
        "Die Liste der installierten Runtime-Skills ist leer.\n\n"
        "Einordnung: Neben Runtime-Skills habe ich Zugriff auf Built-in Tools, die direkt in meiner "
        "Basis-Infrastruktur integriert sind – zum Beispiel Python-Skills erstellen/verwalten, "
        "System-Informationen abrufen oder Memory-Funktionen. Diese sind nicht als separate \"Skills\" "
        "installiert, sondern gehören zu meinen Kernfähigkeiten."
    )

    with patch("core.layers.output.layer.load_grounding_policy", return_value=_policy()):
        checked = layer._grounding_postcheck(answer, plan, _precheck(evidence))

    assert checked != answer


def test_postcheck_should_repair_unsolicited_skill_creation_offer():
    layer = OutputLayer()
    plan = _plan(
        hints=["runtime_skills", "overview", "capabilities", "skill_taxonomy", "answering_rules"],
        policy_required_tools=["list_skills"],
    )
    evidence = [
        {
            "tool_name": "list_skills",
            "status": "ok",
            "key_facts": [
                "installed_count: 0",
                "available_count: 0",
            ],
        },
    ]
    answer = (
        "Runtime-Skills: Im Runtime-Skill-System sind aktuell keine installierten Skills vorhanden.\n"
        "Einordnung: Das bedeutet, dass noch keine zusätzlichen Funktionen aktiviert wurden. "
        "Ich kann aber trotzdem mit Python-Skills arbeiten, Code ausführen und auf Built-in-Tools zugreifen.\n\n"
        "Möchtest du, dass ich einen speziellen Skill entwickle oder hast du eine konkrete Aufgabe im Sinn?"
    )

    with patch("core.layers.output.layer.load_grounding_policy", return_value=_policy()):
        checked = layer._grounding_postcheck(answer, plan, _precheck(evidence))

    assert checked != answer


@pytest.mark.asyncio
async def test_followup_policy_should_not_require_draft_inventory_without_explicit_draft_question():
    orch = _make_orchestrator()
    control = ControlLayer()

    raw_plan = {
        "needs_memory": False,
        "is_fact_query": True,
        "needs_chat_history": False,
        "memory_keys": [],
        "resolution_strategy": "skill_catalog_context",
        "strategy_hints": ["runtime_skills", "draft_skills", "overview"],
        "suggested_tools": ["list_skills"],
    }
    thinking_plan = coerce_thinking_plan_schema(
        raw_plan,
        user_text="Welche Skills hast du aktuell und welche Skills wuerdest du dir als Naechstes wuenschen?",
        max_memory_keys_per_request=5,
        contains_explicit_tool_intent_fn=lambda text: False,
        has_memory_recall_signal_fn=lambda text: False,
    )
    verification = control._stabilize_verification_result(
        {
            "approved": True,
            "hard_block": False,
            "decision_class": "allow",
            "corrections": {},
            "warnings": [],
            "final_instruction": "",
            "suggested_tools": [],
        },
        thinking_plan,
        user_text="Welche Skills hast du aktuell und welche Skills wuerdest du dir als Naechstes wuenschen?",
    )
    verified_plan = control.apply_corrections(thinking_plan, verification)
    policy = orch._materialize_skill_catalog_policy(verified_plan)

    assert policy["required_tools"] == ["list_skills"]
