"""Prompt payload helpers for ControlLayer verification."""

from __future__ import annotations

import json
from typing import Any


def clip_text(text: str, max_chars: int) -> str:
    """Trim text to a compact prompt-safe size while preserving truncation context."""
    raw = str(text or "").strip()
    if max_chars <= 0:
        return ""
    if len(raw) <= max_chars:
        return raw
    suffix = f"\n...[truncated {len(raw) - max_chars} chars]"
    keep = max(0, max_chars - len(suffix))
    return raw[:keep].rstrip() + suffix


def tool_names(raw_tools: list[Any], limit: int = 8) -> list[str]:
    """Normalize heterogeneous tool entries into unique tool names."""
    names: list[str] = []
    seen = set()
    for item in raw_tools or []:
        if isinstance(item, dict):
            name = str(item.get("tool") or item.get("name") or "").strip()
        else:
            name = str(item or "").strip()
        if not name or name in seen:
            continue
        names.append(name)
        seen.add(name)
        if len(names) >= limit:
            break
    return names


def memory_keys(keys: list[Any], *, get_memory_keys_max_per_request_fn) -> list[str]:
    """Normalize and cap memory keys for compact prompt transport."""
    normalized: list[str] = []
    seen = set()
    limit = int(get_memory_keys_max_per_request_fn())
    for key in keys or []:
        value = str(key or "").strip()
        if not value or value in seen:
            continue
        normalized.append(value)
        seen.add(value)
        if len(normalized) >= limit:
            break
    return normalized


def build_control_prompt_payload(
    user_text: str,
    thinking_plan: dict[str, Any],
    retrieved_memory: str,
    *,
    get_control_prompt_user_chars_fn,
    get_control_prompt_plan_chars_fn,
    get_control_prompt_memory_chars_fn,
    memory_keys_fn,
    tool_names_fn,
    clip_text_fn,
    tool_availability_snapshot_fn,
) -> dict[str, Any]:
    """Build the compact serialized payload sent into the Control prompt."""
    user_limit = int(get_control_prompt_user_chars_fn())
    plan_limit = int(get_control_prompt_plan_chars_fn())
    memory_limit = int(get_control_prompt_memory_chars_fn())

    plan_payload: dict[str, Any] = {
        "intent": str((thinking_plan or {}).get("intent", ""))[:300],
        "hallucination_risk": (thinking_plan or {}).get("hallucination_risk", "medium"),
        "needs_memory": bool((thinking_plan or {}).get("needs_memory")),
        "is_fact_query": bool((thinking_plan or {}).get("is_fact_query")),
        "resolution_strategy": str((thinking_plan or {}).get("resolution_strategy") or "").strip().lower() or None,
        "memory_keys": memory_keys_fn((thinking_plan or {}).get("memory_keys", [])),
        "suggested_tools": tool_names_fn((thinking_plan or {}).get("suggested_tools", [])),
        "suggested_response_style": (thinking_plan or {}).get("suggested_response_style"),
        "dialogue_act": (thinking_plan or {}).get("dialogue_act"),
        "response_tone": (thinking_plan or {}).get("response_tone"),
        "response_length_hint": (thinking_plan or {}).get("response_length_hint"),
        "tone_confidence": (thinking_plan or {}).get("tone_confidence"),
        "time_reference": (thinking_plan or {}).get("time_reference"),
        "needs_sequential_thinking": bool(
            (thinking_plan or {}).get("needs_sequential_thinking")
            or (thinking_plan or {}).get("sequential_thinking_required")
        ),
        "sequential_complexity": (thinking_plan or {}).get("sequential_complexity", 0),
    }
    plan_payload["tool_availability"] = tool_availability_snapshot_fn(
        plan_payload.get("suggested_tools", [])
    )
    route = (thinking_plan or {}).get("_domain_route", {})
    if isinstance(route, dict) and route:
        plan_payload["domain_route"] = {
            "domain_tag": str(route.get("domain_tag") or "").strip().upper(),
            "domain_locked": bool(route.get("domain_locked")),
            "operation": str(route.get("operation") or "").strip().lower(),
        }
    if (thinking_plan or {}).get("_policy_conflict_reason"):
        plan_payload["policy_conflict_reason"] = str(
            (thinking_plan or {}).get("_policy_conflict_reason", "")
        )[:200]
    if (thinking_plan or {}).get("_sequential_deferred"):
        plan_payload["sequential_deferred"] = True
        plan_payload["sequential_deferred_reason"] = str(
            (thinking_plan or {}).get("_sequential_deferred_reason", "")
        )[:120]
    if (thinking_plan or {}).get("_skill_gate_blocked"):
        plan_payload["skill_gate_blocked"] = True
        plan_payload["skill_gate_reason"] = (thinking_plan or {}).get("_skill_gate_reason", "")
    if (thinking_plan or {}).get("_blueprint_gate_blocked"):
        plan_payload["blueprint_gate_blocked"] = True
        plan_payload["blueprint_gate_reason"] = (thinking_plan or {}).get("_blueprint_gate_reason", "")
    if bool((thinking_plan or {}).get("_hardware_gate_triggered")):
        plan_payload["hardware_gate_triggered"] = True
        plan_payload["hardware_gate_warning"] = str(
            (thinking_plan or {}).get("_hardware_gate_warning") or ""
        )[:240]
    container_resolution = (thinking_plan or {}).get("_container_resolution")
    if isinstance(container_resolution, dict) and container_resolution:
        plan_payload["container_resolution"] = {
            "decision": str(container_resolution.get("decision") or "").strip(),
            "blueprint_id": str(container_resolution.get("blueprint_id") or "").strip(),
            "score": container_resolution.get("score", 0.0),
            "reason": str(container_resolution.get("reason") or "")[:200],
        }
    raw_candidates = (thinking_plan or {}).get("_container_candidates")
    if isinstance(raw_candidates, list) and raw_candidates:
        compact_candidates = []
        for row in raw_candidates[:3]:
            if not isinstance(row, dict):
                continue
            compact_candidates.append(
                {
                    "id": str(row.get("id") or row.get("blueprint_id") or "").strip(),
                    "score": row.get("score", 0.0),
                }
            )
        if compact_candidates:
            plan_payload["container_candidates"] = compact_candidates

    plan_json = json.dumps(plan_payload, ensure_ascii=False)
    if len(plan_json) > plan_limit:
        plan_payload = {
            "intent": plan_payload["intent"],
            "hallucination_risk": plan_payload["hallucination_risk"],
            "needs_memory": plan_payload["needs_memory"],
            "memory_keys": plan_payload["memory_keys"][:2],
            "suggested_tools": plan_payload["suggested_tools"][:4],
            "tool_availability": plan_payload.get("tool_availability", {}),
        }
        plan_json = clip_text_fn(json.dumps(plan_payload, ensure_ascii=False), plan_limit)
    else:
        plan_json = clip_text_fn(plan_json, plan_limit)

    memory_excerpt = clip_text_fn(retrieved_memory, memory_limit) if retrieved_memory else "(keine)"

    return {
        "user_request": clip_text_fn(user_text, user_limit),
        "thinking_plan_compact": plan_json,
        "memory_excerpt": memory_excerpt,
    }
