from __future__ import annotations

import json
import uuid
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional, Tuple

from core.tools.tool_result import ToolResult


def merge_grounding_evidence_items(
    existing: Any,
    extra: Any,
) -> List[Dict[str, Any]]:
    merged: List[Dict[str, Any]] = []
    seen = set()
    for source in (existing or [], extra or []):
        if not isinstance(source, list):
            continue
        for item in source:
            if not isinstance(item, dict):
                continue
            sig = (
                str(item.get("tool_name", "")).strip(),
                str(item.get("ref_id", "")).strip(),
                str(item.get("status", "")).strip().lower(),
                tuple(str(x).strip() for x in (item.get("key_facts") or [])[:3])
                if isinstance(item.get("key_facts"), list)
                else (),
            )
            if sig in seen:
                continue
            seen.add(sig)
            merged.append(item)
    return merged


def format_tool_result(
    result: Any,
    tool_name: str,
    *,
    detect_tool_error_fn: Callable[[Any], Tuple[bool, str]],
    result_char_cap: int = 3000,
) -> Tuple[str, bool, Dict[str, Any]]:
    """
    Format tool result for consistent handling (Fast Lane + MCP).

    Returns:
        (formatted_string, success, metadata)
    """
    if isinstance(result, ToolResult):
        success = result.success
        if success:
            if isinstance(result.content, (dict, list)):
                content_str = json.dumps(result.content, ensure_ascii=False, default=str)
            else:
                content_str = str(result.content)
            if len(content_str) > result_char_cap:
                content_str = content_str[:result_char_cap] + "... (gekuerzt)"
            formatted = f"\n--- {tool_name} (Fast Lane ⚡ {result.latency_ms:.1f}ms) ---\n{content_str}\n"
            metadata = {
                "execution_mode": "fast_lane",
                "latency_ms": result.latency_ms,
                "tool_name": tool_name,
            }
        else:
            formatted = f"\n### FEHLER ({tool_name}): {result.error}\n"
            metadata = {
                "execution_mode": "fast_lane",
                "error": result.error,
                "tool_name": tool_name,
            }
        return formatted, success, metadata

    result_str = json.dumps(result, ensure_ascii=False, default=str) if isinstance(result, (dict, list)) else str(result)
    is_error, err_msg = detect_tool_error_fn(result)
    if len(result_str) > result_char_cap:
        result_str = result_str[:result_char_cap] + "... (gekuerzt)"
    if is_error:
        formatted = f"\n### FEHLER ({tool_name}): {err_msg or result_str}\n"
    else:
        formatted = f"\n### TOOL-ERGEBNIS ({tool_name}):\n{result_str}\n"
    metadata = {
        "execution_mode": "mcp",
        "tool_name": tool_name,
    }
    if is_error:
        metadata["error"] = err_msg or result_str
    return formatted, not is_error, metadata


def build_tool_result_card(
    *,
    tool_name: str,
    raw_result: str,
    status: str,
    conversation_id: str,
    save_workspace_entry_fn: Callable[[str, str, str, str], Any],
    log_warn_fn: Callable[[str], None],
    tool_card_char_cap: int,
    tool_card_bullet_cap: int,
) -> Tuple[str, str]:
    """
    Build a compact Tool Result Card for tool_context and persist full payload to workspace events.
    """
    ref_id = uuid.uuid4().hex[:12]
    timestamp = datetime.utcnow().isoformat() + "Z"

    lines = [
        line.strip()
        for line in str(raw_result or "").splitlines()
        if line.strip() and not line.strip().startswith("#")
    ]
    key_facts = lines[:tool_card_bullet_cap] or [str(raw_result or "")[:200].strip() or "Keine Ausgabe"]

    status_icon = {"ok": "✅", "error": "❌", "partial": "⚠️"}.get(status, "🔧")
    bullets = "\n".join(f"- {fact[:150]}" for fact in key_facts)
    card = (
        f"\n[TOOL-CARD: {tool_name} | {status_icon} {status} | ref:{ref_id}]\n"
        f"{bullets}\n"
        f"ts:{timestamp}\n"
    )
    if len(card) > tool_card_char_cap:
        card = card[:tool_card_char_cap] + "\n[...card truncated]\n"

    entry_type = "tool_result"
    extra_fields: Dict[str, Any] = {}
    try:
        parsed = json.loads(str(raw_result or ""))
        if isinstance(parsed, dict):
            event_type = parsed.get("event_type") or parsed.get("action_taken") or parsed.get("action")
            if event_type in ("approval_requested", "pending_package_approval"):
                entry_type = "approval_requested"
                extra_fields = {
                    "skill_name": parsed.get("skill_name") or tool_name,
                    "missing_packages": parsed.get("missing_packages", []),
                    "non_allowlisted_packages": parsed.get("non_allowlisted_packages", []),
                }
    except Exception:
        pass

    try:
        save_workspace_entry_fn(
            conversation_id,
            json.dumps(
                {
                    "tool_name": tool_name,
                    "status": status,
                    "ref_id": ref_id,
                    "timestamp": timestamp,
                    "key_facts": key_facts,
                    "payload": str(raw_result or "")[:50_000],
                    **extra_fields,
                },
                ensure_ascii=False,
                default=str,
            ),
            entry_type,
            "orchestrator",
        )
    except Exception as exc:
        log_warn_fn(f"[Orchestrator] Card event save failed for {tool_name}: {exc}")

    return card, ref_id


def compute_ctx_mode(
    trace: Dict[str, Any],
    *,
    is_loop: bool = False,
    get_context_trace_dryrun_fn: Callable[[], bool],
) -> str:
    """
    Compute the canonical mode string for [CTX-FINAL] logging.
    Format: (small|full)[+failure][+dryrun][+loop]
    """
    mode = "small" if trace.get("small_model_mode") else "full"
    if "failure_ctx" in trace.get("context_sources", []):
        mode += "+failure"
    if get_context_trace_dryrun_fn():
        mode += "+dryrun"
    if is_loop:
        mode += "+loop"
    return mode


def extract_workspace_observations(thinking_plan: Dict[str, Any]) -> Optional[str]:
    parts = []
    intent = thinking_plan.get("intent")
    if intent and intent != "unknown":
        parts.append(f"**Intent:** {intent}")

    memory_keys = thinking_plan.get("memory_keys", [])
    if memory_keys:
        parts.append(f"**Memory keys:** {', '.join(memory_keys)}")

    risk = thinking_plan.get("hallucination_risk", "")
    if risk == "high":
        parts.append("**Risk:** High hallucination risk detected")

    needs_seq = thinking_plan.get("needs_sequential_thinking", False)
    if needs_seq:
        parts.append("**Sequential thinking** required")

    if not parts:
        return None
    return "\n".join(parts)
