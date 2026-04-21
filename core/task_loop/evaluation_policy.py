from __future__ import annotations

from dataclasses import dataclass

from core.task_loop.completion_policy import completion_detail, is_task_loop_complete
from core.task_loop.contracts import RiskLevel, StopReason, TaskLoopSnapshot
from core.task_loop.evidence_policy import TaskLoopEvidenceAssessment, assess_task_loop_evidence
from core.task_loop.guards import StopDecision, detect_loop
from core.task_loop.progress_policy import TaskLoopProgressAssessment, assess_task_loop_progress


@dataclass(frozen=True)
class TaskLoopEvaluation:
    stop_decision: StopDecision
    progress_made: bool
    is_complete: bool
    detail: str = ""
    evidence_assessment: TaskLoopEvidenceAssessment | None = None
    progress_assessment: TaskLoopProgressAssessment | None = None


def evaluate_task_loop_iteration(
    snapshot: TaskLoopSnapshot,
    *,
    max_steps: int = 4,
    max_errors: int = 4,
    max_no_progress: int = 2,
    repeated_action_threshold: int = 2,
) -> TaskLoopEvaluation:
    evidence_assessment = assess_task_loop_evidence(snapshot)
    progress_assessment = assess_task_loop_progress(snapshot)

    if snapshot.error_count >= max_errors:
        detail = (
            f"error_count={snapshot.error_count} max_errors={max_errors} "
            f"progress={progress_assessment.progress_score:.2f}"
        )
        return TaskLoopEvaluation(
            stop_decision=StopDecision(True, StopReason.MAX_ERRORS_REACHED, detail),
            progress_made=False,
            is_complete=False,
            detail=detail,
            evidence_assessment=evidence_assessment,
            progress_assessment=progress_assessment,
        )

    if snapshot.no_progress_count >= max_no_progress:
        detail = (
            f"no_progress_count={snapshot.no_progress_count} max_no_progress={max_no_progress} "
            f"novelty={progress_assessment.novelty_score:.2f}"
        )
        return TaskLoopEvaluation(
            stop_decision=StopDecision(True, StopReason.NO_PROGRESS, detail),
            progress_made=False,
            is_complete=False,
            detail=detail,
            evidence_assessment=evidence_assessment,
            progress_assessment=progress_assessment,
        )

    if snapshot.tool_trace and detect_loop(
        snapshot.tool_trace,
        repeated_threshold=repeated_action_threshold,
    ):
        detail = (
            f"repeated_action_threshold={repeated_action_threshold} "
            f"progress={progress_assessment.progress_score:.2f}"
        )
        return TaskLoopEvaluation(
            stop_decision=StopDecision(True, StopReason.LOOP_DETECTED, detail),
            progress_made=False,
            is_complete=False,
            detail=detail,
            evidence_assessment=evidence_assessment,
            progress_assessment=progress_assessment,
        )

    if snapshot.risk_level == RiskLevel.RISKY:
        detail = (
            f"{snapshot.risk_level.value} evidence={evidence_assessment.evidence_score:.2f} "
            f"verification={str(evidence_assessment.requires_verification).lower()}"
        )
        return TaskLoopEvaluation(
            stop_decision=StopDecision(True, StopReason.RISK_GATE_REQUIRED, detail),
            progress_made=True,
            is_complete=False,
            detail=detail,
            evidence_assessment=evidence_assessment,
            progress_assessment=progress_assessment,
        )

    if snapshot.risk_level == RiskLevel.BLOCKED:
        detail = (
            f"{snapshot.risk_level.value} blocker_burden={progress_assessment.blocker_burden:.2f}"
        )
        return TaskLoopEvaluation(
            stop_decision=StopDecision(True, StopReason.NO_CONCRETE_NEXT_STEP, detail),
            progress_made=False,
            is_complete=False,
            detail=detail,
            evidence_assessment=evidence_assessment,
            progress_assessment=progress_assessment,
        )

    if is_task_loop_complete(snapshot):
        detail = (
            f"{completion_detail(snapshot)} "
            f"completion_confidence={evidence_assessment.completion_confidence:.2f} "
            f"requires_verification={str(evidence_assessment.requires_verification).lower()}"
        )
        return TaskLoopEvaluation(
            stop_decision=StopDecision(False),
            progress_made=True,
            is_complete=True,
            detail=detail,
            evidence_assessment=evidence_assessment,
            progress_assessment=progress_assessment,
        )

    if snapshot.step_index >= max_steps:
        detail = (
            f"step_index={snapshot.step_index} max_steps={max_steps} "
            f"completion_confidence={evidence_assessment.completion_confidence:.2f}"
        )
        return TaskLoopEvaluation(
            stop_decision=StopDecision(True, StopReason.MAX_STEPS_REACHED, detail),
            progress_made=True,
            is_complete=False,
            detail=detail,
            evidence_assessment=evidence_assessment,
            progress_assessment=progress_assessment,
        )

    detail = (
        f"next_step={str(snapshot.pending_step or '')[:120]} "
        f"progress={progress_assessment.progress_score:.2f} "
        f"evidence={evidence_assessment.evidence_score:.2f}"
    )
    return TaskLoopEvaluation(
        stop_decision=StopDecision(False),
        progress_made=True,
        is_complete=False,
        detail=detail,
        evidence_assessment=evidence_assessment,
        progress_assessment=progress_assessment,
    )


__all__ = ["TaskLoopEvaluation", "evaluate_task_loop_iteration"]
