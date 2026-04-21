from __future__ import annotations

from typing import Any, Dict, List, Optional

from mcp.hub import get_hub
from mcp.tool_prompt_hints import iter_base_detection_rules


def normalize_tool_definition(tool_def: Dict[str, Any]) -> Dict[str, Any]:
    tool = dict(tool_def) if isinstance(tool_def, dict) else {}
    name = str(tool.get("name") or "").strip()
    if not name:
        return {}

    input_schema = tool.get("inputSchema")
    if not isinstance(input_schema, dict):
        input_schema = {}

    execution_class = str(tool.get("execution") or "mcp").strip().lower() or "mcp"
    server = str(
        tool.get("mcp")
        or tool.get("server")
        or ("fast-lane" if execution_class == "direct" else "unknown")
    ).strip() or "unknown"

    transport = str(tool.get("transport") or "").strip().lower()
    if not transport and execution_class == "direct":
        transport = "direct"

    return {
        "name": name,
        "mcp": server,
        "server": server,
        "description": str(tool.get("description") or "").strip(),
        "inputSchema": dict(input_schema),
        "transport": transport,
        "execution_class": execution_class,
        "visibility": str(tool.get("visibility") or "default").strip().lower() or "default",
        "tags": [
            str(item or "").strip()
            for item in list(tool.get("tags") or [])
            if str(item or "").strip()
        ],
    }


def list_live_tools(*, hub: Optional[Any] = None) -> List[Dict[str, Any]]:
    try:
        active_hub = hub or get_hub()
        raw_tools = active_hub.list_tools() or []
    except Exception:
        return []

    normalized: List[Dict[str, Any]] = []
    seen = set()
    for raw in raw_tools:
        item = normalize_tool_definition(raw if isinstance(raw, dict) else {})
        name = str(item.get("name") or "").strip()
        if not name or name in seen:
            continue
        seen.add(name)
        normalized.append(item)
    normalized.sort(key=lambda item: str(item.get("name") or ""))
    return normalized


def build_available_tools_snapshot(
    selected_tools: List[Any] | None,
    *,
    hub: Optional[Any] = None,
) -> List[Dict[str, Any]]:
    snapshot: List[Dict[str, Any]] = []
    selected_names: List[str] = []
    seen = set()
    for item in list(selected_tools or []):
        if isinstance(item, dict):
            name = str(item.get("tool") or item.get("name") or "").strip()
        else:
            name = str(item or "").strip()
        if not name or name in seen:
            continue
        seen.add(name)
        selected_names.append(name)

    if hub is None:
        return [
            {
                "name": name,
                "mcp": "unknown",
                "server": "unknown",
                "description": "",
                "inputSchema": {},
                "transport": "",
                "execution_class": "unknown",
                "visibility": "default",
                "tags": [],
            }
            for name in selected_names
        ]

    live_tools = list_live_tools(hub=hub)
    by_name = {
        str(item.get("name") or "").strip(): item
        for item in live_tools
        if str(item.get("name") or "").strip()
    }

    for name in selected_names:
        resolved = by_name.get(name)
        if resolved:
            snapshot.append(dict(resolved))
            continue
        snapshot.append(
            {
                "name": name,
                "mcp": "unknown",
                "server": "unknown",
                "description": "",
                "inputSchema": {},
                "transport": "",
                "execution_class": "unknown",
                "visibility": "default",
                "tags": [],
            }
        )
    return snapshot


def build_detection_hints(*, hub: Optional[Any] = None) -> str:
    """Returns detection rules text for Thinking injection.

    Prefers live hub-generated rules (base + custom MCP config.json rules)
    when a hub is provided. Falls back to static base rules otherwise.
    Never triggers Hub initialization or DB roundtrips on its own.
    """
    if hub is not None:
        try:
            return hub.get_detection_rules()
        except Exception:
            pass
    rules = sorted(iter_base_detection_rules(), key=lambda x: x[0])
    return "=== MCP DETECTION RULES ===\n" + "\n".join(r[1] for r in rules)
