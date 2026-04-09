import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from core.orchestrator_semantic_context_utils import (
    derive_container_addon_tags_from_inspect,
    maybe_build_skill_semantic_context,
    parse_list_draft_skills_snapshot,
    parse_list_skills_runtime_snapshot,
    summarize_container_inspect_for_capability_context,
    summarize_skill_registry_snapshot,
    summarize_skill_runtime_snapshot,
)
from core.plan_runtime_bridge import get_runtime_grounding_evidence


def test_derive_container_addon_tags_from_inspect_extracts_identity_and_image_tags():
    out = derive_container_addon_tags_from_inspect(
        {
            "blueprint_id": "trion-home",
            "name": "trion-home",
            "image": "python:3.12-slim",
            "running": True,
        }
    )

    assert "container-shell" in out
    assert "trion-home" in out
    assert "python" in out
    assert "slim" in out
    assert "running" in out


def test_parse_list_skills_runtime_snapshot_reads_structured_content():
    out = parse_list_skills_runtime_snapshot(
        {
            "structuredContent": {
                "installed": [{"name": "current_weather"}, {"name": "system_hardware_info"}],
                "installed_count": 2,
                "available": [],
                "available_count": 0,
            }
        }
    )

    assert out["installed_count"] == 2
    assert out["available_count"] == 0
    assert out["installed_names"] == ["current_weather", "system_hardware_info"]


def test_parse_list_draft_skills_snapshot_reads_names():
    out = parse_list_draft_skills_snapshot(
        {
            "structuredContent": {
                "drafts": [{"name": "draft_alpha"}, "draft_beta"],
            }
        }
    )

    assert out["draft_count"] == 2
    assert out["draft_names"] == ["draft_alpha", "draft_beta"]


def test_summarize_helpers_emit_expected_lines():
    runtime = summarize_skill_runtime_snapshot(
        {
            "installed_count": 2,
            "draft_count": 1,
            "available_count": 0,
            "installed_names": ["current_weather", "system_hardware_info"],
            "draft_names": ["draft_alpha"],
        }
    )
    registry = summarize_skill_registry_snapshot(
        {
            "active_count": 2,
            "draft_count": 1,
            "active_names": ["current_weather", "system_hardware_info"],
            "draft_names": ["draft_alpha"],
        }
    )
    container = summarize_container_inspect_for_capability_context(
        {
            "container_id": "ctr-1",
            "name": "trion-home",
            "blueprint_id": "trion-home",
            "image": "python:3.12-slim",
            "status": "running",
            "network": "bridge",
            "resource_limits": {"cpu_count": 2, "memory_mb": 1024},
            "mounts": ["/srv/work:/home/trion/workspace"],
            "ports": [{"host_port": "3000", "container_port": "3000", "protocol": "tcp"}],
        }
    )

    assert "installed_runtime_skills: 2" in runtime
    assert "draft_skills: 1" in runtime
    assert "active_count: 2" in registry
    assert "draft_names: draft_alpha" in registry
    assert "container_id: ctr-1" in container
    assert "resource_limits: cpu=2 memory_mb=1024" in container
    assert "3000->3000/tcp" in container


@pytest.mark.asyncio
async def test_maybe_build_skill_semantic_context_direct_utility_path():
    class _FakeHub:
        def initialize(self):
            return None

        async def call_tool_async(self, tool_name, args):
            if tool_name == "list_skills":
                return {
                    "structuredContent": {
                        "installed": [{"name": "current_weather"}],
                        "installed_count": 1,
                        "available": [],
                        "available_count": 0,
                    }
                }
            if tool_name == "list_draft_skills":
                return {
                    "structuredContent": {
                        "drafts": ["draft_alpha"],
                    }
                }
            raise AssertionError(f"unexpected tool call: {tool_name}")

    def _resp(payload):
        response = MagicMock()
        response.read.return_value = json.dumps(payload).encode("utf-8")
        response.__enter__ = MagicMock(return_value=response)
        response.__exit__ = MagicMock(return_value=False)
        return response

    verified_plan = {
        "is_fact_query": True,
        "_authoritative_resolution_strategy": "skill_catalog_context",
        "_skill_catalog_policy": {
            "mode": "inventory_read_only",
            "required_tools": ["list_skills", "list_draft_skills"],
            "selected_hints": ["draft_skills", "tools_vs_skills"],
        },
        "strategy_hints": ["draft_skills", "tools_vs_skills"],
    }

    with patch(
        "urllib.request.urlopen",
        return_value=_resp({"active": ["current_weather"], "drafts": ["draft_alpha"]}),
    ), patch(
        "intelligence_modules.skill_addons.loader.load_skill_addon_context",
        new=AsyncMock(
            return_value={
                "selected_docs": [{"id": "skill-tools-vs-skills", "title": "Tools Versus Skills"}],
                "context_text": "Built-in Tools sind keine installierten Runtime-Skills.",
            }
        ),
    ):
        out = await maybe_build_skill_semantic_context(
            user_text="Was ist der Unterschied zwischen Tools und Skills?",
            conversation_id="conv-semantic-direct",
            verified_plan=verified_plan,
            get_effective_resolution_strategy_fn=lambda plan: str(
                (plan or {}).get("_authoritative_resolution_strategy") or ""
            ),
            is_skill_catalog_context_query_fn=lambda text: "skills" in text.lower(),
            materialize_skill_catalog_policy_fn=lambda plan: dict(plan.get("_skill_catalog_policy") or {}),
            get_hub_fn=lambda: _FakeHub(),
            build_tool_result_card_fn=lambda tool_name, raw_result, status, conversation_id: (
                f"\n[TOOL-CARD: {tool_name} | {status} | ref:{tool_name}-ref]\n- ok\n",
                f"{tool_name}-ref",
            ),
            build_grounding_evidence_entry_fn=lambda tool_name, raw_result, status, ref_id: {
                "tool_name": tool_name,
                "status": status,
                "ref_id": ref_id,
                "key_facts": [str(raw_result).splitlines()[0]],
            },
            merge_grounding_evidence_items_fn=lambda existing, extra: list(existing or []) + list(extra or []),
            safe_str_fn=lambda value, max_len: str(value)[:max_len],
            log_warn_fn=lambda msg: None,
        )

    assert "SKILL CATALOG CONTEXT" in out["context_text"]
    assert "installed_runtime_skills: 1" in out["context_text"]
    assert "Built-in Tools sind keine installierten Runtime-Skills." in out["context_text"]
    assert "list_skills" in out["tool_results_text"]
    assert "list_draft_skills" in out["tool_results_text"]
    assert "skill_addons" in out["tool_results_text"]

    evidence = get_runtime_grounding_evidence(verified_plan)
    assert any(item.get("tool_name") == "list_skills" for item in evidence)
    assert any(item.get("tool_name") == "skill_registry_snapshot" for item in evidence)
    assert any(item.get("tool_name") == "skill_addons" for item in evidence)
