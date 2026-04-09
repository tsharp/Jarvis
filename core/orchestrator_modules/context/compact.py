from __future__ import annotations

from typing import Any, Dict, Optional, Set


def get_compact_context(
    *,
    context_manager: Any,
    conversation_id: Optional[str],
    has_tool_failure: bool = False,
    exclude_event_types: Optional[Set[str]] = None,
    csv_trigger: Optional[str] = None,
    log_info_fn: Any,
    log_warn_fn: Any,
) -> str:
    from config import (
        get_jit_retrieval_max,
        get_jit_retrieval_max_on_failure,
        get_small_model_mode,
        get_small_model_next_max,
        get_small_model_now_max,
        get_small_model_rules_max,
    )

    if not get_small_model_mode():
        return ""

    try:
        retrieval_budget = (
            get_jit_retrieval_max_on_failure() if has_tool_failure else get_jit_retrieval_max()
        )
        retrieval_count = 1 + (
            1 if retrieval_budget >= 2 and conversation_id != "_container_events" else 0
        )
        limits: Dict[str, Any] = {
            "now_max": get_small_model_now_max(),
            "rules_max": get_small_model_rules_max(),
            "next_max": get_small_model_next_max(),
            "retrieval_count": retrieval_count,
            "csv_trigger": csv_trigger,
        }

        text = context_manager.build_small_model_context(
            conversation_id=conversation_id,
            limits=limits,
            exclude_event_types=exclude_event_types,
            trigger=csv_trigger,
        )

        if retrieval_budget >= 2 and conversation_id != "_container_events":
            container_ctx = context_manager.build_small_model_context(
                conversation_id="_container_events",
                limits={
                    "now_max": 3,
                    "rules_max": 0,
                    "next_max": 1,
                    "retrieval_count": retrieval_count,
                },
                exclude_event_types=exclude_event_types,
            )
            if container_ctx:
                text = text + "\n" + container_ctx if text else container_ctx

        log_info_fn(
            f"[Orchestrator] cleanup_used=True retrieval_count={retrieval_count} "
            f"context_chars={len(text)} failure={has_tool_failure}"
        )
        return text
    except Exception as exc:
        log_warn_fn(f"[Orchestrator] _get_compact_context failed: {exc}")
        try:
            from core.context_cleanup import _minimal_fail_context, format_compact_context

            return format_compact_context(_minimal_fail_context())
        except Exception:
            return (
                "NOW:\n  - CONTEXT ERROR: Zustand unvollständig\n"
                "NEXT:\n  - Bitte Anfrage kurz präzisieren oder letzten Schritt wiederholen"
            )


def apply_effective_context_guardrail(
    *,
    ctx: str,
    trace: Dict[str, Any],
    small_model_mode: bool,
    label: str,
    log_warn_fn: Any,
) -> str:
    if small_model_mode:
        return ctx

    from config import get_effective_context_guardrail_chars

    cap = get_effective_context_guardrail_chars()
    if cap <= 0 or len(ctx) <= cap:
        return ctx

    marker = "\n[...context truncated by guardrail...]\n"
    keep_head = max(0, int(cap * 0.7))
    keep_tail = max(0, cap - keep_head - len(marker))
    if keep_tail <= 0:
        clipped = ctx[:cap]
    else:
        clipped = ctx[:keep_head] + marker + ctx[-keep_tail:]

    trace["context_chars_final"] = len(clipped)
    if "guardrail_ctx" not in trace["context_sources"]:
        trace["context_sources"].append("guardrail_ctx")
    log_warn_fn(
        f"[CTX] guardrail enforced ({label}): {len(ctx)} → {len(clipped)} chars "
        f"(cap={cap})"
    )
    return clipped
