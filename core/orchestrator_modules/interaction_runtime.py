from __future__ import annotations

import json
import os
import re
import urllib.request
from typing import Any, Callable, Dict, List, Optional, Tuple


def recover_home_read_directory_with_fast_lane(
    dir_path: str,
    *,
    max_files: int = 5,
    fast_lane_executor_cls: Any,
) -> Tuple[bool, str]:
    path = str(dir_path or ".").strip() or "."
    try:
        fl = fast_lane_executor_cls()
        sub_result = fl.execute("home_list", {"path": path})
        sub_items = sub_result.content if hasattr(sub_result, "content") else sub_result
        if not isinstance(sub_items, list):
            return False, ""

        files_read = 0
        parts: List[str] = [
            f"home_read recovery for directory '{path}'",
            "listing: " + json.dumps(sub_items, ensure_ascii=False),
        ]
        for sub_item in sub_items:
            if files_read >= max_files:
                break
            item = str(sub_item or "").strip()
            if not item or item.endswith("/"):
                continue
            fp = item if path in (".", "") else f"{path}/{item}"
            try:
                fc = fl.execute("home_read", {"path": fp})
                fc_content = fc.content if hasattr(fc, "content") else fc
                text = str(fc_content or "").strip()
                if not text:
                    continue
                parts.append(f"file[{fp}]: {text}")
                files_read += 1
            except Exception:
                continue

        if files_read <= 0:
            return True, "\n".join(parts)
        parts.append(f"files_read: {files_read}")
        return True, "\n".join(parts)
    except Exception:
        return False, ""


def sanitize_skill_name_candidate(raw_name: Any) -> str:
    candidate = str(raw_name or "").strip().strip("`\"'.,:;!?()[]{}")
    if not candidate:
        return ""
    candidate = candidate.replace("-", "_")
    candidate = re.sub(r"[^A-Za-z0-9_]", "_", candidate)
    candidate = re.sub(r"_+", "_", candidate).strip("_")
    if not re.fullmatch(r"[A-Za-z][A-Za-z0-9_]{1,63}", candidate):
        return ""
    return candidate.lower()


def is_explicit_deep_request(user_text: str) -> bool:
    text = str(user_text or "").lower()
    deep_markers = (
        "/deep",
        "deep analysis",
        "tiefenanalyse",
        "ausfuehrlich",
        "ausführlich",
        "sehr detailliert",
        "vollständige analyse",
        "vollstaendige analyse",
    )
    return any(marker in text for marker in deep_markers)


def is_explicit_think_request(user_text: str) -> bool:
    text = str(user_text or "").lower()
    think_markers = (
        "schritt für schritt",
        "schritt fuer schritt",
        "step by step",
        "denk schrittweise",
        "denke schrittweise",
        "reason step by step",
        "chain of thought",
        "zeige dein thinking",
    )
    return any(marker in text for marker in think_markers)


def extract_tool_name(tool_spec: Any) -> str:
    if isinstance(tool_spec, dict):
        return str(tool_spec.get("tool") or tool_spec.get("name") or "").strip()
    return str(tool_spec or "").strip()


def is_home_container_start_query(
    user_text: str,
    *,
    home_container_query_markers: List[str],
    home_container_start_markers: List[str],
) -> bool:
    text = str(user_text or "").strip().lower()
    if not text:
        return False
    has_home_marker = any(marker in text for marker in home_container_query_markers)
    if not has_home_marker:
        return False
    return any(marker in text for marker in home_container_start_markers)


def is_home_container_info_query(
    user_text: str,
    *,
    home_container_query_markers: List[str],
    home_container_purpose_markers: List[str],
    is_home_container_start_query_fn: Callable[[str], bool],
) -> bool:
    text = str(user_text or "").strip().lower()
    if not text:
        return False
    if is_home_container_start_query_fn(text):
        return False
    has_home_marker = any(marker in text for marker in home_container_query_markers)
    if not has_home_marker:
        return False
    return any(marker in text for marker in home_container_purpose_markers) or "container" in text


