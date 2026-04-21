"""CIM context helpers for ControlLayer."""

from __future__ import annotations

import json


CIM_URL = "http://cim-server:8086"


async def get_cim_context(
    user_text: str,
    *,
    mode: str | None = None,
    async_client_cls,
    cim_url: str = CIM_URL,
    log_debug_fn,
) -> str | None:
    """Fetch causal prompt context from the CIM MCP endpoint."""
    try:
        async with async_client_cls(timeout=10.0) as client:
            init = await client.post(
                f"{cim_url}/mcp",
                json={
                    "jsonrpc": "2.0",
                    "id": 0,
                    "method": "initialize",
                    "params": {
                        "protocolVersion": "2024-11-05",
                        "capabilities": {},
                        "clientInfo": {"name": "control-layer", "version": "4.0.0"},
                    },
                },
                headers={"Content-Type": "application/json"},
            )
            session_id = init.headers.get("mcp-session-id")
            if not session_id:
                return None
            resp = await client.post(
                f"{cim_url}/mcp",
                json={
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "tools/call",
                    "params": {"name": "analyze", "arguments": {"query": user_text, "mode": mode}},
                },
                headers={"Content-Type": "application/json", "mcp-session-id": session_id},
            )
            if resp.status_code == 200:
                for line in resp.text.split("\n"):
                    if line.startswith("data: "):
                        data = json.loads(line[6:])
                        if "result" in data:
                            content = data["result"].get("content", [])
                            if content:
                                result = json.loads(content[0].get("text", "{}"))
                                return result.get("causal_prompt", "")
    except Exception as exc:
        log_debug_fn(f"[CIM] Not available: {exc}")
    return None
