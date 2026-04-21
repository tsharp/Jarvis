"""Safety and authority gates for autonomous self-clarification."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, Iterable, List, Sequence

from core.task_loop.action_resolution.auto_clarify.contracts import (
    AutoClarifyAction,
    AutoClarifyBlocker,
)

DEFAULT_AUTONOMY_THRESHOLD = 0.80
DEFAULT_RECHECK_THRESHOLD = 0.50
DEFAULT_CONFIDENCE_MARGIN = 0.10


class AutonomyGateDecision(str, Enum):
    SELF_EXECUTE = "self_execute"
    RECHECK = "recheck"
    ASK_USER = "ask_user"
    BLOCK = "block"


@dataclass(frozen=True)
class AutonomyGateConfig:
    autonomy_threshold: float = DEFAULT_AUTONOMY_THRESHOLD
    recheck_threshold: float = DEFAULT_RECHECK_THRESHOLD
    confidence_margin: float = DEFAULT_CONFIDENCE_MARGIN

    def to_dict(self) -> Dict[str, float]:
        return {
            "autonomy_threshold": float(self.autonomy_threshold),
            "recheck_threshold": float(self.recheck_threshold),
            "confidence_margin": float(self.confidence_margin),
        }


@dataclass(frozen=True)
class AutonomyCandidateScore:
    key: str
    score: float
    action: AutoClarifyAction | None = None
    rationale: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def normalized_score(self) -> float:
        return max(0.0, min(1.0, float(self.score)))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "key": self.key,
            "score": self.normalized_score(),
            "action": self.action.to_dict() if self.action is not None else None,
            "rationale": list(self.rationale),
            "metadata": dict(self.metadata),
        }


@dataclass(frozen=True)
class AutonomyGateResult:
    decision: AutonomyGateDecision
    config: AutonomyGateConfig
    top_candidate: AutonomyCandidateScore | None = None
    second_candidate: AutonomyCandidateScore | None = None
    confidence_margin: float = 0.0
    hard_blockers: List[AutoClarifyBlocker] = field(default_factory=list)
    rationale: List[str] = field(default_factory=list)
    detail: str = ""
    recheck_attempted: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "decision": self.decision.value,
            "config": self.config.to_dict(),
            "top_candidate": (
                self.top_candidate.to_dict() if self.top_candidate is not None else None
            ),
            "second_candidate": (
                self.second_candidate.to_dict()
                if self.second_candidate is not None
                else None
            ),
            "confidence_margin": float(self.confidence_margin),
            "hard_blockers": [item.to_dict() for item in self.hard_blockers],
            "rationale": list(self.rationale),
            "detail": self.detail,
            "recheck_attempted": bool(self.recheck_attempted),
        }


def _sorted_candidates(
    candidates: Sequence[AutonomyCandidateScore],
) -> List[AutonomyCandidateScore]:
    return sorted(
        candidates,
        key=lambda item: (item.normalized_score(), item.key),
        reverse=True,
    )


def _margin_between(
    top_candidate: AutonomyCandidateScore | None,
    second_candidate: AutonomyCandidateScore | None,
) -> float:
    if top_candidate is None or second_candidate is None:
        return 1.0 if top_candidate is not None else 0.0
    return max(
        0.0,
        top_candidate.normalized_score() - second_candidate.normalized_score(),
    )


def evaluate_autonomy_gates(
    candidates: Sequence[AutonomyCandidateScore],
    *,
    hard_blockers: Iterable[AutoClarifyBlocker] | None = None,
    config: AutonomyGateConfig | None = None,
    recheck_attempted: bool = False,
) -> AutonomyGateResult:
    gate_config = config or AutonomyGateConfig()
    blockers = list(hard_blockers or [])
    if blockers:
        return AutonomyGateResult(
            decision=AutonomyGateDecision.BLOCK,
            config=gate_config,
            hard_blockers=blockers,
            rationale=[
                "Mindestens ein harter Safety- oder Authority-Blocker ist aktiv."
            ],
            detail="Autonome Selbstklaerung ist wegen harter Blocker gesperrt.",
            recheck_attempted=recheck_attempted,
        )

    ranked_candidates = _sorted_candidates(candidates)
    top_candidate = ranked_candidates[0] if ranked_candidates else None
    second_candidate = ranked_candidates[1] if len(ranked_candidates) > 1 else None
    confidence_margin = _margin_between(top_candidate, second_candidate)

    if top_candidate is None:
        return AutonomyGateResult(
            decision=AutonomyGateDecision.ASK_USER,
            config=gate_config,
            rationale=[
                "Es gibt aktuell keinen autonomen Kandidaten fuer die naechste Massnahme."
            ],
            detail="Keine tragfaehige autonome Option gefunden.",
            recheck_attempted=recheck_attempted,
        )

    top_score = top_candidate.normalized_score()
    rationale = [
        f"Top-Kandidat `{top_candidate.key}` mit Score {top_score:.2f}.",
        f"Confidence-Margin zur zweitbesten Option: {confidence_margin:.2f}.",
    ]
    if top_candidate.rationale:
        rationale.extend(top_candidate.rationale)

    if (
        top_score >= gate_config.autonomy_threshold
        and confidence_margin >= gate_config.confidence_margin
    ):
        rationale.append(
            "Top-Kandidat erreicht den Autonomie-Schwellwert und ist klar genug getrennt."
        )
        return AutonomyGateResult(
            decision=AutonomyGateDecision.SELF_EXECUTE,
            config=gate_config,
            top_candidate=top_candidate,
            second_candidate=second_candidate,
            confidence_margin=confidence_margin,
            rationale=rationale,
            detail="Autonome Fortsetzung ist freigegeben.",
            recheck_attempted=recheck_attempted,
        )

    if not recheck_attempted:
        rationale.append(
            "Noch keine klare Autonomie-Freigabe. Ein weiterer Discovery-/Recheck-Pass ist noetig."
        )
        return AutonomyGateResult(
            decision=AutonomyGateDecision.RECHECK,
            config=gate_config,
            top_candidate=top_candidate,
            second_candidate=second_candidate,
            confidence_margin=confidence_margin,
            rationale=rationale,
            detail="Autonome Optionen sind noch nicht stark oder eindeutig genug.",
            recheck_attempted=recheck_attempted,
        )

    if top_score >= gate_config.recheck_threshold:
        rationale.append(
            "Auch nach Recheck bleibt die Auswahl zu unscharf. User-Klaerung ist noetig."
        )
    else:
        rationale.append(
            "Auch nach Recheck bleibt kein Kandidat ausreichend tragfaehig."
        )
    return AutonomyGateResult(
        decision=AutonomyGateDecision.ASK_USER,
        config=gate_config,
        top_candidate=top_candidate,
        second_candidate=second_candidate,
        confidence_margin=confidence_margin,
        rationale=rationale,
        detail="User-Rueckfrage ist noetig, weil keine ausreichend starke autonome Option bleibt.",
        recheck_attempted=recheck_attempted,
    )


def should_self_execute(result: AutonomyGateResult) -> bool:
    return result.decision == AutonomyGateDecision.SELF_EXECUTE


def should_recheck(result: AutonomyGateResult) -> bool:
    return result.decision == AutonomyGateDecision.RECHECK


def should_ask_user(result: AutonomyGateResult) -> bool:
    return result.decision == AutonomyGateDecision.ASK_USER


def should_block(result: AutonomyGateResult) -> bool:
    return result.decision == AutonomyGateDecision.BLOCK


__all__ = [
    "AutonomyCandidateScore",
    "AutonomyGateConfig",
    "AutonomyGateDecision",
    "AutonomyGateResult",
    "DEFAULT_AUTONOMY_THRESHOLD",
    "DEFAULT_CONFIDENCE_MARGIN",
    "DEFAULT_RECHECK_THRESHOLD",
    "evaluate_autonomy_gates",
    "should_ask_user",
    "should_block",
    "should_recheck",
    "should_self_execute",
]
