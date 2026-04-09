from typing import Any, Callable, Dict, List, Optional, Sequence


_EFFECTIVE_RESOLUTION_STRATEGIES = {
    "container_inventory",
    "container_blueprint_catalog",
    "container_state_binding",
    "container_request",
    "active_container_capability",
    "home_container_info",
    "skill_catalog_context",
}


def tool_name_list(
    suggested_tools: Optional[List[Any]],
    *,
    extract_tool_name_fn: Callable[[Any], str],
) -> List[str]:
    out: List[str] = []
    for tool in suggested_tools or []:
        name = extract_tool_name_fn(tool).strip()
        if name:
            out.append(name)
    return out


def get_effective_resolution_strategy(verified_plan: Optional[Dict[str, Any]]) -> str:
    if not isinstance(verified_plan, dict):
        return ""
    for key in ("_authoritative_resolution_strategy", "resolution_strategy"):
        strategy = str(verified_plan.get(key) or "").strip().lower()
        if strategy in _EFFECTIVE_RESOLUTION_STRATEGIES:
            return strategy
    return ""


def looks_like_host_runtime_lookup(user_text: str) -> bool:
    lower = str(user_text or "").strip().lower()
    if not lower:
        return False
    has_target = any(
        token in lower
        for token in (
            "host server",
            "host-server",
            "server",
            "host",
            "ip adresse",
            "ip-adresse",
            "ip address",
        )
    )
    if not has_target:
        return False
    return any(
        token in lower
        for token in (
            "find",
            "finden",
            "ermittel",
            "heraus",
            "auslesen",
            "check",
            "prüf",
            "pruef",
            "zeige",
            "gib",
        )
    )


def container_state_has_active_target(state: Optional[Dict[str, Any]]) -> bool:
    if not isinstance(state, dict):
        return False
    if str(state.get("last_active_container_id", "")).strip():
        return True
    if str(state.get("home_container_id", "")).strip():
        return True
    for row in state.get("known_containers") or []:
        if not isinstance(row, dict):
            continue
        if str(row.get("status", "")).strip().lower() == "running":
            return True
    return False


def is_active_container_capability_query(
    user_text: str,
    *,
    active_container_capability_exclude_markers: Sequence[str],
    active_container_deictic_markers: Sequence[str],
    active_container_capability_markers: Sequence[str],
) -> bool:
    text = str(user_text or "").strip().lower()
    if not text:
        return False
    if any(marker in text for marker in active_container_capability_exclude_markers):
        return False
    has_deictic_marker = any(marker in text for marker in active_container_deictic_markers)
    if not has_deictic_marker:
        return False
    return any(marker in text for marker in active_container_capability_markers)


def is_container_request_query(
    user_text: str,
    *,
    container_request_query_markers: Sequence[str],
) -> bool:
    text = str(user_text or "").strip().lower()
    if not text:
        return False
    return any(marker in text for marker in container_request_query_markers)


def is_container_blueprint_catalog_query(
    user_text: str,
    *,
    container_blueprint_query_markers: Sequence[str],
    is_container_request_query_fn: Callable[[str], bool],
) -> bool:
    text = str(user_text or "").strip().lower()
    if not text:
        return False
    if is_container_request_query_fn(text):
        return False
    return any(marker in text for marker in container_blueprint_query_markers)


def is_container_inventory_query(
    user_text: str,
    *,
    container_inventory_query_markers: Sequence[str],
    is_container_blueprint_catalog_query_fn: Callable[[str], bool],
    is_container_request_query_fn: Callable[[str], bool],
) -> bool:
    text = str(user_text or "").strip().lower()
    if not text:
        return False
    if is_container_blueprint_catalog_query_fn(text) or is_container_request_query_fn(text):
        return False
    return any(marker in text for marker in container_inventory_query_markers)


def is_container_state_binding_query(
    user_text: str,
    *,
    container_state_query_markers: Sequence[str],
    is_active_container_capability_query_fn: Callable[[str], bool],
) -> bool:
    text = str(user_text or "").strip().lower()
    if not text:
        return False
    if is_active_container_capability_query_fn(text):
        return False
    return any(marker in text for marker in container_state_query_markers)


