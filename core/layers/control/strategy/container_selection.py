"""Container-selection helpers for ControlLayer."""

from __future__ import annotations

from typing import Any


def normalize_container_candidates(thinking_plan: dict[str, Any]) -> list[dict[str, Any]]:
    """Normalize container candidates to compact ``{id, score}`` rows."""
    raw = []
    if isinstance(thinking_plan, dict):
        raw = thinking_plan.get("_container_candidates") or []
        if not raw and isinstance(thinking_plan.get("_container_resolution"), dict):
            raw = thinking_plan["_container_resolution"].get("candidates") or []

    out: list[dict[str, Any]] = []
    seen = set()
    for row in raw or []:
        if not isinstance(row, dict):
            continue
        blueprint_id = str(row.get("id") or row.get("blueprint_id") or "").strip()
        if not blueprint_id or blueprint_id in seen:
            continue
        seen.add(blueprint_id)
        try:
            score = float(row.get("score") or 0.0)
        except Exception:
            score = 0.0
        out.append({"id": blueprint_id, "score": score})
    out.sort(key=lambda item: item.get("score", 0.0), reverse=True)
    return out


def is_container_request_plan(thinking_plan: dict[str, Any]) -> bool:
    """Detect whether the plan represents a container-request path."""
    if not isinstance(thinking_plan, dict):
        return False
    suggested = thinking_plan.get("suggested_tools") or []
    suggested_names = [str(t.get("tool") if isinstance(t, dict) else t).strip() for t in suggested]
    if any(name in {"request_container", "home_start"} for name in suggested_names):
        return True

    route = thinking_plan.get("_domain_route", {})
    operation = str((route or {}).get("operation") or "").strip().lower()
    domain_tag = str((route or {}).get("domain_tag") or "").strip().upper()
    has_container_resolution = bool(
        thinking_plan.get("_container_candidates")
        or thinking_plan.get("_container_resolution")
    )
    return (
        domain_tag == "CONTAINER"
        and operation in {"create", "start", "run", "provision"}
        and has_container_resolution
    )


