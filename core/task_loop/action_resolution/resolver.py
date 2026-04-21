from __future__ import annotations

from typing import Any, Dict

from core.task_loop.action_resolution.contracts import (
    ActionResolutionDecision,
    ActionResolutionMode,
    ActionResolutionSource,
    ResolvedLoopAction,
)
from core.task_loop.action_resolution.auto_clarify.policy import (
    evaluate_auto_clarify,
)
from core.task_loop.action_resolution.auto_clarify.contracts import (
    AutoClarifyDecision,
    AutoClarifyMode,
)
from core.task_loop.action_resolution.read_first_policy import (
    maybe_resolve_read_first_action,
)
from core.task_loop.action_resolution.domain_dispatch import dispatch_by_capability


def _resolved_execute_existing_step(
    step_request: Any,
    *,
    detail: str,
    rationale: list[str],
) -> ActionResolutionDecision:
    suggested_tools = list(getattr(step_request, "suggested_tools", []) or [])
    requested_capability = dict(getattr(step_request, "requested_capability", {}) or {})
    capability_context = dict(getattr(step_request, "capability_context", {}) or {})
    step_title = str(getattr(step_request, "step_title", "") or "").strip()
    step_type = str(getattr(getattr(step_request, "step_type", None), "value", getattr(step_request, "step_type", "")) or "").strip()
    return ActionResolutionDecision(
        resolved=True,
        action=ResolvedLoopAction(
            mode=ActionResolutionMode.EXECUTE_EXISTING_STEP,
            title=step_title,
            step_type=step_type,
            suggested_tools=suggested_tools,
            requested_capability=requested_capability,
            capability_context=capability_context,
        ),
        source=ActionResolutionSource.GENERIC,
        rationale=rationale,
        detail=detail,
    )


def _context_with_auto_clarify_fields(
    capability_context: Dict[str, Any],
    auto_decision: AutoClarifyDecision,
) -> Dict[str, Any]:
    merged = dict(capability_context or {})
    known_fields = dict(merged.get("known_fields") or {})
    for field in auto_decision.resolved_fields:
        known_fields[str(field.name)] = field.value
    if known_fields:
        merged["known_fields"] = known_fields

    unresolved_names = {str(field.name) for field in auto_decision.missing_fields}
    if unresolved_names:
        existing_missing = list(merged.get("missing_fields") or [])
        remaining = []
        for item in existing_missing:
            if isinstance(item, dict):
                name = str(item.get("name") or "").strip()
                if name and name in unresolved_names:
                    remaining.append(item)
                continue
            name = str(item or "").strip()
            if name and name in unresolved_names:
                remaining.append(name)
        merged["missing_fields"] = remaining
    return merged


def _auto_clarify_mode_to_action_mode(mode: AutoClarifyMode) -> ActionResolutionMode:
    if mode is AutoClarifyMode.SELF_DISCOVER:
        return ActionResolutionMode.INSERT_DISCOVERY_STEP
    if mode is AutoClarifyMode.SELF_COMPLETE:
        return ActionResolutionMode.EXECUTE_EXISTING_STEP
    if mode is AutoClarifyMode.RESOLVE_SECRET:
        return ActionResolutionMode.REPLAN_WITH_ACTION
    if mode is AutoClarifyMode.ASK_USER:
        return ActionResolutionMode.ASK_USER
    return ActionResolutionMode.BLOCK


