from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional, Tuple


def append_context_block(
    ctx_str: str,
    new_block: str,
    source_name: str,
    trace: Dict[str, Any],
    *,
    prepend: bool = False,
) -> str:
    if not new_block:
        return ctx_str
    updated = (new_block + ctx_str) if prepend else (ctx_str + new_block)
    trace["context_sources"].append(source_name)
    trace["context_chars_final"] += len(new_block)
    return updated


def build_failure_compact_block(
    conv_id: Optional[str],
    current_context_len: int,
    small_model_mode: bool,
    *,
    get_compact_context_fn: Callable[..., str],
) -> str:
    compact = get_compact_context_fn(
        conv_id,
        has_tool_failure=True,
        exclude_event_types={"tool_result"},
    )
    if not compact:
        return ""
    if small_model_mode:
        from config import get_small_model_char_cap

        overhead = len("[COMPACT-CONTEXT-ON-FAILURE]\n") + len("\n\n")
        budget = max(0, get_small_model_char_cap() - current_context_len - overhead)
        compact = compact[:budget]
    if not compact:
        return ""
    return f"[COMPACT-CONTEXT-ON-FAILURE]\n{compact}\n\n"


def apply_final_cap(
    ctx: str,
    trace: Dict[str, Any],
    small_model_mode: bool,
    label: str,
    *,
    log_warn_fn: Callable[[str], None],
) -> str:
    if not small_model_mode:
        return ctx

    from config import get_small_model_char_cap, get_small_model_final_cap

    cap = get_small_model_final_cap()
    if cap <= 0:
        cap = get_small_model_char_cap()
    if len(ctx) > cap:
        orig = len(ctx)
        ctx = ctx[:cap]
        trace["context_chars_final"] = cap
        log_warn_fn(f"[CTX] FINAL CAP enforced ({label}): {orig} → {cap} chars")
    return ctx


def tool_context_has_failures_or_skips(tool_context: str) -> bool:
    if not tool_context:
        return False
    markers = (
        "TOOL-FEHLER",
        "VERIFY-FEHLER",
        "TOOL-SKIP",
        "[request_container]: FEHLER",
        "[request_container]: RÜCKFRAGE",
    )
    return any(marker in tool_context for marker in markers)


def tool_context_has_success(tool_context: str) -> bool:
    if not tool_context:
        return False
    return "[TOOL-CARD:" in tool_context and "| ✅ ok |" in tool_context


def maybe_prefetch_skills(
    user_text: str,
    selected_tools: List[Any],
    *,
    get_skill_context_fn: Callable[[str], str],
    read_only_skill_tools: List[str],
    log_debug_fn: Callable[[str], None],
) -> Tuple[str, str]:
    from config import (
        get_skill_context_renderer,
        get_small_model_mode,
        get_small_model_skill_prefetch_policy,
        get_small_model_skill_prefetch_thin_cap,
    )

    renderer = get_skill_context_renderer()

    if not get_small_model_mode():
        ctx = get_skill_context_fn(user_text)
        return ctx, "full"

    policy = get_small_model_skill_prefetch_policy()

    skill_tools = set(read_only_skill_tools).union({"autonomous_skill_task"})
    has_skill_intent = bool(
        selected_tools
        and skill_tools
        & {
            (tool.get("name", "") if isinstance(tool, dict) else str(tool))
            for tool in selected_tools
        }
    )

    if policy == "off" and not has_skill_intent:
        return "", "off"

    ctx = get_skill_context_fn(user_text)
    if not ctx:
        return "", "off"

    if renderer == "legacy":
        thin_cap = get_small_model_skill_prefetch_thin_cap()
        lines = ctx.splitlines()
        header = lines[0] if lines else ""
        skill_lines = [line for line in lines[1:] if line.strip().startswith("-")]
        thin_ctx = "\n".join([header] + skill_lines[:1]).strip()
        thin_ctx = thin_ctx[:thin_cap]
        log_debug_fn(
            f"[Orchestrator] Skill prefetch thin (legacy): {len(thin_ctx)} chars (cap={thin_cap})"
        )
        return thin_ctx, "thin"

    log_debug_fn(f"[Orchestrator] Skill prefetch (typedstate): {len(ctx)} chars")
    return ctx, "thin"


def verify_container_running(
    container_id: str,
    *,
    get_hub_fn: Callable[[], Any],
    log_info_fn: Callable[[str], None],
    log_warn_fn: Callable[[str], None],
) -> bool:
    try:
        hub = get_hub_fn()
        hub.initialize()
        result = hub.call_tool("container_stats", {"container_id": container_id})
        if isinstance(result, dict) and not result.get("error"):
            log_info_fn(f"[Orchestrator-Verify] Container {container_id[:12]} confirmed running")
            return True
        log_warn_fn(f"[Orchestrator-Verify] Container {container_id[:12]} NOT running: {result}")
        return False
    except Exception as exc:
        log_warn_fn(f"[Orchestrator-Verify] Check failed for {container_id[:12]}: {exc}")
        return False


def build_summary_from_structure(structure: Dict[str, Any]) -> str:
    lines = []
    lines.append("# Document Overview")
    lines.append(
        f"- Size: {structure.get('total_chars', 0)} chars, {structure.get('total_tokens', 0)} tokens"
    )
    lines.append(f"- Complexity: {structure.get('complexity', 0)}/10")

    if structure.get("headings"):
        lines.append(f"\n## Structure ({len(structure['headings'])} headings):")
        for heading in structure["headings"][:5]:
            lines.append(f"- {heading.get('level', 1) * '#'} {heading.get('text', '')}")

    if structure.get("keywords"):
        lines.append(f"\n## Keywords: {', '.join(structure['keywords'][:10])}")

    if structure.get("intro"):
        lines.append(f"\n## Intro:\n{structure['intro'][:300]}...")

    return "\n".join(lines)


async def execute_thinking_layer(
    user_text: str,
    *,
    thinking_layer: Any,
    log_info_fn: Callable[[str], None],
) -> Dict[str, Any]:
    log_info_fn("[Orchestrator] === LAYER 1: THINKING ===")
    thinking_plan = await thinking_layer.analyze(user_text)

    log_info_fn(f"[Orchestrator-Thinking] intent={thinking_plan.get('intent')}")
    log_info_fn(f"[Orchestrator-Thinking] needs_memory={thinking_plan.get('needs_memory')}")
    log_info_fn(f"[Orchestrator-Thinking] memory_keys={thinking_plan.get('memory_keys')}")
    log_info_fn(f"[Orchestrator-Thinking] hallucination_risk={thinking_plan.get('hallucination_risk')}")
    return thinking_plan
