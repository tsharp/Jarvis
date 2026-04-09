from __future__ import annotations

import json
import re
from typing import Any, Callable, Dict, List, Optional, Tuple


def build_master_workspace_summary(event_type: str, payload: Dict[str, Any]) -> str:
    data = payload if isinstance(payload, dict) else {}
    kind = str(event_type or "").strip() or "planning_event"

    if kind == "planning_start":
        objective = str(data.get("objective", "") or "").strip()
        max_loops = data.get("max_loops")
        state = str(data.get("state", "") or "").strip()
        planning_mode = str(data.get("planning_mode", "") or "").strip()
        parts = [f"objective={objective[:140]}" if objective else "objective=unknown"]
        if max_loops is not None:
            parts.append(f"max_loops={max_loops}")
        if state:
            parts.append(f"state={state}")
        if planning_mode:
            parts.append(f"planning_mode={planning_mode}")
        return " | ".join(parts)

    if kind == "planning_step":
        parts: List[str] = []
        phase = str(data.get("phase", "") or "").strip()
        if phase:
            parts.append(f"phase={phase}")
        if data.get("loop") is not None:
            parts.append(f"loop={data.get('loop')}")
        state = str(data.get("state", "") or "").strip()
        if state:
            parts.append(f"state={state}")
        decision = str(data.get("decision", "") or "").strip()
        if decision:
            parts.append(f"decision={decision}")
        next_action = str(data.get("next_action", "") or "").strip()
        if next_action:
            parts.append(f"next_action={next_action[:140]}")
        action = str(data.get("action", "") or "").strip()
        if action:
            parts.append(f"action={action[:140]}")
        reason = str(data.get("reason", "") or "").strip()
        if reason:
            parts.append(f"reason={reason[:120]}")
        return " | ".join(parts) if parts else "planning_step"

    if kind == "planning_done":
        loops = data.get("loops_executed")
        steps = data.get("steps_completed")
        final_state = str(data.get("final_state", "") or "").strip()
        stop_reason = str(data.get("stop_reason", "") or "").strip()
        parts = []
        if loops is not None:
            parts.append(f"loops={loops}")
        if steps is not None:
            parts.append(f"steps={steps}")
        if final_state:
            parts.append(f"final_state={final_state}")
        if stop_reason:
            parts.append(f"stop_reason={stop_reason}")
        return " | ".join(parts) if parts else "planning_done"

    if kind == "planning_error":
        phase = str(data.get("phase", "") or "").strip()
        error = str(data.get("error", "") or "").strip() or "unknown_error"
        error_code = str(data.get("error_code", "") or "").strip()
        action = str(data.get("action", "") or "").strip()
        stop_reason = str(data.get("stop_reason", "") or "").strip()
        parts = [f"error={error[:180]}"]
        if error_code:
            parts.append(f"error_code={error_code[:80]}")
        if phase:
            parts.append(f"phase={phase}")
        if action:
            parts.append(f"action={action[:120]}")
        if stop_reason:
            parts.append(f"stop_reason={stop_reason[:80]}")
        return " | ".join(parts)

    return json.dumps(data, ensure_ascii=False)[:240] if data else kind


def persist_master_workspace_event(
    *,
    conversation_id: str,
    event_type: str,
    payload: Dict[str, Any],
    build_master_workspace_summary_fn: Callable[[str, Dict[str, Any]], str],
    save_workspace_entry_fn: Callable[..., Optional[Dict[str, Any]]],
) -> Optional[Dict[str, Any]]:
    conv_id = str(conversation_id or "").strip()
    kind = str(event_type or "").strip()
    if not conv_id or kind not in {"planning_start", "planning_step", "planning_done", "planning_error"}:
        return None
    content = build_master_workspace_summary_fn(kind, payload if isinstance(payload, dict) else {})
    return save_workspace_entry_fn(
        conversation_id=conv_id,
        content=content,
        entry_type=kind,
        source_layer="master",
    )


def compute_retrieval_policy(
    thinking_plan: Dict[str, Any],
    verified_plan: Dict[str, Any],
    *,
    current_tool_context: str = "",
    get_jit_retrieval_max_fn: Callable[[], int],
    get_jit_retrieval_max_on_failure_fn: Callable[[], int],
) -> Dict[str, Any]:
    tool_failure = bool(
        (verified_plan or {}).get("_tool_failure")
        or ("TOOL-FEHLER" in current_tool_context or "VERIFY-FEHLER" in current_tool_context)
    )
    base_max = (
        get_jit_retrieval_max_on_failure_fn()
        if tool_failure
        else get_jit_retrieval_max_fn()
    )
    reasons = []
    if tool_failure:
        reasons.append(f"tool_failure → budget={base_max}")
    else:
        reasons.append(f"normal → budget={base_max}")
    return {
        "max_retrievals": base_max,
        "tool_failure": tool_failure,
        "time_reference": (thinking_plan or {}).get("time_reference"),
        "reasons": reasons,
    }


