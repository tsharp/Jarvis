from unittest.mock import patch

from core.tool_exposure import build_available_tools_snapshot, build_detection_hints, list_live_tools


def test_list_live_tools_normalizes_and_deduplicates_live_hub_tools():
    class _Hub:
        def list_tools(self):
            return [
                {
                    "name": "request_container",
                    "mcp": "container-commander",
                    "description": "Start a container.",
                    "inputSchema": {"type": "object", "properties": {"blueprint_id": {"type": "string"}}},
                },
                {
                    "name": "request_container",
                    "mcp": "container-commander",
                    "description": "Duplicate entry should be ignored.",
                },
                {
                    "name": "workspace_event_save",
                    "description": "Persist workspace event.",
                    "execution": "direct",
                },
            ]

    tools = list_live_tools(hub=_Hub())

    assert [item["name"] for item in tools] == ["request_container", "workspace_event_save"]
    assert tools[0]["mcp"] == "container-commander"
    assert tools[0]["execution_class"] == "mcp"
    assert tools[1]["mcp"] == "fast-lane"
    assert tools[1]["transport"] == "direct"


def test_list_live_tools_returns_empty_list_on_hub_error():
    class _Hub:
        def list_tools(self):
            raise RuntimeError("hub unavailable")

    assert list_live_tools(hub=_Hub()) == []


def test_build_available_tools_snapshot_resolves_selected_names_against_live_tools():
    class _Hub:
        def list_tools(self):
            return [
                {
                    "name": "request_container",
                    "mcp": "container-commander",
                    "description": "Start a container.",
                    "inputSchema": {"type": "object"},
                },
                {
                    "name": "blueprint_list",
                    "mcp": "container-commander",
                    "description": "List blueprints.",
                    "inputSchema": {"type": "object"},
                },
            ]

    snapshot = build_available_tools_snapshot(["blueprint_list", "request_container"], hub=_Hub())

    assert [item["name"] for item in snapshot] == ["blueprint_list", "request_container"]
    assert snapshot[0]["mcp"] == "container-commander"
    assert snapshot[1]["description"] == "Start a container."


def test_build_detection_hints_returns_base_rules_without_hub():
    hints = build_detection_hints()
    assert "MCP DETECTION RULES" in hints
    assert "memory_save" in hints
    assert "blueprint_list" in hints


def test_build_detection_hints_delegates_to_hub_get_detection_rules():
    class _Hub:
        def get_detection_rules(self):
            return "CUSTOM RULES FROM HUB"

    hints = build_detection_hints(hub=_Hub())
    assert hints == "CUSTOM RULES FROM HUB"


def test_build_detection_hints_falls_back_to_base_rules_on_hub_error():
    class _BrokenHub:
        def get_detection_rules(self):
            raise RuntimeError("hub broken")

    hints = build_detection_hints(hub=_BrokenHub())
    assert "MCP DETECTION RULES" in hints
    assert "memory_save" in hints