def extract_requested_skill_name(
    user_text: str,
    *,
    sanitize_skill_name_candidate_fn: Callable[[Any], str],
) -> str:
    text = str(user_text or "").strip()
    if not text:
        return ""

    patterns = [
        r"(?i)\brun_skill\s+([A-Za-z][A-Za-z0-9_-]{2,63})\b",
        r"(?i)\b(?:führe|fuehre|run|execute|starte|start)\s+(?:den\s+|die\s+|das\s+)?skill\s+([A-Za-z][A-Za-z0-9_-]{2,63})\b",
        r"(?i)\bskill\s+([A-Za-z][A-Za-z0-9_-]{2,63})\s+(?:aus|ausführen|ausfuehren|run|starten|execute)\b",
        r"(?i)\b(?:skill|funktion)\s+(?:namens|name|named|called)\s+[`\"']?([A-Za-z][A-Za-z0-9_-]{2,63})[`\"']?",
    ]
    stopwords = {
        "skill",
        "run_skill",
        "ausfuehren",
        "ausführen",
        "execute",
        "run",
        "start",
        "starte",
        "fuehre",
        "führe",
        "bitte",
    }
    for pattern in patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE | re.UNICODE)
        if not match:
            continue
        candidate = sanitize_skill_name_candidate_fn(match.group(1))
        if candidate and candidate not in stopwords:
            return candidate
    return ""


def filter_think_tools(
    tools: List[Any],
    *,
    user_text: str,
    thinking_plan: Optional[Dict[str, Any]],
    source: str,
    is_explicit_think_request_fn: Callable[[str], bool],
    extract_tool_name_fn: Callable[[Any], str],
    log_info_fn: Callable[[str], None],
) -> List[Any]:
    if not tools:
        return tools

    plan = thinking_plan or {}
    allow_think = False
    reason = "not_needed"

    if is_explicit_think_request_fn(user_text):
        allow_think = True
        reason = "explicit_user_request"
    elif str(plan.get("_response_mode", "interactive")) == "deep":
        allow_think = True
        reason = "deep_mode"
    elif plan.get("_sequential_deferred"):
        allow_think = False
        reason = "sequential_deferred"
    elif plan.get("needs_sequential_thinking") or plan.get("sequential_thinking_required"):
        allow_think = True
        reason = "sequential_required"

    if allow_think:
        return tools

    filtered = []
    dropped = 0
    for tool in tools:
        if extract_tool_name_fn(tool) in {"think", "think_simple"}:
            dropped += 1
            continue
        filtered.append(tool)

    if dropped:
        log_info_fn(
            f"[Orchestrator] Filtered think tool(s) source={source} "
            f"dropped={dropped} reason={reason}"
        )
    return filtered


def filter_tool_selector_candidates(
    selected_tools: Optional[List[Any]],
    *,
    user_text: str,
    forced_mode: str = "",
    is_explicit_deep_request_fn: Callable[[str], bool],
    filter_think_tools_fn: Callable[..., List[Any]],
) -> Optional[List[Any]]:
    if not selected_tools:
        return selected_tools
    plan_hint = {
        "_response_mode": "deep"
        if (forced_mode == "deep" or is_explicit_deep_request_fn(user_text))
        else "interactive"
    }
    return filter_think_tools_fn(
        list(selected_tools),
        user_text=user_text,
        thinking_plan=plan_hint,
        source="tool_selector",
    )


def requested_response_mode(request: Any) -> str:
    raw = request.raw_request if isinstance(getattr(request, "raw_request", None), dict) else {}
    mode = str(raw.get("response_mode", "")).strip().lower()
    return mode if mode in {"interactive", "deep"} else ""