def is_skill_catalog_context_query(
    user_text: str,
    *,
    skill_catalog_exclude_markers: Sequence[str],
    skill_catalog_query_markers: Sequence[str],
) -> bool:
    text = str(user_text or "").strip().lower().replace("-", " ")
    if not text:
        return False
    if any(marker in text for marker in skill_catalog_exclude_markers):
        return False
    return any(marker in text for marker in skill_catalog_query_markers)


def should_prioritize_skill_catalog_route(
    verified_plan: Optional[Dict[str, Any]],
    *,
    user_text: str = "",
    get_effective_resolution_strategy_fn: Callable[[Optional[Dict[str, Any]]], str],
    is_skill_catalog_context_query_fn: Callable[[str], bool],
) -> bool:
    if get_effective_resolution_strategy_fn(verified_plan) == "skill_catalog_context":
        return True
    return is_skill_catalog_context_query_fn(user_text)


def select_read_only_skill_tool_for_query(
    user_text: str,
    verified_plan: Optional[Dict[str, Any]] = None,
) -> str:
    hints = verified_plan.get("strategy_hints") if isinstance(verified_plan, dict) else []
    normalized_hints = {
        str(hint or "").strip().lower()
        for hint in (hints if isinstance(hints, list) else [])
        if str(hint or "").strip()
    }
    normalized_text = str(user_text or "").strip().lower().replace("-", " ")
    if "draft_skills" in normalized_hints or "draft skill" in normalized_text:
        return "list_draft_skills"
    return "list_skills"


def materialize_skill_catalog_policy(
    verified_plan: Optional[Dict[str, Any]],
    *,
    effective_resolution_strategy: str,
    read_only_skill_tools: Sequence[str],
    skill_action_tools: Sequence[str],
    tool_name_list_fn: Callable[[Optional[List[Any]]], List[str]],
) -> Dict[str, Any]:
    if not isinstance(verified_plan, dict):
        return {}
    if effective_resolution_strategy != "skill_catalog_context":
        return {}

    raw_hints = verified_plan.get("strategy_hints")
    strategy_hints = [
        str(hint or "").strip().lower()
        for hint in (raw_hints if isinstance(raw_hints, list) else [])
        if str(hint or "").strip()
    ]
    hint_set = set(strategy_hints)

    suggested_tools = tool_name_list_fn(
        verified_plan.get("_authoritative_suggested_tools")
        or verified_plan.get("suggested_tools")
        or []
    )
    read_only_tools = [
        name for name in suggested_tools if name in read_only_skill_tools
    ]
    has_non_read_only_skill_tools = any(
        name in skill_action_tools for name in suggested_tools
    )
    followup_split_required = bool("fact_then_followup" in hint_set)

    required_tools: List[str] = []

    def _add_required(tool_name: str) -> None:
        if tool_name and tool_name not in required_tools:
            required_tools.append(tool_name)

    draft_focus = "list_draft_skills" in read_only_tools or (
        "draft_skills" in hint_set and not followup_split_required
    )
    runtime_focus = bool(
        {
            "runtime_skills",
            "tools_vs_skills",
            "overview",
            "fact_then_followup",
        }.intersection(hint_set)
    ) or "list_skills" in read_only_tools

    if draft_focus:
        _add_required("list_draft_skills")
    if runtime_focus or not required_tools:
        _add_required("list_skills")
    if "get_skill_info" in read_only_tools:
        _add_required("get_skill_info")

    force_sections = ["Runtime-Skills", "Einordnung"]
    if followup_split_required:
        force_sections.append("Wunsch-Skills")

    policy = {
        "mode": "mixed" if has_non_read_only_skill_tools else "inventory_read_only",
        "required_tools": required_tools,
        "force_sections": force_sections,
        "draft_explanation_required": bool(
            draft_focus or "tools_vs_skills" in hint_set
        ),
        "followup_split_required": followup_split_required,
        "allow_sequential": False,
        "semantic_guardrails_only": True,
        "selected_hints": strategy_hints,
    }
    verified_plan["_skill_catalog_policy"] = policy
    return policy


