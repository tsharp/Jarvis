"""
core.layers.output.generation.tool_check
==========================================
Non-Streaming Tool-Check Call.

Prüft ob der LLM Tool-Calls zurückgibt (NON-STREAMING /api/chat).
Gibt bei keinen Tool-Calls None zurück — dann Text-Antwort-Pfad.
"""
from typing import Any, Dict, List, Optional

from utils.logger import log_error, log_info
from utils.role_endpoint_resolver import resolve_role_endpoint
from core.llm_provider_client import complete_chat, resolve_role_provider
from config import get_output_provider


async def chat_check_tools(
    ollama_base: str,
    model: str,
    messages: List[Dict],
    tools: List[Dict],
) -> Optional[Dict]:
    """
    NON-STREAMING /api/chat call um zu prüfen ob Tool-Calls kommen.
    Returns: {"content": "...", "tool_calls": [...]} oder None
    """
    if not tools:
        return None

    try:
        provider = resolve_role_provider("output", default=get_output_provider())
        endpoint = ollama_base
        if provider == "ollama":
            route = resolve_role_endpoint("output", default_endpoint=ollama_base)
            if route["hard_error"]:
                log_error(
                    f"[Routing] role=output hard_error=true code={route['error_code']} "
                    f"requested_target={route['requested_target']}"
                )
                return None
            endpoint = route["endpoint"] or ollama_base

        # Non-Ollama providers are currently text-only in Output.
        tool_payload = tools if provider == "ollama" else []
        result = await complete_chat(
            provider=provider,
            model=model,
            messages=messages,
            timeout_s=90.0,
            ollama_endpoint=endpoint,
            tools=tool_payload,
        )
        tool_calls = result.get("tool_calls", []) if isinstance(result, dict) else []
        content = result.get("content", "") if isinstance(result, dict) else ""

        if tool_calls:
            return {"content": content, "tool_calls": tool_calls}

        return None  # Keine Tool-Calls → Text-Antwort

    except Exception as e:
        log_error(f"[OutputLayer] Tool check failed: {e}")
        return None