def _decision_from_auto_clarify(
    step_request: Any,
    auto_decision: AutoClarifyDecision,
) -> ActionResolutionDecision | None:
    step_title = str(getattr(step_request, "step_title", "") or "").strip()
    step_type = str(
        getattr(
            getattr(step_request, "step_type", None),
            "value",
            getattr(step_request, "step_type", ""),
        )
        or ""
    ).strip()
    suggested_tools = list(getattr(step_request, "suggested_tools", []) or [])
    requested_capability = dict(getattr(step_request, "requested_capability", {}) or {})
    capability_context = dict(getattr(step_request, "capability_context", {}) or {})

    if auto_decision.mode is AutoClarifyMode.NO_ACTION:
        return None

    if auto_decision.mode in {AutoClarifyMode.ASK_USER, AutoClarifyMode.BLOCK}:
        return ActionResolutionDecision(
            resolved=True,
            action=ResolvedLoopAction(
                mode=_auto_clarify_mode_to_action_mode(auto_decision.mode),
                title=step_title,
                step_type=step_type,
                suggested_tools=[],
                requested_capability=requested_capability,
                capability_context=_context_with_auto_clarify_fields(
                    capability_context,
                    auto_decision,
                ),
                metadata={
                    "ask_user_message": auto_decision.ask_user_message,
                    "capability_family": auto_decision.capability_family,
                    "auto_clarify_mode": auto_decision.mode.value,
                },
            ),
            source=ActionResolutionSource.AUTO_CLARIFY_POLICY,
            rationale=list(auto_decision.rationale),
            blockers=[blocker.code for blocker in auto_decision.blockers],
            detail=auto_decision.detail or f"auto_clarify:{auto_decision.mode.value}",
        )

    action = auto_decision.action
    if action is None:
        return None

    resolved_capability_context = _context_with_auto_clarify_fields(
        action.capability_context or capability_context,
        auto_decision,
    )
    return ActionResolutionDecision(
        resolved=True,
        action=ResolvedLoopAction(
            mode=_auto_clarify_mode_to_action_mode(auto_decision.mode),
            title=action.title or step_title,
            step_type=action.step_type or step_type,
            suggested_tools=list(action.suggested_tools or suggested_tools),
            requested_capability=dict(action.requested_capability or requested_capability),
            capability_context=resolved_capability_context,
            metadata={
                "capability_family": auto_decision.capability_family,
                "auto_clarify_mode": auto_decision.mode.value,
                "auto_clarify_resolved": bool(auto_decision.resolved),
                "auto_clarify_metadata": dict(auto_decision.metadata or {}),
            },
        ),
        source=ActionResolutionSource.AUTO_CLARIFY_POLICY,
        rationale=list(auto_decision.rationale),
        blockers=[blocker.code for blocker in auto_decision.blockers],
        detail=auto_decision.detail or f"auto_clarify:{auto_decision.mode.value}",
    )


def resolve_next_loop_action(
    *,
    snapshot: Any,
    step_request: Any,
    step_result: Any | None = None,
    recovery_hint: Dict[str, Any] | None = None,
) -> ActionResolutionDecision:
    """Resolve the next concrete loop action.

    This is the generic package entry-point. For now it only defines the stable
    contract and returns a minimal default decision:
    - if the current step already carries tools or capability metadata, execute
      the existing step as-is
    - otherwise report an unresolved decision that higher-level policies can
      refine later
    """

    _ = snapshot
    _ = step_result
    _ = recovery_hint

    suggested_tools = list(getattr(step_request, "suggested_tools", []) or [])
    requested_capability = dict(getattr(step_request, "requested_capability", {}) or {})
    capability_context = dict(getattr(step_request, "capability_context", {}) or {})

    read_first_decision = maybe_resolve_read_first_action(step_request)
    if read_first_decision is not None:
        return read_first_decision

    # Wenn noch keine Capability bekannt ist: zuerst per Intent bestimmen,
    # bevor auto_clarify als generischer ASK_USER-Fallback greift.
    if not requested_capability:
        dispatch_decision = dispatch_by_capability(step_request)
        if dispatch_decision is not None:
            return dispatch_decision

    auto_clarify_decision = evaluate_auto_clarify(
        snapshot=snapshot,
        step_request=step_request,
        step_result=step_result,
        recheck_attempted=bool((recovery_hint or {}).get("recheck_attempted")),
    )
    translated_auto_decision = _decision_from_auto_clarify(
        step_request,
        auto_clarify_decision,
    )
    if translated_auto_decision is not None:
        return translated_auto_decision

    if suggested_tools or requested_capability or capability_context:
        rationale = ["step_request_has_action_metadata"]
        if suggested_tools:
            rationale.append("step_request_has_suggested_tools")
        if requested_capability:
            rationale.append("step_request_has_requested_capability")
        if capability_context:
            rationale.append("step_request_has_capability_context")
        return _resolved_execute_existing_step(
            step_request,
            detail="default_execute_existing_step",
            rationale=rationale,
        )

    return ActionResolutionDecision(
        resolved=False,
        action=None,
        source=ActionResolutionSource.GENERIC,
        rationale=["no_action_metadata_available"],
        blockers=["missing_action_resolution_policy"],
        detail="no_default_action_resolution",
    )


__all__ = ["resolve_next_loop_action"]