def compact_json_value(
    value: Any,
    *,
    max_items: int,
    max_str_len: int,
    max_depth: int,
    _depth: int = 0,
) -> Any:
    if _depth >= max_depth:
        return "...truncated(depth)"
    if isinstance(value, dict):
        out: Dict[str, Any] = {}
        for idx, (k, v) in enumerate(value.items()):
            if idx >= max_items:
                out["_truncated_keys"] = len(value) - max_items
                break
            out[str(k)] = compact_json_value(
                v,
                max_items=max_items,
                max_str_len=max_str_len,
                max_depth=max_depth,
                _depth=_depth + 1,
            )
        return out
    if isinstance(value, list):
        out = [
            compact_json_value(
                item,
                max_items=max_items,
                max_str_len=max_str_len,
                max_depth=max_depth,
                _depth=_depth + 1,
            )
            for item in value[:max_items]
        ]
        if len(value) > max_items:
            out.append(f"...truncated {len(value) - max_items} item(s)")
        return out
    if isinstance(value, str) and len(value) > max_str_len:
        cut = len(value) - max_str_len
        return value[:max_str_len] + f"... (truncated {cut} chars)"
    return value


def clip_json_text(json_text: str, cap: int) -> str:
    if cap <= 0:
        return ""
    try:
        payload = json.loads(json_text)
    except Exception:
        return ""

    profiles = [
        (12, 1200, 5),
        (8, 600, 4),
        (4, 240, 3),
        (2, 120, 2),
        (1, 60, 1),
    ]
    for max_items, max_str_len, max_depth in profiles:
        compact = compact_json_value(
            payload,
            max_items=max_items,
            max_str_len=max_str_len,
            max_depth=max_depth,
        )
        candidate = json.dumps(compact, ensure_ascii=False, separators=(",", ":"))
        if len(candidate) <= cap:
            return candidate

    if isinstance(payload, dict):
        fallback = json.dumps(
            {"_truncated": True, "type": "object", "keys": len(payload)},
            ensure_ascii=False,
            separators=(",", ":"),
        )
    elif isinstance(payload, list):
        fallback = json.dumps(
            ["_truncated", "array", len(payload)],
            ensure_ascii=False,
            separators=(",", ":"),
        )
    elif isinstance(payload, str):
        fallback = json.dumps(
            payload[: max(0, min(len(payload), cap - 2))],
            ensure_ascii=False,
            separators=(",", ":"),
        )
    else:
        fallback = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))

    if len(fallback) <= cap:
        return fallback
    if cap >= 2:
        return "{}"
    return ""


def is_tool_context_block_header(line: str) -> bool:
    header = line.lstrip()
    return (
        header.startswith("[COMPACT-CONTEXT-ON-FAILURE]")
        or header.startswith("[TOOL-CARD:")
        or header.startswith("### ")
        or header.startswith("[request_container]:")
    )


def split_tool_context_blocks(tool_context: str) -> List[str]:
    if not tool_context:
        return []
    lines = tool_context.splitlines(keepends=True)
    blocks: List[str] = []
    current: List[str] = []
    for line in lines:
        if current and is_tool_context_block_header(line):
            blocks.append("".join(current))
            current = [line]
        else:
            current.append(line)
    if current:
        blocks.append("".join(current))
    return blocks


def clip_tool_context_line(line: str, max_chars: int) -> str:
    if max_chars <= 0:
        return ""
    if len(line) <= max_chars:
        return line

    has_nl = line.endswith("\n")
    base = line[:-1] if has_nl else line
    left_ws = base[: len(base) - len(base.lstrip())]
    core = base[len(left_ws):]
    core_stripped = core.strip()
    nl_len = 1 if has_nl else 0
    core_budget = max_chars - len(left_ws) - nl_len

    if core_budget > 2 and core_stripped and core_stripped[0] in "{[" and core_stripped[-1] in "}]":
        clipped_json = clip_json_text(core_stripped, core_budget)
        if clipped_json:
            out = left_ws + clipped_json
            if has_nl and len(out) + 1 <= max_chars:
                out += "\n"
            return out

    if core_budget <= 0:
        return ""
    marker = "... [truncated]"
    if core_budget <= len(marker):
        short = core[:core_budget]
    else:
        keep = core_budget - len(marker)
        dropped = max(0, len(core) - keep)
        marker = f"... [truncated {dropped} chars]"
        if len(marker) > core_budget:
            marker = "... [truncated]"
            keep = max(0, core_budget - len(marker))
        short = core[:keep] + marker
    out = left_ws + short
    if has_nl and len(out) + 1 <= max_chars:
        out += "\n"
    return out


