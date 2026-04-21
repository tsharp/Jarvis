"""Top-level auto-clarify policy entry points."""

from __future__ import annotations

from typing import Any, Dict, List

from core.task_loop.action_resolution.auto_clarify.contracts import (
    AutoClarifyAutonomyLevel,
    AutoClarifyDecision,
    AutoClarifyMode,
    AutoClarifySource,
    MissingField,
    ResolvedField,
)
from core.task_loop.action_resolution.auto_clarify.domain_dispatch import (
    dispatch_auto_clarify_proposal,
)
from core.task_loop.action_resolution.auto_clarify.safety_gates import (
    AutonomyCandidateScore,
    AutonomyGateDecision,
    evaluate_autonomy_gates,
)


def _proposal_missing_fields(proposal: Dict[str, Any]) -> List[MissingField]:
    return list(proposal.get("missing_fields") or [])


def _proposal_resolved_fields(proposal: Dict[str, Any]) -> List[ResolvedField]:
    return list(proposal.get("resolved_fields") or [])


def _autonomy_level_for_mode(mode: AutoClarifyMode) -> AutoClarifyAutonomyLevel:
    if mode in {AutoClarifyMode.SELF_DISCOVER, AutoClarifyMode.RESOLVE_SECRET}:
        return AutoClarifyAutonomyLevel.READ_ONLY
    if mode is AutoClarifyMode.SELF_COMPLETE:
        return AutoClarifyAutonomyLevel.SAFE_WRITE
    return AutoClarifyAutonomyLevel.READ_ONLY


def _default_ask_user_message(
    proposal: Dict[str, Any],
    missing_fields: List[MissingField],
) -> str:
    message = str(proposal.get("ask_user_message") or "").strip()
    if message:
        return message
    if missing_fields:
        return (
            "Ich brauche noch Angaben zu: "
            + ", ".join(item.name for item in missing_fields)
            + "."
        )
    return "Ich brauche noch eine Bestaetigung oder zusaetzliche Angaben, um sicher weiterzumachen."


def evaluate_auto_clarify(
    *,
    snapshot: Any,
    step_request: Any,
    step_result: Any | None = None,
    recheck_attempted: bool = False,
) -> AutoClarifyDecision:
    proposal = dispatch_auto_clarify_proposal(
        snapshot,
        step_request,
        step_result=step_result,
    )
    capability_family = str(proposal.get("capability_family") or "").strip().lower()
    candidates = list(proposal.get("candidates") or [])
    blockers = list(proposal.get("blockers") or [])
    rationale = list(proposal.get("rationale") or [])
    missing_fields = _proposal_missing_fields(proposal)
    resolved_fields = _proposal_resolved_fields(proposal)

    gate_result = evaluate_autonomy_gates(
        candidates,
        hard_blockers=blockers,
        recheck_attempted=recheck_attempted,
    )
    full_rationale = rationale + list(gate_result.rationale or [])
    detail = str(proposal.get("detail") or "").strip() or gate_result.detail

    if gate_result.decision is AutonomyGateDecision.BLOCK:
        return AutoClarifyDecision(
            resolved=False,
            mode=AutoClarifyMode.BLOCK,
            autonomy_level=AutoClarifyAutonomyLevel.READ_ONLY,
            source=AutoClarifySource.SAFETY_GATES,
            capability_family=capability_family,
            action=None,
            missing_fields=missing_fields,
            resolved_fields=resolved_fields,
            blockers=list(gate_result.hard_blockers),
            rationale=full_rationale,
            detail=detail or "auto_clarify_blocked",
            metadata={"recheck_attempted": bool(recheck_attempted)},
        )

    if gate_result.decision is AutonomyGateDecision.SELF_EXECUTE and gate_result.top_candidate is not None:
        action = gate_result.top_candidate.action
        mode = action.mode if action is not None else AutoClarifyMode.SELF_DISCOVER
        return AutoClarifyDecision(
            resolved=True,
            mode=mode,
            autonomy_level=_autonomy_level_for_mode(mode),
            source=AutoClarifySource.POLICY,
            capability_family=capability_family,
            action=action,
            missing_fields=missing_fields,
            resolved_fields=resolved_fields,
            blockers=[],
            rationale=full_rationale,
            detail=detail or "auto_clarify_self_execute",
            metadata={
                "recheck_attempted": bool(recheck_attempted),
                "confidence_margin": float(gate_result.confidence_margin),
            },
        )

    if gate_result.decision is AutonomyGateDecision.RECHECK:
        recheck_action = gate_result.top_candidate.action if gate_result.top_candidate is not None else None
        return AutoClarifyDecision(
            resolved=False,
            mode=AutoClarifyMode.SELF_DISCOVER,
            autonomy_level=AutoClarifyAutonomyLevel.READ_ONLY,
            source=AutoClarifySource.SAFETY_GATES,
            capability_family=capability_family,
            action=recheck_action,
            missing_fields=missing_fields,
            resolved_fields=resolved_fields,
            blockers=[],
            rationale=full_rationale,
            detail=detail or "auto_clarify_recheck_needed",
            metadata={
                "recheck_attempted": bool(recheck_attempted),
                "confidence_margin": float(gate_result.confidence_margin),
            },
        )

    return AutoClarifyDecision(
        resolved=False,
        mode=AutoClarifyMode.ASK_USER,
        autonomy_level=AutoClarifyAutonomyLevel.READ_ONLY,
        source=AutoClarifySource.SAFETY_GATES,
        capability_family=capability_family,
        action=None,
        missing_fields=missing_fields,
        resolved_fields=resolved_fields,
        blockers=[],
        rationale=full_rationale,
        detail=detail or "auto_clarify_ask_user",
        ask_user_message=_default_ask_user_message(proposal, missing_fields),
        metadata={
            "recheck_attempted": bool(recheck_attempted),
            "confidence_margin": float(gate_result.confidence_margin),
        },
    )


__all__ = ["evaluate_auto_clarify"]
