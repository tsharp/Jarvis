import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from core.layers.control import ControlLayer
from core.layers.output import OutputLayer
from core.orchestrator_plan_schema_utils import coerce_thinking_plan_schema
from core.plan_runtime_bridge import get_runtime_grounding_evidence, set_runtime_tool_results


_TOOLS = [
    {"name": "list_skills", "mcp": "skill-server", "description": "List installed runtime skills"},
    {"name": "get_skill_info", "mcp": "skill-server", "description": "Read skill metadata"},
]


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


def _urlopen_response(payload):
    response = MagicMock()
    response.read.return_value = json.dumps(payload).encode("utf-8")
    response.__enter__ = MagicMock(return_value=response)
    response.__exit__ = MagicMock(return_value=False)
    return response


async def _build_skill_prompt_flow(user_text: str, raw_plan=None):
    orch = _make_orchestrator()
    control = ControlLayer()

    raw_plan = raw_plan or {
        "needs_memory": False,
        "is_fact_query": True,
        "needs_chat_history": False,
        "memory_keys": [],
        "suggested_tools": ["list_skills"],
    }
    thinking_plan = coerce_thinking_plan_schema(
        raw_plan,
        user_text=user_text,
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
        user_text=user_text,
    )
    verified_plan = control.apply_corrections(thinking_plan, verification)
    orch._materialize_skill_catalog_policy(verified_plan)

    class _FakeHub:
        def initialize(self):
            return None

        async def call_tool_async(self, tool_name, args):
            if tool_name == "list_skills":
                assert args == {"include_available": False}
                return {
                    "structuredContent": {
                        "installed": [
                            {"name": "current_weather", "version": "1.0.0"},
                            {"name": "system_hardware_info", "version": "1.0.0"},
                        ],
                        "installed_count": 2,
                        "available": [],
                        "available_count": 0,
                    }
                }
            if tool_name == "list_draft_skills":
                assert args == {}
                return {
                    "structuredContent": {
                        "drafts": ["draft_alpha"],
                    }
                }
            raise AssertionError(f"unexpected tool call: {tool_name}")

    with patch("core.orchestrator.get_hub", return_value=_FakeHub()), \
         patch(
             "urllib.request.urlopen",
             return_value=_urlopen_response(
                 {
                     "active": ["current_weather", "system_hardware_info"],
                     "drafts": ["draft_alpha"],
                 }
             ),
         ), \
         patch(
             "intelligence_modules.skill_addons.loader.embed_text",
             new=AsyncMock(return_value=None),
         ):
        semantic_ctx = await orch._maybe_build_skill_semantic_context(
            user_text=user_text,
            conversation_id="conv-skill-prompt",
            verified_plan=verified_plan,
        )

    set_runtime_tool_results(verified_plan, semantic_ctx["tool_results_text"])
    verified_plan["_selected_tools_for_prompt"] = ["list_skills"]

    with patch("core.layers.output.get_enabled_tools", return_value=_TOOLS), \
         patch("core.layers.output.get_output_tool_prompt_limit", return_value=10), \
         patch("core.layers.output.get_output_tool_injection_mode", return_value="selected"):
        prompt = OutputLayer().build_system_prompt(verified_plan, semantic_ctx["context_text"])

    return thinking_plan, verified_plan, semantic_ctx, prompt


@pytest.mark.asyncio
async def test_skill_inventory_prompt_flow_uses_runtime_authority_and_semantic_rules():
    thinking_plan, verified_plan, semantic_ctx, prompt = await _build_skill_prompt_flow(
        "Welche Skills hast du?"
    )

    assert thinking_plan["resolution_strategy"] == "skill_catalog_context"
    assert "runtime_skills" in thinking_plan["strategy_hints"]
    assert "answering_rules" in thinking_plan["strategy_hints"]
    assert verified_plan["_authoritative_resolution_strategy"] == "skill_catalog_context"
    policy = verified_plan["_skill_catalog_policy"]
    assert policy["mode"] == "inventory_read_only"
    assert policy["required_tools"] == ["list_skills"]
    assert policy["force_sections"] == ["Runtime-Skills", "Einordnung"]

    context_text = semantic_ctx["context_text"]
    assert "Treat live runtime snapshot facts as the inventory authority." in context_text
    assert "installed_runtime_skills: 2" in context_text
    assert "draft_skills: 1" in context_text
    assert "Relevant skill addon docs:" in context_text
    assert "skill-overview" in context_text
    assert "skill-runtime-skills" in context_text
    assert "skill-answering-rules" in context_text
    assert "list_skills` deckt nur installierte Runtime-Skills ab." in context_text

    tool_results = semantic_ctx["tool_results_text"]
    assert "list_skills" in tool_results
    assert "skill_registry_snapshot" in tool_results
    assert "skill_addons" in tool_results

    evidence = get_runtime_grounding_evidence(verified_plan)
    assert any(item.get("tool_name") == "list_skills" for item in evidence)
    assert any(item.get("tool_name") == "skill_addons" for item in evidence)

    assert "### FAKTEN AUS DEM GEDÄCHTNIS:" in prompt
    assert "### OUTPUT-GROUNDING:" in prompt
    assert "### SKILL-SEMANTIK:" in prompt
    assert "### SKILL-KATALOG-ANTWORTMODUS:" in prompt
    assert "`list_skills` beschreibt nur installierte Runtime-Skills" in prompt
    assert "Built-in Tools dürfen nicht als installierte Skills formuliert werden." in prompt
    assert "Pflichtreihenfolge: `Runtime-Skills`, dann `Einordnung`, danach optional `Nächster Schritt`." in prompt
    assert "aktuell 2 installierte Runtime-Skills" in prompt