def record_execution_tool_trace(
    verified_plan: Optional[Dict[str, Any]],
    suggested_tools: Optional[List[Any]],
    *,
    tool_name_list_fn: Callable[[Optional[List[Any]]], List[str]],
    get_effective_resolution_strategy_fn: Callable[[Optional[Dict[str, Any]]], str],
) -> None:
    if not isinstance(verified_plan, dict):
        return
    thinking_tools = tool_name_list_fn(
        verified_plan.get("_thinking_suggested_tools")
        or verified_plan.get("suggested_tools")
        or []
    )
    final_tools = tool_name_list_fn(suggested_tools)
    verified_plan["_thinking_suggested_tools"] = thinking_tools
    verified_plan["_final_execution_tools"] = final_tools

    if get_effective_resolution_strategy_fn(verified_plan) != "skill_catalog_context":
        return

    domain_gate = verified_plan.get("_domain_gate")
    domain_gate = domain_gate if isinstance(domain_gate, dict) else {}
    dropped = int(domain_gate.get("dropped", 0) or 0)
    domain_seeded = bool(verified_plan.get("_domain_tool_seeded"))
    changed = final_tools != thinking_tools
    if not final_tools and thinking_tools:
        status = "suppressed"
    elif changed or domain_seeded:
        status = "rerouted"
    else:
        status = "unchanged"
    reasons: List[str] = []
    if bool(verified_plan.get("_skill_catalog_domain_priority")) or (
        status in {"rerouted", "suppressed"}
        and get_effective_resolution_strategy_fn(verified_plan) == "skill_catalog_context"
    ):
        reasons.append("skill_catalog_priority")
    if domain_seeded:
        reasons.append("domain_seeded")
    if dropped > 0:
        reasons.append(f"domain_filtered:{dropped}")
    if changed and not reasons:
        reasons.append("tool_selection_changed")
    verified_plan["_skill_catalog_tool_route"] = {
        "status": status,
        "reason": ", ".join(reasons) if reasons else "none",
        "thinking_suggested_tools": thinking_tools,
        "final_execution_tools": final_tools,
    }


def finalize_execution_suggested_tools(
    verified_plan: Optional[Dict[str, Any]],
    suggested_tools: Optional[List[Any]],
    *,
    tool_name_list_fn: Callable[[Optional[List[Any]]], List[str]],
    record_execution_tool_trace_fn: Callable[[Optional[Dict[str, Any]], Optional[List[Any]]], None],
) -> List[Any]:
    selected = list(suggested_tools or [])
    if isinstance(verified_plan, dict):
        verified_plan["_selected_tools_for_prompt"] = tool_name_list_fn(selected)
    record_execution_tool_trace_fn(verified_plan, selected)
    return selected


def _resolve_domain_allowed_tools(
    *,
    domain_tag: str,
    verified_plan: Optional[Dict[str, Any]],
    user_text: str,
    domain_cron_tools: Sequence[str],
    read_only_skill_tools: Sequence[str],
    domain_skill_tools: Sequence[str],
    domain_container_tools: Sequence[str],
    should_prioritize_skill_catalog_route_fn: Callable[[Optional[Dict[str, Any]], str], bool],
) -> List[str]:
    skill_catalog_route_priority = (
        domain_tag == "SKILL"
        and should_prioritize_skill_catalog_route_fn(verified_plan, user_text)
    )
    if domain_tag == "CRONJOB":
        return list(domain_cron_tools)
    if skill_catalog_route_priority:
        return list(read_only_skill_tools)
    if domain_tag == "SKILL":
        return list(domain_skill_tools)
    if domain_tag == "CONTAINER":
        return list(domain_container_tools)
    return []


