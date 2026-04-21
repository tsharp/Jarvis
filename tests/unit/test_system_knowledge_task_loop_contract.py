"""Contract-Tests für den System-Knowledge Task-Loop-Trigger."""
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]


# ── Statische Struktur ──────────────────────────────────────────────────────

def test_system_knowledge_capability_package_exists():
    base = ROOT / "core" / "task_loop" / "capabilities" / "system_knowledge"
    assert (base / "__init__.py").exists()
    assert (base / "context.py").exists()


def test_capability_policy_has_system_knowledge_tools():
    src = (ROOT / "core" / "task_loop" / "capability_policy.py").read_text()
    assert "SYSTEM_KNOWLEDGE_TOOLS" in src
    assert "get_system_info" in src
    assert "get_system_overview" in src
    assert '"system_knowledge"' in src


def test_tool_catalog_has_system_knowledge_entry():
    src = (ROOT / "core" / "task_loop" / "action_resolution" / "tool_utility_policy" / "tool_catalog.py").read_text()
    assert '"system_knowledge"' in src
    assert "get_system_info" in src
    assert "get_system_overview" in src


def test_prepare_imports_system_knowledge():
    src = (ROOT / "core" / "task_loop" / "step_runtime" / "prepare.py").read_text()
    assert "is_system_knowledge_intent" in src
    assert "load_system_knowledge_context" in src
    assert "system_knowledge" in src


def test_prompting_has_system_addon_block():
    src = (ROOT / "core" / "task_loop" / "step_runtime" / "prompting.py").read_text()
    assert "_system_addon_context_block" in src
    assert "system_addon_context" in src
    assert "SYSTEM-SELBSTWISSEN" in src


# ── Query-Class-Detection ───────────────────────────────────────────────────

from core.task_loop.capabilities.system_knowledge.context import (
    _detect_query_class,
    is_system_knowledge_intent,
)


@pytest.mark.parametrize("intent,expected_class", [
    ("welche services laufen auf welchem port?", "system_topology"),
    ("service map und docker netz", "system_topology"),
    ("wo liegen die api keys?", "data_locations"),
    ("secrets und vault zugriff", "data_locations"),
    ("wie funktioniert auth im system?", "auth_model"),
    ("bearer token für secret resolve", "auth_model"),
    ("welche tools kann ich aufrufen?", "tool_surface"),
    ("native tools übersicht", "tool_surface"),
    ("skill erstellen — wie geht das?", "self_extension"),
    ("lücke schließen mit neuem skill", "self_extension"),
])
def test_detect_query_class(intent, expected_class):
    assert _detect_query_class(intent) == expected_class


@pytest.mark.parametrize("intent", [
    "get_system_info aufrufen",
    "system übersicht zeigen",
    "system selbst beschreiben",
    "welche services laufen",
    "wo liegen secrets",
    "skill erstellen",
    "welche tools gibt es",
])
def test_is_system_knowledge_intent_positive(intent):
    assert is_system_knowledge_intent(intent)


@pytest.mark.parametrize("intent", [
    "bitte erkläre mir python basics",
    "was ist 2+2",
    "schreibe einen brief",
])
def test_is_system_knowledge_intent_negative(intent):
    assert not is_system_knowledge_intent(intent)


# ── capability_type_from_tools ──────────────────────────────────────────────

from core.task_loop.capability_policy import capability_type_from_tools


def test_get_system_info_maps_to_system_knowledge():
    assert capability_type_from_tools(["get_system_info"]) == "system_knowledge"


def test_get_system_overview_maps_to_system_knowledge():
    assert capability_type_from_tools(["get_system_overview"]) == "system_knowledge"


def test_container_tools_not_overridden_by_system_knowledge():
    assert capability_type_from_tools(["container_list"]) == "container_manager"


def test_system_knowledge_does_not_trigger_for_empty_tools():
    assert capability_type_from_tools([]) == ""


# ── tool_catalog ────────────────────────────────────────────────────────────

from core.task_loop.action_resolution.tool_utility_policy.tool_catalog import (
    DISCOVERY_TOOLS,
    is_discovery_only,
    suggest_tools_for_step,
)


def test_system_knowledge_discovery_tools_in_catalog():
    tools = suggest_tools_for_step("system_knowledge", "zeige system info")
    assert "get_system_info" in tools or "get_system_overview" in tools


def test_system_knowledge_tools_are_discovery_only():
    assert is_discovery_only(["get_system_info"])
    assert is_discovery_only(["get_system_overview"])
    assert is_discovery_only(["get_system_info", "get_system_overview"])


def test_system_knowledge_tools_in_discovery_tools_frozenset():
    assert "get_system_info" in DISCOVERY_TOOLS
    assert "get_system_overview" in DISCOVERY_TOOLS


# ── Loader-Integration ──────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_load_system_knowledge_context_returns_context_for_known_intent():
    from core.task_loop.capabilities.system_knowledge.context import load_system_knowledge_context
    result = await load_system_knowledge_context(
        "welche services laufen und auf welchem port",
        use_embeddings=False,
    )
    assert result.get("system_addon_context", "").strip()
    assert result.get("system_addon_query_class") == "system_topology"


@pytest.mark.asyncio
async def test_load_system_knowledge_context_empty_for_unrelated_intent():
    from core.task_loop.capabilities.system_knowledge.context import load_system_knowledge_context
    result = await load_system_knowledge_context(
        "schreibe ein gedicht über den frühling",
        use_embeddings=False,
    )
    # Kein match → leeres dict
    assert result == {}


@pytest.mark.asyncio
async def test_load_system_knowledge_context_never_raises():
    from core.task_loop.capabilities.system_knowledge.context import load_system_knowledge_context
    # Auch bei leerem Intent kein Exception
    result = await load_system_knowledge_context("", use_embeddings=False)
    assert isinstance(result, dict)