def compact_tool_context_block(block: str, max_chars: int) -> str:
    if max_chars <= 0:
        return ""
    if len(block) <= max_chars:
        return block

    lines = block.splitlines(keepends=True)
    out: List[str] = []
    used = 0
    for line in lines:
        if used >= max_chars:
            break
        remaining = max_chars - used
        if len(line) <= remaining:
            out.append(line)
            used += len(line)
            continue
        clipped = clip_tool_context_line(line, remaining)
        if clipped:
            out.append(clipped)
            used += len(clipped)
        break

    suffix = "\n[...block truncated]\n"
    if used < len(block) and used + len(suffix) <= max_chars:
        out.append(suffix)
    return "".join(out)


def clip_tool_context_structured(tool_context: str, cap: int) -> str:
    marker = "\n[...tool_context truncated...]\n"
    body_cap = cap - len(marker)
    if body_cap <= 0:
        return tool_context[:cap]

    blocks = split_tool_context_blocks(tool_context)
    if not blocks:
        return tool_context[:cap]

    chosen: List[str] = []
    used = 0
    for idx in range(len(blocks) - 1, -1, -1):
        block = blocks[idx]
        remaining = body_cap - used
        if remaining <= 0:
            break
        if len(block) <= remaining:
            chosen.append(block)
            used += len(block)
            continue
        compact = compact_tool_context_block(block, remaining)
        if compact:
            chosen.append(compact)
            used += len(compact)
        break

    body = "".join(reversed(chosen))
    if not body:
        body = tool_context[-body_cap:]
    if len(body) > body_cap:
        body = body[-body_cap:]
    return marker + body


def prepend_with_cap(prefix: str, content: str, cap: int) -> str:
    if cap <= 0:
        return ""
    if len(prefix) >= cap:
        return prefix[:cap]
    keep = max(0, cap - len(prefix))
    return prefix + content[:keep]


def clip_tool_context(
    tool_context: str,
    *,
    small_model_mode: bool,
    get_small_model_tool_ctx_cap_fn: Callable[[], int],
    tool_context_has_failures_or_skips_fn: Callable[[str], bool],
    log_warn_fn: Callable[[str], None],
) -> str:
    if not small_model_mode or not tool_context:
        return tool_context
    cap = get_small_model_tool_ctx_cap_fn()
    if cap <= 0 or len(tool_context) <= cap:
        return tool_context

    had_failure_or_skip = tool_context_has_failures_or_skips_fn(tool_context)
    stripped = tool_context.strip()
    if stripped and stripped[0] in "{[" and stripped[-1] in "}]":
        clipped_json = clip_json_text(stripped, cap)
        if clipped_json:
            tool_context = clipped_json
            log_warn_fn(
                f"[CTX] tool_context clipped to {cap} chars (json-aware, {len(tool_context)} kept)"
            )
        else:
            tool_context = tool_context[:cap]
            log_warn_fn(f"[CTX] tool_context clipped to {cap} chars (json-fallback hard-cut)")
    else:
        looks_structured = bool(
            re.search(
                r"(?m)^(?:\[COMPACT-CONTEXT-ON-FAILURE\]|\[TOOL-CARD:|### |\[request_container\]:)",
                tool_context,
            )
        )
        if looks_structured:
            tool_context = clip_tool_context_structured(tool_context, cap)
            log_warn_fn(
                f"[CTX] tool_context clipped to {cap} chars (structured, {len(tool_context)} kept)"
            )
        else:
            clipped = len(tool_context) - cap
            marker = f"\n[...truncated: {clipped} chars]"
            keep = cap - len(marker)
            if keep <= 0:
                tool_context = tool_context[:cap]
            else:
                tool_context = tool_context[:keep] + marker
            log_warn_fn(f"[CTX] tool_context clipped to {cap} chars ({clipped} truncated)")

    if had_failure_or_skip and not tool_context_has_failures_or_skips_fn(tool_context):
        failure_guard = (
            "\n### TOOL-FEHLER (truncated): Frühere Fehler/Skips wurden "
            "wegen Context-Limit gekürzt.\n"
        )
        tool_context = prepend_with_cap(failure_guard, tool_context, cap)
        log_warn_fn("[CTX] tool_context failure marker re-injected after clipping")

    return tool_context