def seed_tool_for_domain_route(
    route: Optional[Dict[str, Any]],
    *,
    user_text: str = "",
    suggested_tools: Optional[List[Any]] = None,
    verified_plan: Optional[Dict[str, Any]] = None,
    domain_cron_op_to_tool: Dict[str, str],
    domain_container_op_to_tool: Dict[str, str],
    domain_container_tools: Sequence[str],
    should_prioritize_skill_catalog_route_fn: Callable[[Optional[Dict[str, Any]], str], bool],
    select_read_only_skill_tool_for_query_fn: Callable[[str, Optional[Dict[str, Any]]], str],
    looks_like_host_runtime_lookup_fn: Callable[[str], bool],
    extract_tool_name_fn: Callable[[Any], str],
) -> str:
    if not isinstance(route, dict):
        return ""
    tag = str(route.get("domain_tag") or "").strip().upper()
    if tag == "CRONJOB":
        op = str(route.get("operation") or "").strip().lower()
        return domain_cron_op_to_tool.get(op, "autonomy_cron_status")
    if tag == "SKILL":
        if should_prioritize_skill_catalog_route_fn(verified_plan, user_text):
            return select_read_only_skill_tool_for_query_fn(user_text, verified_plan)
        return "autonomous_skill_task"
    if tag == "CONTAINER":
        op = str(route.get("operation") or "").strip().lower()
        if op == "unknown" and looks_like_host_runtime_lookup_fn(user_text):
            return "exec_in_container"
        if op == "unknown":
            for tool in suggested_tools or []:
                name = extract_tool_name_fn(tool).strip().lower()
                if name in domain_container_tools:
                    return name
        return domain_container_op_to_tool.get(op, "container_list")
    return ""


def apply_domain_route_to_plan(
    thinking_plan: Dict[str, Any],
    signal: Optional[Dict[str, Any]],
    *,
    user_text: str = "",
    domain_cron_tools: Sequence[str],
    read_only_skill_tools: Sequence[str],
    domain_skill_tools: Sequence[str],
    domain_container_tools: Sequence[str],
    should_prioritize_skill_catalog_route_fn: Callable[[Optional[Dict[str, Any]], str], bool],
    extract_tool_name_fn: Callable[[Any], str],
    seed_tool_for_domain_route_fn: Callable[..., str],
) -> Dict[str, Any]:
    plan = thinking_plan if isinstance(thinking_plan, dict) else {}
    if not isinstance(signal, dict) or not signal:
        return plan

    route = dict(signal)
    plan["_domain_route"] = route

    domain_locked = bool(route.get("domain_locked"))
    domain_tag = str(route.get("domain_tag") or "").strip().upper()
    if not domain_locked or domain_tag not in {"CRONJOB", "SKILL", "CONTAINER"}:
        return plan

    allowed = _resolve_domain_allowed_tools(
        domain_tag=domain_tag,
        verified_plan=plan,
        user_text=user_text,
        domain_cron_tools=domain_cron_tools,
        read_only_skill_tools=read_only_skill_tools,
        domain_skill_tools=domain_skill_tools,
        domain_container_tools=domain_container_tools,
        should_prioritize_skill_catalog_route_fn=should_prioritize_skill_catalog_route_fn,
    )

    existing = plan.get("suggested_tools", [])
    existing_list = existing if isinstance(existing, list) else []
    existing_allowed = [
        tool
        for tool in existing_list
        if extract_tool_name_fn(tool).strip().lower() in allowed
    ]
    if existing_allowed:
        plan["suggested_tools"] = existing_allowed
        plan["_domain_tool_seeded"] = False
    else:
        seed_tool = seed_tool_for_domain_route_fn(
            route,
            user_text=user_text,
            suggested_tools=existing_list,
            verified_plan=plan,
        )
        if seed_tool:
            plan["suggested_tools"] = [seed_tool]
            plan["_domain_tool_seeded"] = True

    if domain_tag == "CRONJOB":
        plan["_domain_skill_confirmation_disabled"] = True
    elif domain_tag == "SKILL" and should_prioritize_skill_catalog_route_fn(plan, user_text):
        plan["_skill_catalog_domain_priority"] = True
    return plan