def resolve_runtime_output_model(
    requested_model: str,
    *,
    ollama_base: str,
    get_output_model_fn: Callable[[], str],
    get_output_provider_fn: Callable[[], str],
    resolve_role_endpoint_fn: Callable[..., Dict[str, Any]],
    resolve_runtime_chat_model_fn: Callable[..., Dict[str, Any]],
    log_info_fn: Callable[[str], None],
    log_warn_fn: Callable[[str], None],
) -> Tuple[str, Dict[str, Any]]:
    requested = str(requested_model or "").strip()
    fallback = str(get_output_model_fn() or "").strip()
    provider = str(get_output_provider_fn() or "ollama").strip().lower()

    if provider != "ollama":
        resolved = requested or fallback
        resolution = {
            "requested_model": requested,
            "resolved_model": resolved,
            "fallback_model": fallback,
            "endpoint": "cloud",
            "tags_ok": False,
            "available_count": 0,
            "used_fallback": bool(resolved and resolved != requested),
            "reason": "provider_passthrough_non_ollama",
            "provider": provider,
        }
        if resolved != requested:
            log_warn_fn(
                f"[ModelResolver] output model fallback requested='{requested or '<empty>'}' "
                f"resolved='{resolved or '<empty>'}' reason={resolution['reason']} provider={provider}"
            )
        else:
            log_info_fn(
                f"[ModelResolver] output model accepted requested='{requested or '<empty>'}' "
                f"reason={resolution['reason']} provider={provider}"
            )
        return resolved, resolution

    try:
        route = resolve_role_endpoint_fn("output", default_endpoint=ollama_base)
        endpoint = str(route.get("endpoint") or ollama_base or "").strip()
    except Exception as exc:
        log_warn_fn(f"[ModelResolver] role endpoint resolution failed: {exc}")
        endpoint = str(ollama_base or "").strip()

    resolution = resolve_runtime_chat_model_fn(
        requested_model=requested,
        endpoint=endpoint,
        fallback_model=fallback,
    )
    resolved = str(resolution.get("resolved_model") or "").strip()
    if not resolved:
        resolved = fallback or requested
        resolution["resolved_model"] = resolved
        resolution["reason"] = "resolver_empty_fallback_applied"

    if resolved != requested:
        log_warn_fn(
            f"[ModelResolver] output model adjusted requested='{requested or '<empty>'}' "
            f"resolved='{resolved or '<empty>'}' reason={resolution.get('reason')} "
            f"endpoint={resolution.get('endpoint') or 'unknown'} "
            f"available_count={resolution.get('available_count', 0)}"
        )
    else:
        log_info_fn(
            f"[ModelResolver] output model accepted requested='{requested or '<empty>'}' "
            f"endpoint={resolution.get('endpoint') or 'unknown'} "
            f"available_count={resolution.get('available_count', 0)}"
        )
    return resolved, resolution


def apply_response_mode_policy(
    user_text: str,
    thinking_plan: Dict[str, Any],
    *,
    forced_mode: str = "",
    get_default_response_mode_fn: Callable[[], str],
    get_response_mode_sequential_threshold_fn: Callable[[], int],
    is_explicit_deep_request_fn: Callable[[str], bool],
    filter_think_tools_fn: Callable[..., List[Any]],
    log_info_fn: Callable[[str], None],
) -> str:
    if forced_mode in {"interactive", "deep"}:
        mode = forced_mode
    else:
        mode = "deep" if is_explicit_deep_request_fn(user_text) else get_default_response_mode_fn()
    mode = "deep" if mode == "deep" else "interactive"
    thinking_plan["_response_mode"] = mode

    if mode == "interactive":
        threshold = get_response_mode_sequential_threshold_fn()
        complexity = int(thinking_plan.get("sequential_complexity", 0) or 0)
        needs_seq = bool(
            thinking_plan.get("needs_sequential_thinking")
            or thinking_plan.get("sequential_thinking_required")
        )
        if needs_seq and complexity >= threshold:
            thinking_plan["needs_sequential_thinking"] = False
            thinking_plan["sequential_thinking_required"] = False
            thinking_plan["_sequential_deferred"] = True
            thinking_plan["_sequential_deferred_reason"] = (
                f"interactive_mode_complexity_{complexity}_threshold_{threshold}"
            )
            log_info_fn(
                f"[Orchestrator] Sequential deferred (interactive mode): "
                f"complexity={complexity} threshold={threshold}"
            )

    if thinking_plan.get("suggested_tools"):
        thinking_plan["suggested_tools"] = filter_think_tools_fn(
            list(thinking_plan.get("suggested_tools", [])),
            user_text=user_text,
            thinking_plan=thinking_plan,
            source=f"response_mode:{mode}",
        )
    return mode