def apply_container_candidate_resolution(
    verification: dict[str, Any],
    thinking_plan: dict[str, Any],
    *,
    user_text: str = "",
    is_container_request_plan_fn,
    has_hard_safety_markers_fn,
    user_text_has_hard_safety_keywords_fn,
    user_text_has_malicious_intent_fn,
    normalize_container_candidates_fn,
    warning_list_fn,
    container_auto_select_min_score: float,
    container_auto_select_min_margin: float,
) -> dict[str, Any]:
    """Resolve container candidates into selection, clarification, or blueprint fallback."""
    if not isinstance(verification, dict) or not is_container_request_plan_fn(thinking_plan):
        return verification
    suggested = thinking_plan.get("suggested_tools") or []
    suggested_names = [str(t.get("tool") if isinstance(t, dict) else t).strip() for t in suggested]
    if bool(thinking_plan.get("_trion_home_start_fast_path")) or "home_start" in suggested_names:
        return verification
    if (
        has_hard_safety_markers_fn(verification)
        or user_text_has_hard_safety_keywords_fn(user_text)
        or user_text_has_malicious_intent_fn(user_text)
    ):
        return verification

    resolution = thinking_plan.get("_container_resolution", {}) if isinstance(thinking_plan, dict) else {}
    if not isinstance(resolution, dict):
        resolution = {}
    candidates = normalize_container_candidates_fn(thinking_plan)
    decision = str(resolution.get("decision") or "").strip().lower() or "no_blueprint"
    warnings = warning_list_fn(verification.get("warnings", []))
    corrections = verification.get("corrections", {})
    if not isinstance(corrections, dict):
        corrections = {}

    top = candidates[0] if candidates else {}
    top_id = str(top.get("id") or "").strip()
    top_score = float(top.get("score") or 0.0) if top else 0.0
    second_score = float(candidates[1].get("score") or 0.0) if len(candidates) > 1 else 0.0
    score_margin = top_score - second_score
    merged_text = f"{str(user_text or '')} {str((thinking_plan or {}).get('intent') or '')}".lower()
    explicit_match = bool(top_id and top_id.lower() in merged_text)

    auto_select = False
    if top_id:
        if explicit_match or decision == "use_blueprint" or len(candidates) == 1:
            auto_select = True
        elif (
            top_score >= container_auto_select_min_score
            and score_margin >= container_auto_select_min_margin
        ):
            auto_select = True

    if auto_select and top_id:
        corrections["_selected_blueprint_id"] = top_id
        corrections["_blueprint_gate_blocked"] = False
        corrections["_blueprint_gate_reason"] = ""
        corrections["_blueprint_recheck_required"] = False
        corrections["_blueprint_recheck_reason"] = ""
        corrections["_blueprint_no_match"] = False
        corrections["_container_resolution"] = {
            "decision": "selected",
            "blueprint_id": top_id,
            "score": top_score,
            "reason": str(resolution.get("reason") or "control_selected_blueprint"),
            "candidates": candidates[:3],
        }
        verification["corrections"] = corrections
        verification["approved"] = True
        verification["hard_block"] = False
        verification["decision_class"] = "allow" if not warnings else "warn"
        verification["block_reason_code"] = ""
        verification["reason"] = "container_blueprint_selected_by_control"
        if not verification.get("final_instruction"):
            verification["final_instruction"] = (
                f"Nutze request_container mit blueprint_id='{top_id}'."
            )
        return verification

    verification["approved"] = True
    verification["hard_block"] = False
    verification["decision_class"] = "warn"
    verification["block_reason_code"] = ""

    if candidates:
        corrections["_blueprint_gate_blocked"] = False
        corrections["_blueprint_gate_reason"] = ""
        corrections["_blueprint_recheck_required"] = True
        corrections["_blueprint_recheck_reason"] = "container_blueprint_recheck_required"
        corrections["_blueprint_no_match"] = False
        corrections["_blueprint_suggest"] = {
            "blueprint_id": top_id,
            "score": top_score,
            "suggest": True,
            "candidates": candidates[:3],
        }
        corrections["_container_resolution"] = {
            "decision": "recheck_required",
            "blueprint_id": top_id,
            "score": top_score,
            "reason": str(resolution.get("reason") or "container_blueprint_recheck_required"),
            "candidates": candidates[:3],
        }
        warnings.append(
            "Container blueprint selection is not strong enough yet; Control downgraded the turn to blueprint discovery before any user clarification."
        )
        verification["suggested_tools"] = ["blueprint_list"]
        verification["_authoritative_suggested_tools"] = ["blueprint_list"]
        verification["reason"] = "container_blueprint_recheck_required"
        verification["final_instruction"] = (
            "Führe zuerst blueprint_list aus und prüfe die verfügbaren Blueprints. "
            "Frage den User erst dann, wenn nach der Discovery weiterhin mehrere plausible Blueprints übrig bleiben. "
            "Führe request_container noch nicht aus."
        )
    else:
        corrections["_blueprint_gate_blocked"] = False
        corrections["_blueprint_gate_reason"] = ""
        corrections["_blueprint_recheck_required"] = True
        corrections["_blueprint_recheck_reason"] = "container_blueprint_discovery_required"
        corrections["_blueprint_no_match"] = True
        corrections["_container_resolution"] = {
            "decision": "discovery_required",
            "blueprint_id": "",
            "score": float(resolution.get("score") or 0.0),
            "reason": str(resolution.get("reason") or "container_blueprint_discovery_required"),
            "candidates": [],
        }
        warnings.append(
            "No verified blueprint match was strong enough; Control requires blueprint discovery before any user clarification."
        )
        verification["suggested_tools"] = ["blueprint_list"]
        verification["_authoritative_suggested_tools"] = ["blueprint_list"]
        verification["reason"] = "container_blueprint_discovery_required"
        verification["final_instruction"] = (
            "Führe zuerst blueprint_list aus und ermittle verfügbare Blueprints. "
            "Biete dem User erst danach eine Auswahl oder einen neuen Blueprint an. "
            "Führe request_container nicht frei aus."
        )

    verification["corrections"] = corrections
    verification["warnings"] = warnings
    return verification
