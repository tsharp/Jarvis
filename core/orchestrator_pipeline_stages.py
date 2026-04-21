"""
Shared pipeline stages for Sync- and Stream-Flow.

These are pure-computation stages with no yield calls.
Both orchestrator_sync_flow_utils and orchestrator_stream_flow_utils call these.

Stages:
  run_pre_control_gates()    — Skill-Dedup, Container-Candidate, Hardware-Gate
  run_plan_finalization()    — Post-thinking coercion, response mode, temporal context
  run_tool_selection_stage() — Tool selection, short-input bypass, budget/domain signals
  prepare_output_invocation() — Model resolution, memory guard flag, time budget (pre-output)
"""

from typing import Any, Dict, List, Optional, Tuple


def run_pre_control_gates(
    orch: Any,
    user_text: str,
    thinking_plan: Dict,
    request: Any,
    log_info_fn: Any,
    log_warn_fn: Any,
) -> Tuple[Optional[Dict], Optional[str]]:
    """
    Runs the three pre-control gates in order, mutating thinking_plan in-place.

    Returns:
        skill_gate_result  — None | {"blocked": True, "reason": str}
                                  | {"routed": True, "skill_name": str, "score": float}
        hardware_gate_msg  — None | str  (non-empty means gate triggered)
    """
    skill_gate_result: Optional[Dict] = None

    # ── Skill Dedup Gate ──────────────────────────────────────────
    if "autonomous_skill_task" in thinking_plan.get("suggested_tools", []):
        if not orch._contains_explicit_skill_intent(user_text):
            thinking_plan["_skill_gate_blocked"] = True
            thinking_plan["_skill_gate_reason"] = "no_explicit_skill_intent"
            thinking_plan["suggested_tools"] = [
                t for t in thinking_plan.get("suggested_tools", [])
                if t not in {"autonomous_skill_task", "run_skill", "create_skill"}
            ]
            log_info_fn("[Pipeline] Skill gate blocked — reason=no_explicit_skill_intent")
            skill_gate_result = {"blocked": True, "reason": "no_explicit_skill_intent"}
        else:
            skill_decision = orch._route_skill_request(user_text, thinking_plan)
            if skill_decision and skill_decision.get("blocked"):
                thinking_plan["_skill_gate_blocked"] = True
                thinking_plan["_skill_gate_reason"] = skill_decision.get("reason", "skill_router_unavailable")
                thinking_plan["suggested_tools"] = [
                    t for t in thinking_plan.get("suggested_tools", [])
                    if t not in {"autonomous_skill_task", "run_skill", "create_skill"}
                ]
                log_warn_fn(
                    f"[Pipeline] Skill gate blocked — reason={thinking_plan['_skill_gate_reason']}"
                )
                skill_gate_result = {"blocked": True, "reason": thinking_plan["_skill_gate_reason"]}
            elif skill_decision:
                thinking_plan["suggested_tools"] = ["run_skill"]
                thinking_plan["_skill_router"] = skill_decision
                log_info_fn(
                    f"[Pipeline] Skill Dedup Gate: '{skill_decision['skill_name']}' "
                    f"(score={skill_decision['score']:.2f}) — run_skill statt create"
                )
                skill_gate_result = {
                    "routed": True,
                    "skill_name": skill_decision["skill_name"],
                    "score": skill_decision["score"],
                }

    # ── TRION Home Start Fast-Path ───────────────────────────────
    thinking_plan["suggested_tools"] = orch._rewrite_home_start_request_tools(
        user_text,
        thinking_plan,
        list(thinking_plan.get("suggested_tools") or []),
        prefix="[Pipeline]",
    )

    # ── Container Candidate Evidence + Blueprint Gate ────────────
    if "request_container" in thinking_plan.get("suggested_tools", []):
        orch._prepare_container_candidate_evidence(
            user_text,
            thinking_plan,
            chat_history=list(getattr(request, "messages", None) or []),
        )
        # Apply blueprint gate flags from resolution (mirrors old inline gate logic)
        _res = thinking_plan.get("_container_resolution") or {}
        _dec = _res.get("decision", "no_blueprint")
        if _dec == "resolver_error":
            thinking_plan["_blueprint_gate_blocked"] = True
            thinking_plan["_blueprint_gate_reason"] = _res.get("reason", "blueprint_router_unavailable")
            thinking_plan["_blueprint_recheck_required"] = False
            thinking_plan["_blueprint_recheck_reason"] = ""
            log_warn_fn(
                f"[Pipeline] Blueprint gate blocked — reason={thinking_plan['_blueprint_gate_reason']}"
            )
        elif _dec == "use_blueprint":
            thinking_plan["_blueprint_gate_blocked"] = False
            thinking_plan["_blueprint_gate_reason"] = ""
            thinking_plan["_blueprint_recheck_required"] = False
            thinking_plan["_blueprint_recheck_reason"] = ""
            thinking_plan["_blueprint_router"] = {
                "blueprint_id": _res.get("blueprint_id", ""),
                "score": _res.get("score", 0.0),
                "reason": _res.get("reason", ""),
                "candidates": _res.get("candidates", []),
            }
            log_info_fn(
                f"[Pipeline] Blueprint auto-routed: '{_res.get('blueprint_id')}' "
                f"(score={_res.get('score', 0.0):.2f})"
            )
        elif _dec == "suggest_blueprint":
            thinking_plan["_blueprint_gate_blocked"] = False
            thinking_plan["_blueprint_gate_reason"] = ""
            thinking_plan["_blueprint_recheck_required"] = True
            thinking_plan["_blueprint_recheck_reason"] = "container_blueprint_recheck_required"
            thinking_plan["_blueprint_suggest"] = {
                "blueprint_id": _res.get("blueprint_id", ""),
                "score": _res.get("score", 0.0),
                "suggest": True,
                "candidates": _res.get("candidates", []),
            }
            _cur_tools = list(thinking_plan.get("suggested_tools") or [])
            if "blueprint_list" not in _cur_tools:
                thinking_plan["suggested_tools"] = ["blueprint_list"] + _cur_tools
            log_info_fn("[Pipeline] Blueprint suggest: Recheck via blueprint_list vor User-Rückfrage")
        else:  # no_blueprint or unknown
            thinking_plan["_blueprint_gate_blocked"] = False
            thinking_plan["_blueprint_gate_reason"] = ""
            thinking_plan["_blueprint_recheck_required"] = True
            thinking_plan["_blueprint_recheck_reason"] = "container_blueprint_discovery_required"
            thinking_plan["_blueprint_no_match"] = True
            _cur_tools = list(thinking_plan.get("suggested_tools") or [])
            if "blueprint_list" not in _cur_tools:
                thinking_plan["suggested_tools"] = ["blueprint_list"] + _cur_tools
            log_info_fn("[Pipeline] Blueprint: kein Match — blueprint_list als Discovery-Schritt injiziert")

    # ── Hardware Gate Early ───────────────────────────────────────
    hardware_gate_msg: Optional[str] = None
    _early_gate_msg = orch._check_hardware_gate_early(user_text, thinking_plan)
    if _early_gate_msg:
        log_info_fn("[Pipeline] Early Hardware Gate signal — delegated to Control hard-block authority")
        thinking_plan["_hardware_gate_triggered"] = True
        thinking_plan["_hardware_gate_warning"] = str(_early_gate_msg)[:1200]
        hardware_gate_msg = str(_early_gate_msg)

    return skill_gate_result, hardware_gate_msg