def detect_tools_by_keyword(
    user_text: str,
    *,
    is_home_container_info_query_fn: Callable[[str], bool],
    is_home_container_start_query_fn: Callable[[str], bool],
    is_active_container_capability_query_fn: Callable[[str], bool],
    is_container_state_binding_query_fn: Callable[[str], bool],
    is_container_blueprint_catalog_query_fn: Callable[[str], bool],
    is_container_inventory_query_fn: Callable[[str], bool],
    is_container_request_query_fn: Callable[[str], bool],
) -> List[Any]:
    user_lower = user_text.lower()
    if any(kw in user_lower for kw in [
        "festplatte", "festplatten", "laufwerk", "laufwerke",
        "storage", "disk", "disks", "mount", "mounts", "speicherplatz",
    ]):
        if any(kw in user_lower for kw in ["summary", "übersicht", "uebersicht", "kapazität", "kapazitaet", "frei", "belegt"]):
            return ["storage_get_summary"]
        if any(kw in user_lower for kw in ["mount", "mounts", "eingehängt", "eingehaengt"]):
            return ["storage_list_mounts"]
        if any(kw in user_lower for kw in ["policy", "richtlinie", "zone"]):
            return ["storage_get_policy"]
        if any(kw in user_lower for kw in ["blacklist", "blocked paths", "gesperrt", "blockiert"]):
            return ["storage_list_blocked_paths"]
        if any(kw in user_lower for kw in ["managed paths", "verwaltete pfade", "managed"]):
            return ["storage_list_managed_paths"]
        if any(kw in user_lower for kw in ["audit", "änderungen", "aenderungen", "verlauf", "log"]):
            return ["storage_audit_log"]
        return ["storage_list_disks"]
    if any(kw in user_lower for kw in [
        "grafikkarte", "gpu", "vram", "hardware", "systemhardware", "welche karte"
    ]):
        return [{"tool": "run_skill", "args": {"name": "system_hardware_info", "action": "run", "args": {}}}]
    if any(kw in user_lower for kw in ["skill", "skills", "fähigkeit"]):
        if any(kw in user_lower for kw in ["zeig", "list", "welche", "hast du", "installiert", "verfügbar"]):
            if any(kw in user_lower for kw in ["draft", "entwurf", "noch nicht aktiv", "nicht aktiv"]):
                return ["list_draft_skills"]
            return ["list_skills"]
        if any(kw in user_lower for kw in ["erstell", "create", "bau", "mach"]):
            return ["autonomous_skill_task"]
    elif is_home_container_info_query_fn(user_lower):
        return ["container_list", {"tool": "home_read", "args": {"path": "."}}]
    elif is_home_container_start_query_fn(user_lower):
        return ["home_start"]
    elif is_active_container_capability_query_fn(user_lower):
        return ["container_inspect"]
    elif is_container_state_binding_query_fn(user_lower):
        return ["container_list"]
    elif any(kw in user_lower for kw in ["erinnerst du", "weißt du noch", "was weißt du über"]):
        return ["memory_graph_search"]
    elif any(kw in user_lower for kw in ["merk dir", "speicher", "remember"]):
        return ["memory_fact_save"]
    elif is_container_blueprint_catalog_query_fn(user_lower):
        return ["blueprint_list"]
    elif is_container_inventory_query_fn(user_lower):
        return ["container_list"]
    elif is_container_request_query_fn(user_lower) or any(kw in user_lower for kw in [
        "deploy container", "starte einen", "deploy blueprint", "python container", "node container",
        "starte python", "starte node", "starte sandbox"
    ]):
        return ["request_container"]
    elif any(kw in user_lower for kw in ["stoppe container", "stop container", "container stoppen", "beende container", "container beenden"]):
        return ["stop_container"]
    elif any(kw in user_lower for kw in ["container stats", "container status", "container auslastung", "container efficiency"]):
        return ["container_stats"]
    elif any(kw in user_lower for kw in ["container log", "container logs", "container ausgabe"]):
        return ["container_logs"]
    elif any(kw in user_lower for kw in ["snapshot", "snapshots", "snapshot list", "volume backup"]):
        return ["snapshot_list"]
    elif any(kw in user_lower for kw in [
        "berechne", "berechnung", "rechne", "ausführen", "execute",
        "führe aus", "run code", "code ausführen", "programmier",
        "fibonacci", "fakultät", "führe code", "code schreiben und ausführen"
    ]):
        return ["request_container", "exec_in_container"]
    return []