def apply_domain_tool_policy(
    verified_plan: Dict[str, Any],
    suggested_tools: List[Any],
    *,
    user_text: str = "",
    prefix: str = "[Orchestrator]",
    domain_cron_tools: Sequence[str],
    read_only_skill_tools: Sequence[str],
    domain_skill_tools: Sequence[str],
    domain_container_tools: Sequence[str],
    should_prioritize_skill_catalog_route_fn: Callable[[Optional[Dict[str, Any]], str], bool],
    seed_tool_for_domain_route_fn: Callable[..., str],
    looks_like_host_runtime_lookup_fn: Callable[[str], bool],
    extract_tool_name_fn: Callable[[Any], str],
    log_info_fn: Callable[[str], None],
) -> List[Any]:
    if not isinstance(verified_plan, dict):
        return suggested_tools

    route = verified_plan.get("_domain_route")
    if not isinstance(route, dict):
        return suggested_tools
    if not bool(route.get("domain_locked")):
        return suggested_tools

    domain_tag = str(route.get("domain_tag") or "").strip().upper()
    allowed = _resolve_domain_allowed_tools(
        domain_tag=domain_tag,
        verified_plan=verified_plan,
        user_text=user_text,
        domain_cron_tools=domain_cron_tools,
        read_only_skill_tools=read_only_skill_tools,
        domain_skill_tools=domain_skill_tools,
        domain_container_tools=domain_container_tools,
        should_prioritize_skill_catalog_route_fn=should_prioritize_skill_catalog_route_fn,
    )
    if not allowed:
        return suggested_tools

    before = len(suggested_tools or [])
    filtered = [
        tool
        for tool in (suggested_tools or [])
        if extract_tool_name_fn(tool).strip().lower() in allowed
    ]
    dropped = max(0, before - len(filtered))

    if not filtered:
        if domain_tag == "SKILL" and bool(verified_plan.get("_skill_gate_blocked")):
            log_info_fn(
                f"{prefix} Domain gate skipped SKILL reseed: "
                f"reason={verified_plan.get('_skill_gate_reason') or 'skill_gate_blocked'}"
            )
        else:
            seed_tool = seed_tool_for_domain_route_fn(
                route,
                user_text=user_text,
                suggested_tools=suggested_tools,
                verified_plan=verified_plan,
            )
            if seed_tool and seed_tool in allowed:
                filtered = [seed_tool]

    if dropped or before == 0:
        verified_plan["_domain_gate"] = {
            "domain_tag": domain_tag,
            "dropped": dropped,
            "kept": [extract_tool_name_fn(t) for t in filtered],
        }
        log_info_fn(
            f"{prefix} Domain gate applied: tag={domain_tag} dropped={dropped} "
            f"kept={verified_plan['_domain_gate']['kept']}"
        )

    if domain_tag == "CONTAINER" and looks_like_host_runtime_lookup_fn(user_text):
        has_exec = any(
            extract_tool_name_fn(tool).strip().lower() == "exec_in_container"
            for tool in filtered
        )
        has_request = any(
            extract_tool_name_fn(tool).strip().lower() == "request_container"
            for tool in filtered
        )
        if has_exec and has_request:
            filtered = [
                tool
                for tool in filtered
                if extract_tool_name_fn(tool).strip().lower() != "request_container"
            ]
            log_info_fn(
                f"{prefix} Container runtime fast-path: dropped request_container "
                "(exec already present)"
            )
        elif has_request and not has_exec:
            filtered = [
                tool
                for tool in filtered
                if extract_tool_name_fn(tool).strip().lower() != "request_container"
            ]
            filtered.insert(0, "exec_in_container")
            log_info_fn(
                f"{prefix} Container runtime fast-path: replaced request_container "
                "with exec_in_container"
            )
    return filtered


def rewrite_home_start_request_tools(
    user_text: str,
    verified_plan: Optional[Dict[str, Any]],
    suggested_tools: List[Any],
    *,
    prefix: str = "[Orchestrator]",
    is_home_container_start_query_fn: Callable[[str], bool],
    extract_tool_name_fn: Callable[[Any], str],
    log_info_fn: Callable[[str], None],
) -> List[Any]:
    if not is_home_container_start_query_fn(user_text):
        return suggested_tools

    rewritten: List[Any] = []
    seen = set()
    replaced = False
    for tool in suggested_tools or []:
        name = extract_tool_name_fn(tool).strip().lower()
        if name == "request_container":
            if "home_start" not in seen:
                rewritten.append("home_start")
                seen.add("home_start")
            replaced = True
            continue
        if not name or name in seen:
            continue
        rewritten.append(tool)
        seen.add(name)

    if not replaced and "home_start" not in seen:
        rewritten.insert(0, "home_start")
        replaced = True

    if "home_start" in seen and isinstance(verified_plan, dict):
        verified_plan["_trion_home_start_fast_path"] = True
        verified_plan["needs_chat_history"] = True
        log_info_fn(
            f"{prefix} TRION Home start fast-path: "
            f"{[extract_tool_name_fn(t) for t in rewritten]}"
        )
    return rewritten


