"""Main verification flow for ControlLayer."""

from __future__ import annotations

import asyncio
import json
from typing import Any

import httpx


async def verify_flow(
    user_text: str,
    thinking_plan: dict[str, Any],
    *,
    retrieved_memory: str = "",
    response_mode: str = "interactive",
    light_cim,
    ollama_base: str,
    control_prompt: str,
    get_control_provider_fn,
    resolve_role_provider_fn,
    resolve_role_endpoint_fn,
    complete_prompt_fn,
    safe_parse_json_fn,
    make_hard_block_verification_fn,
    cim_policy_available: bool,
    process_cim_policy_fn,
    run_cim_policy_engine_fn,
    user_text_has_malicious_intent_fn,
    get_available_skills_async_fn,
    is_skill_creation_sensitive_fn,
    extract_requested_skill_name_fn,
    is_light_cim_hard_denial_fn,
    warning_list_fn,
    normalize_response_mode_fn,
    resolve_verify_timeout_s_fn,
    resolve_model_fn,
    build_control_prompt_payload_fn,
    resolve_control_endpoint_override_fn,
    default_verification_fn,
    stabilize_verification_result_fn,
    log_info_fn,
    log_warning_fn,
    log_error_fn,
) -> dict[str, Any]:
    """Run the full control verification flow."""
    sequential_result = thinking_plan.get("_sequential_result")
    # FIX: Removed - Bridge handles Sequential Thinking
    # if not sequential_result:
    # sequential_result = await self._check_sequential_thinking(user_text, thinking_plan)
    if sequential_result:
        log_info_fn(
            f"[ControlLayer] Sequential completed with {len(sequential_result.get('steps', []))} steps"
        )
        thinking_plan["_sequential_result"] = sequential_result

    if user_text_has_malicious_intent_fn(user_text):
        return make_hard_block_verification_fn(
            reason_code="malicious_intent",
            warnings=["Dangerous keyword detected: blocked by deterministic policy guard"],
        )

    if bool((thinking_plan or {}).get("_hardware_gate_triggered")):
        hardware_msg = str((thinking_plan or {}).get("_hardware_gate_warning") or "").strip()
        return make_hard_block_verification_fn(
            reason_code="hardware_self_protection",
            warnings=[hardware_msg or "Hardware self-protection gate triggered."],
            reason="hardware_self_protection",
        )

    log_info_fn(f"[ControlLayer-DEBUG] CIM_POLICY_AVAILABLE={cim_policy_available}")
    cim_verification = await run_cim_policy_engine_fn(
        user_text,
        thinking_plan,
        cim_policy_available=cim_policy_available,
        process_cim_policy_fn=process_cim_policy_fn,
        get_available_skills_async_fn=get_available_skills_async_fn,
        user_text_has_malicious_intent_fn=user_text_has_malicious_intent_fn,
        is_skill_creation_sensitive_fn=is_skill_creation_sensitive_fn,
        extract_requested_skill_name_fn=extract_requested_skill_name_fn,
        make_hard_block_verification_fn=make_hard_block_verification_fn,
        log_info_fn=log_info_fn,
        log_warning_fn=log_warning_fn,
        log_error_fn=log_error_fn,
    )
    if cim_verification is not None:
        return cim_verification

    soft_light_cim_warnings: list[str] = []
    try:
        cim_result = light_cim.validate_basic(
            intent=thinking_plan.get("intent", ""),
            hallucination_risk=thinking_plan.get("hallucination_risk", "low"),
            user_text=user_text,
            thinking_plan=thinking_plan,
        )
        log_info_fn(f"[LightCIM] safe={cim_result['safe']}, confidence={cim_result['confidence']:.2f}")
        if not cim_result["safe"]:
            if is_light_cim_hard_denial_fn(cim_result):
                out = make_hard_block_verification_fn(
                    reason_code="pii",
                    warnings=cim_result["warnings"],
                    reason="pii",
                )
                out["_light_cim"] = cim_result
                return out
            soft_light_cim_warnings = warning_list_fn(cim_result.get("warnings", []))
            if soft_light_cim_warnings:
                log_warning_fn(
                    "[ControlLayer] LightCIM soft warning pass-through: "
                    f"{soft_light_cim_warnings}"
                )
    except Exception as exc:
        log_error_fn(f"[LightCIM] Error: {exc}")

    response_mode_norm = normalize_response_mode_fn(response_mode)
    verify_timeout_s = resolve_verify_timeout_s_fn(response_mode_norm)
    control_model = resolve_model_fn(response_mode_norm)
    payload = build_control_prompt_payload_fn(user_text, thinking_plan, retrieved_memory)
    prompt = f"""{control_prompt}

CONTROL_INPUT:
{json.dumps(payload, ensure_ascii=False)}

Deine Bewertung (nur JSON):"""
    log_info_fn(
        "[ControlLayer] verify_prompt "
        f"chars={len(prompt)} "
        f"user_chars={len(payload.get('user_request', ''))} "
        f"plan_chars={len(payload.get('thinking_plan_compact', ''))} "
        f"memory_chars={len(payload.get('memory_excerpt', ''))}"
    )

    provider = resolve_role_provider_fn("control", default=get_control_provider_fn())
    try:
        endpoint_source = "cloud"
        endpoint = ollama_base
        if provider == "ollama":
            route = resolve_role_endpoint_fn("control", default_endpoint=ollama_base)
            endpoint_source = "routing"
            log_info_fn(
                f"[Routing] role=control provider=ollama requested_target={route['requested_target']} "
                f"effective_target={route['effective_target'] or 'none'} "
                f"fallback={bool(route['fallback_reason'])} "
                f"fallback_reason={route['fallback_reason'] or 'none'} "
                f"endpoint_source={route['endpoint_source']}"
            )
            if route["hard_error"]:
                log_error_fn(
                    f"[Routing] role=control hard_error=true code={route['error_code']} "
                    f"requested_target={route['requested_target']}"
                )
                return default_verification_fn(thinking_plan)
            endpoint = route["endpoint"] or ollama_base
            endpoint_override = resolve_control_endpoint_override_fn(response_mode_norm)
            if endpoint_override:
                endpoint = endpoint_override
                endpoint_source = "control_override"
        else:
            log_info_fn(f"[Routing] role=control provider={provider} endpoint=cloud")

        log_info_fn(
            "[ControlLayer] verify_runtime "
            f"mode={response_mode_norm} provider={provider} model={control_model} "
            f"timeout_s={verify_timeout_s:.1f} endpoint={endpoint} "
            f"endpoint_source={endpoint_source}"
        )

        content = await complete_prompt_fn(
            provider=provider,
            model=control_model,
            prompt=prompt,
            timeout_s=verify_timeout_s,
            ollama_endpoint=endpoint,
            json_mode=True,
        )
        if not content:
            fallback = default_verification_fn(thinking_plan)
            if soft_light_cim_warnings:
                warnings = warning_list_fn(fallback.get("warnings", []))
                warnings.extend(soft_light_cim_warnings)
                fallback["warnings"] = warnings
            return fallback
        parsed = safe_parse_json_fn(
            content,
            default=default_verification_fn(thinking_plan),
            context="ControlLayer",
        )
        if soft_light_cim_warnings:
            warnings = warning_list_fn(parsed.get("warnings", []))
            warnings.extend(soft_light_cim_warnings)
            parsed["warnings"] = warnings
        return stabilize_verification_result_fn(parsed, thinking_plan, user_text=user_text)
    except (httpx.TimeoutException, asyncio.TimeoutError) as exc:
        msg = (
            "Control verification timeout (504): "
            f"provider={provider if 'provider' in locals() else 'unknown'} "
            f"model={control_model if 'control_model' in locals() else resolve_model_fn(response_mode_norm)} "
            f"endpoint={endpoint if 'endpoint' in locals() else ollama_base} "
            f"timeout_s={verify_timeout_s if 'verify_timeout_s' in locals() else 30.0}"
        )
        log_error_fn(f"[ControlLayer] {msg} err={type(exc).__name__}")
        fallback = default_verification_fn(thinking_plan)
        warnings = list(fallback.get("warnings", []))
        warnings.append(msg)
        warnings.extend(soft_light_cim_warnings)
        fallback["warnings"] = warnings
        fallback["_error"] = {"code": 504, "type": "control_timeout", "message": msg}
        return fallback
    except Exception as exc:
        msg = f"Control verification error: {type(exc).__name__}: {exc}"
        log_error_fn(f"[ControlLayer] {msg}")
        fallback = default_verification_fn(thinking_plan)
        warnings = list(fallback.get("warnings", []))
        warnings.append(msg)
        warnings.extend(soft_light_cim_warnings)
        fallback["warnings"] = warnings
        fallback["_error"] = {"code": 500, "type": "control_error", "message": msg}
        return fallback