def run_plan_finalization(
    orch: Any,
    user_text: str,
    request: Any,
    thinking_plan: Dict,
    selected_tools: List[str],
    query_budget_signal: Dict,
    domain_route_signal: Dict,
    forced_response_mode: Optional[str],
    conversation_id: str,
    log_info_fn: Any,
) -> Tuple[Dict, str]:
    """
    Post-thinking plan coercion, response mode resolution and temporal context.

    Mutates thinking_plan (via orch helpers) and returns the finalized plan
    and the resolved response_mode string.
    """
    thinking_plan = orch._coerce_thinking_plan_schema(
        thinking_plan,
        user_text=user_text,
    )
    thinking_plan = orch._apply_query_budget_to_plan(
        thinking_plan,
        query_budget_signal,
        user_text=user_text,
    )
    thinking_plan = orch._apply_domain_route_to_plan(
        thinking_plan,
        domain_route_signal,
        user_text=user_text,
    )
    thinking_plan = orch._resolve_precontrol_policy_conflicts(
        user_text,
        thinking_plan,
        conversation_id=conversation_id,
    )

    # Short-Input Plan Bypass
    if (
        not thinking_plan.get("suggested_tools")
        and selected_tools
        and len(user_text.split()) < 5
    ):
        thinking_plan["suggested_tools"] = list(selected_tools)
        log_info_fn(
            f"[Pipeline] Short-Input Plan Bypass: suggested_tools injected "
            f"from selected_tools={selected_tools}"
        )

    response_mode = orch._apply_response_mode_policy(
        user_text,
        thinking_plan,
        forced_mode=forced_response_mode,
    )
    log_info_fn(
        "[Pipeline] dialogue_controls "
        f"act={thinking_plan.get('dialogue_act')} "
        f"tone={thinking_plan.get('response_tone')} "
        f"len={thinking_plan.get('response_length_hint')} "
        f"conf={thinking_plan.get('tone_confidence')}"
    )
    orch._apply_temporal_context_fallback(
        user_text,
        thinking_plan,
        chat_history=getattr(request, "messages", None) or [],
    )

    return thinking_plan, response_mode