def prioritize_home_container_tools(
    user_text: str,
    verified_plan: Dict[str, Any],
    suggested_tools: List[Any],
    *,
    prefix: str = "[Orchestrator]",
    is_home_container_info_query_fn: Callable[[str], bool],
    extract_tool_name_fn: Callable[[Any], str],
    log_info_fn: Callable[[str], None],
) -> List[Any]:
    if not isinstance(verified_plan, dict):
        return suggested_tools
    if not bool(verified_plan.get("is_fact_query", False)):
        return suggested_tools
    if not is_home_container_info_query_fn(user_text):
        return suggested_tools

    tool_names = [extract_tool_name_fn(t).lower() for t in (suggested_tools or [])]
    has_container_discovery = any(name in {"container_list", "container_inspect"} for name in tool_names)
    if has_container_discovery:
        return suggested_tools

    adjusted: List[Any] = ["container_list"]
    seen = {"container_list"}
    has_home_reader = False
    for tool in suggested_tools or []:
        name = extract_tool_name_fn(tool).strip().lower()
        if not name or name in seen:
            continue
        if name == "query_skill_knowledge":
            continue
        if name == "home_read":
            has_home_reader = True
            if isinstance(tool, dict):
                args = dict(tool.get("args", {}) or {})
                if not str(args.get("path", "")).strip():
                    args["path"] = "."
                adjusted.append({"tool": "home_read", "args": args})
            else:
                adjusted.append({"tool": "home_read", "args": {"path": "."}})
            seen.add(name)
            continue
        adjusted.append(tool)
        seen.add(name)

    if not has_home_reader:
        adjusted.append({"tool": "home_read", "args": {"path": "."}})

    log_info_fn(
        f"{prefix} Home-container routing override: "
        f"{[extract_tool_name_fn(t) for t in adjusted]}"
    )
    verified_plan["needs_chat_history"] = True
    return adjusted


def materialize_container_query_policy(
    verified_plan: Optional[Dict[str, Any]],
    *,
    strategy: str,
) -> Dict[str, Any]:
    if not isinstance(verified_plan, dict):
        return {}
    if strategy not in {
        "container_inventory",
        "container_blueprint_catalog",
        "container_state_binding",
        "container_request",
        "active_container_capability",
    }:
        return {}

    if strategy == "container_inventory":
        policy = {
            "query_class": strategy,
            "required_tools": ["container_list"],
            "truth_mode": "runtime_inventory",
        }
    elif strategy == "container_blueprint_catalog":
        policy = {
            "query_class": strategy,
            "required_tools": ["blueprint_list"],
            "truth_mode": "blueprint_catalog",
        }
    elif strategy == "container_state_binding":
        policy = {
            "query_class": strategy,
            "required_tools": ["container_inspect", "container_list"],
            "truth_mode": "session_binding",
        }
    elif strategy == "container_request":
        policy = {
            "query_class": strategy,
            "required_tools": ["request_container", "home_start"],
            "truth_mode": "request_flow",
        }
    else:
        policy = {
            "query_class": strategy,
            "required_tools": ["container_inspect"],
            "truth_mode": "active_container_capability",
        }
    verified_plan["_container_query_policy"] = policy
    return policy


def prioritize_active_container_capability_tools(
    user_text: str,
    verified_plan: Dict[str, Any],
    suggested_tools: List[Any],
    *,
    conversation_id: str = "",
    force: bool = False,
    prefix: str = "[Orchestrator]",
    is_active_container_capability_query_fn: Callable[[str], bool],
    get_recent_container_state_fn: Callable[[str], Optional[Dict[str, Any]]],
    container_state_has_active_target_fn: Callable[[Optional[Dict[str, Any]]], bool],
    extract_tool_name_fn: Callable[[Any], str],
    log_info_fn: Callable[[str], None],
) -> List[Any]:
    if not isinstance(verified_plan, dict):
        return suggested_tools
    if not bool(verified_plan.get("is_fact_query", False)):
        return suggested_tools
    if not force and not is_active_container_capability_query_fn(user_text):
        return suggested_tools

    container_state = get_recent_container_state_fn(conversation_id) if conversation_id else None
    if not container_state_has_active_target_fn(container_state):
        return suggested_tools

    adjusted: List[Any] = ["container_inspect"]
    seen = {"container_inspect"}
    for tool in suggested_tools or []:
        name = extract_tool_name_fn(tool).strip().lower()
        if not name or name in seen:
            continue
        if name in {"exec_in_container", "container_stats", "container_list", "query_skill_knowledge"}:
            continue
        adjusted.append(tool)
        seen.add(name)

    log_info_fn(
        f"{prefix} Active-container capability override: "
        f"{[extract_tool_name_fn(t) for t in adjusted]}"
    )
    verified_plan["needs_chat_history"] = True
    return adjusted