@pytest.mark.asyncio
async def test_tools_vs_skills_prompt_flow_keeps_category_boundary_visible():
    thinking_plan, verified_plan, semantic_ctx, prompt = await _build_skill_prompt_flow(
        "Was ist der Unterschied zwischen Tools und Skills?"
    )

    assert thinking_plan["resolution_strategy"] == "skill_catalog_context"
    assert "tools_vs_skills" in thinking_plan["strategy_hints"]
    assert "answering_rules" in thinking_plan["strategy_hints"]
    assert verified_plan["_authoritative_resolution_strategy"] == "skill_catalog_context"
    policy = verified_plan["_skill_catalog_policy"]
    assert policy["required_tools"] == ["list_skills"]
    assert policy["draft_explanation_required"] is True

    context_text = semantic_ctx["context_text"]
    assert "Relevant skill addon docs: skill-tools-vs-skills, skill-answering-rules" in context_text
    assert "Built-in Tools sind native oder MCP-gebundene Werkzeuge." in context_text
    assert "Tool X ist als Skill installiert" in context_text
    assert "list_skills` deckt nicht die komplette Faehigkeitenwelt ab." in context_text

    tool_results = semantic_ctx["tool_results_text"]
    assert "list_skills" in tool_results
    assert "skill_addons" in tool_results

    assert "### SKILL-SEMANTIK:" in prompt
    assert "Trenne in der Antwort Runtime-Skills, Draft Skills und Built-in Tools explizit" in prompt
    assert "Session- oder System-Skills nur nennen, wenn sie im Kontext ausdrücklich belegt sind." in prompt
    assert "### SKILL-KATALOG-ANTWORTMODUS:" in prompt
    assert "Wenn du Built-in Tools erwähnst, dann ausschließlich im explizit markierten Abschnitt `Einordnung`." in prompt
    assert "### FAKTEN AUS DEM GEDÄCHTNIS:" in prompt


@pytest.mark.asyncio
async def test_live_inventory_prompt_flow_sharpens_hints_and_includes_taxonomy_docs():
    live_prompt = (
        "Dir stehen SKILLS zu verfügung. Kannst du mal schauen, "
        "was du darüber in erfahrung bringen kannst? "
        "Was für skills hättest du gerne?"
    )
    thinking_plan, verified_plan, semantic_ctx, prompt = await _build_skill_prompt_flow(
        live_prompt,
        raw_plan={
            "needs_memory": False,
            "is_fact_query": True,
            "needs_chat_history": False,
            "memory_keys": [],
            "resolution_strategy": "skill_catalog_context",
            "strategy_hints": ["runtime_skills", "draft_skills", "overview"],
            "suggested_tools": ["list_skills"],
        },
    )

    assert thinking_plan["resolution_strategy"] == "skill_catalog_context"
    assert "runtime_skills" in thinking_plan["strategy_hints"]
    assert "overview" in thinking_plan["strategy_hints"]
    assert "tools_vs_skills" in thinking_plan["strategy_hints"]
    assert "answering_rules" in thinking_plan["strategy_hints"]
    assert "fact_then_followup" in thinking_plan["strategy_hints"]
    assert verified_plan["_authoritative_resolution_strategy"] == "skill_catalog_context"
    policy = verified_plan["_skill_catalog_policy"]
    assert policy["required_tools"] == ["list_skills"]
    assert policy["force_sections"] == [
        "Runtime-Skills",
        "Einordnung",
        "Wunsch-Skills",
    ]

    context_text = semantic_ctx["context_text"]
    assert "Relevant skill addon docs:" in context_text
    assert "skill-overview" in context_text
    assert "skill-answering-rules" in context_text
    assert "Installed Runtime Skills sind die Skills" in context_text
    assert "Built-in Tools" in context_text
    assert "Session-/System-Skills" in context_text
    assert "list_skills` deckt nur installierte Runtime-Skills ab." in context_text

    assert "### SKILL-SEMANTIK:" in prompt
    assert "### SKILL-KATALOG-ANTWORTMODUS:" in prompt
    assert "Built-in Tools dürfen nicht als installierte Skills formuliert werden." in prompt
    assert "Keine unmarkierte Freitext-Liste" in prompt
    assert "Faktinventar und Wunsch-/Brainstorming-Teil kombiniert" in prompt
    assert "Wunsch-Skills" in prompt
    tool_results = semantic_ctx["tool_results_text"]
    assert "list_draft_skills" not in tool_results