async def run_tool_selection_stage(
    orch: Any,
    user_text: str,
    request: Any,
    forced_response_mode: Optional[str],
    tone_signal: Any,
    log_info_fn: Any,
) -> Tuple[List[str], Dict, Dict, str]:
    """
    Layer 0: Tool selection, short-input bypass, budget and domain signals.

    Returns:
        selected_tools        — list of tool names
        query_budget_signal   — dict
        domain_route_signal   — dict
        last_assistant_msg    — str (used downstream for context enrichment)
    """
    # Extract last assistant message for context-aware selection
    last_assistant_msg = ""
    for _msg in reversed(list(getattr(request, "messages", None) or [])):
        if isinstance(_msg, dict) and _msg.get("role") == "assistant":
            last_assistant_msg = str(_msg.get("content", ""))
            break

    selected_tools = await orch.tool_selector.select_tools(
        user_text, context_summary=last_assistant_msg
    )
    selected_tools = orch._filter_tool_selector_candidates(
        selected_tools, user_text, forced_mode=forced_response_mode
    )

    # Short-Input Bypass: inject follow-up tools when semantic search returns empty
    if not selected_tools and len(user_text.split()) < 5:
        if last_assistant_msg:
            selected_tools = ["request_container", "run_skill"]
        else:
            selected_tools = ["request_container", "run_skill", "home_write"]
        log_info_fn("[Pipeline] Short-Input Bypass: core follow-up tools injected")

    query_budget_signal = await orch._classify_query_budget_signal(
        user_text,
        selected_tools=selected_tools,
        tone_signal=tone_signal,
    )
    domain_route_signal = await orch._classify_domain_signal(
        user_text,
        selected_tools=selected_tools,
    )

    return selected_tools, query_budget_signal, domain_route_signal, last_assistant_msg


def prepare_output_invocation(
    orch: Any,
    request: Any,
    verified_plan: Dict,
    mem_res: Any,
    response_mode: str,
) -> Tuple[str, bool]:
    """
    Common pre-output setup for both Sync- and Stream-Flow.

    Resolves the output model, sets _output_model_resolution and _output_time_budget_s
    on verified_plan, and extracts the memory-guard flag from MemoryResolution.

    Returns:
        resolved_output_model        — model handle to pass to output.generate / generate_stream
        memory_required_but_missing  — guard flag from mem_res.required_missing
    """
    # Guard flag — computed once upstream in build_effective_context(), do not recompute.
    memory_required_but_missing: bool = getattr(mem_res, "required_missing", False)

    # Model resolution
    resolved_output_model, model_resolution = orch._resolve_runtime_output_model(request.model)
    verified_plan["_output_model_resolution"] = model_resolution

    # Output time budget — keeps Sync and Stream consistent
    try:
        from config import get_output_timeout_interactive_s, get_output_timeout_deep_s
        verified_plan["_output_time_budget_s"] = (
            get_output_timeout_deep_s()
            if response_mode == "deep"
            else get_output_timeout_interactive_s()
        )
    except Exception:
        pass

    return resolved_output_model, memory_required_but_missing