def apply_container_query_policy(
    user_text: str,
    verified_plan: Dict[str, Any],
    suggested_tools: List[Any],
    *,
    conversation_id: str = "",
    prefix: str = "[Orchestrator]",
    get_effective_resolution_strategy_fn: Callable[[Optional[Dict[str, Any]]], str],
    is_active_container_capability_query_fn: Callable[[str], bool],
    is_container_state_binding_query_fn: Callable[[str], bool],
    is_container_blueprint_catalog_query_fn: Callable[[str], bool],
    is_container_request_query_fn: Callable[[str], bool],
    is_container_inventory_query_fn: Callable[[str], bool],
    materialize_container_query_policy_fn: Callable[[Optional[Dict[str, Any]], str], Dict[str, Any]],
    get_recent_container_state_fn: Callable[[str], Optional[Dict[str, Any]]],
    container_state_has_active_target_fn: Callable[[Optional[Dict[str, Any]]], bool],
    is_home_container_start_query_fn: Callable[[str], bool],
    extract_tool_name_fn: Callable[[Any], str],
    tool_name_list_fn: Callable[[Optional[List[Any]]], List[str]],
    log_info_fn: Callable[[str], None],
) -> List[Any]:
    if not isinstance(verified_plan, dict):
        return suggested_tools

    strategy = get_effective_resolution_strategy_fn(verified_plan)
    if not strategy:
        if is_active_container_capability_query_fn(user_text):
            strategy = "active_container_capability"
        elif is_container_state_binding_query_fn(user_text):
            strategy = "container_state_binding"
        elif is_container_blueprint_catalog_query_fn(user_text):
            strategy = "container_blueprint_catalog"
        elif is_container_request_query_fn(user_text):
            strategy = "container_request"
        elif is_container_inventory_query_fn(user_text):
            strategy = "container_inventory"
    if strategy not in {
        "container_inventory",
        "container_blueprint_catalog",
        "container_state_binding",
        "container_request",
        "active_container_capability",
    }:
        return suggested_tools

    policy = materialize_container_query_policy_fn(verified_plan, strategy)
    container_state = get_recent_container_state_fn(conversation_id) if conversation_id else None
    has_active_target = container_state_has_active_target_fn(container_state)

    if strategy == "container_inventory":
        adjusted = ["container_list"]
    elif strategy == "container_blueprint_catalog":
        adjusted = ["blueprint_list"]
    elif strategy == "container_request":
        if is_home_container_start_query_fn(user_text):
            adjusted = ["home_start"]
            verified_plan["_trion_home_start_fast_path"] = True
            verified_plan["needs_chat_history"] = True
            if policy:
                policy["truth_mode"] = "home_start_reuse"
        else:
            adjusted = ["request_container"]
    elif strategy == "container_state_binding":
        adjusted = ["container_inspect"] if has_active_target else ["container_list"]
        verified_plan["needs_chat_history"] = True
    else:
        adjusted = suggested_tools

    if strategy != "active_container_capability":
        adjusted_names = [extract_tool_name_fn(t) for t in adjusted]
        if tool_name_list_fn(suggested_tools) != adjusted_names:
            log_info_fn(
                f"{prefix} Container query policy override: strategy={strategy} "
                f"tools={adjusted_names}"
            )
        if policy:
            policy["selected_tools"] = adjusted_names
        return adjusted

    if policy:
        policy["selected_tools"] = tool_name_list_fn(suggested_tools)
    return suggested_tools