def detect_skill_by_trigger(
    user_text: str,
    *,
    skill_server_url: Optional[str] = None,
    urlopen_fn: Any = None,
    log_info_fn: Callable[[str], None],
) -> List[Any]:
    skill_server = skill_server_url or os.getenv("SKILL_SERVER_URL", "http://trion-skill-server:8088")
    open_fn = urlopen_fn or urllib.request.urlopen
    user_lower = user_text.lower()

    try:
        with open_fn(f"{skill_server}/v1/skills", timeout=2) as response:
            data = json.loads(response.read())
        active_names = data.get("active", [])

        best_match = None
        best_score = 0
        for name in active_names:
            try:
                with open_fn(f"{skill_server}/v1/skills/{name}", timeout=2) as meta_response:
                    meta = json.loads(meta_response.read())
                for trigger in meta.get("triggers", []):
                    trigger_lower = str(trigger).lower().strip()
                    if not trigger_lower:
                        continue
                    if trigger_lower in user_lower and len(trigger_lower) > best_score:
                        best_match = name
                        best_score = len(trigger_lower)
            except Exception:
                continue

        if best_match:
            log_info_fn(f"[Orchestrator] Trigger-Match: '{best_match}' (score={best_score})")
            return [best_match]
    except Exception as exc:
        log_info_fn(f"[Orchestrator] Trigger-Check fehlgeschlagen: {exc}")
    return []


def route_skill_request(
    user_text: str,
    thinking_plan: Dict[str, Any],
    *,
    get_skill_discovery_enable_fn: Optional[Callable[[], Any]] = None,
    get_skill_router_fn: Optional[Callable[[], Any]] = None,
    env_get_fn: Callable[[str, str], str] = os.getenv,
    log_info_fn: Callable[[str], None],
    log_error_fn: Callable[[str], None],
) -> Optional[Dict[str, Any]]:
    try:
        if get_skill_discovery_enable_fn is None:
            from config import get_skill_discovery_enable as _get_skill_discovery_enable

            get_skill_discovery_enable_fn = _get_skill_discovery_enable
        if not bool(get_skill_discovery_enable_fn()):
            log_info_fn("[Orchestrator] Skill discovery disabled (SKILL_DISCOVERY_ENABLE=false)")
            return None
    except Exception:
        if str(env_get_fn("SKILL_DISCOVERY_ENABLE", "true")).lower() != "true":
            log_info_fn("[Orchestrator] Skill discovery disabled via env fallback")
            return None

    try:
        if get_skill_router_fn is None:
            from core.skill_router import get_skill_router as _get_skill_router

            get_skill_router_fn = _get_skill_router
        router = get_skill_router_fn()
        decision = router.route(
            user_text=user_text,
            intent=thinking_plan.get("intent", ""),
        )
        if decision.decision == "use_existing" and decision.skill_name:
            return {"skill_name": decision.skill_name, "score": decision.score}
    except Exception as exc:
        log_error_fn(f"[Orchestrator] SkillRouter error (fail-closed): {exc}")
        return {
            "blocked": True,
            "reason": "skill_router_unavailable",
            "error": str(exc),
        }
    return None


def route_blueprint_request(
    user_text: str,
    thinking_plan: Dict[str, Any],
    *,
    get_blueprint_router_fn: Optional[Callable[[], Any]] = None,
    log_error_fn: Callable[[str], None],
) -> Optional[Dict[str, Any]]:
    try:
        if get_blueprint_router_fn is None:
            from core.blueprint_router import get_blueprint_router as _get_blueprint_router

            get_blueprint_router_fn = _get_blueprint_router
        router = get_blueprint_router_fn()
        decision = router.route(
            user_text=user_text,
            intent=thinking_plan.get("intent", "") if isinstance(thinking_plan, dict) else "",
        )
        if decision.decision == "use_blueprint" and decision.blueprint_id:
            return {"blueprint_id": decision.blueprint_id, "score": decision.score}
        if decision.decision == "suggest_blueprint" and decision.blueprint_id:
            return {
                "blueprint_id": decision.blueprint_id,
                "score": decision.score,
                "suggest": True,
                "candidates": decision.candidates,
            }
    except Exception as exc:
        log_error_fn(f"[Orchestrator] BlueprintRouter error (fail-closed): {exc}")
        return {
            "blocked": True,
            "reason": "blueprint_router_unavailable",
            "error": str(exc),
        }
    return None
