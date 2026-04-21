from __future__ import annotations

import csv
import re
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

from core.task_loop.contracts import TaskLoopSnapshot


_REPO_ROOT = Path(__file__).resolve().parents[2]
_ANTI_PATTERNS_PATH = _REPO_ROOT / "intelligence_modules" / "procedural_rag" / "anti_patterns.csv"
_ERROR_PATTERNS_PATH = _REPO_ROOT / "CIM-skill_rag" / "error_handling_patterns.csv"
_CAUSAL_CONTEXT_RE = re.compile(
    r"\b(cause|causes|causal|because|why|effect|impact|influence|correlation|correlated|associated)\b",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class TaskLoopProgressAssessment:
    progress_score: float
    novelty_score: float
    blocker_burden: float
    hard_blocked: bool
    requires_recovery: bool
    matched_anti_pattern_ids: tuple[str, ...] = field(default_factory=tuple)
    matched_error_pattern_ids: tuple[str, ...] = field(default_factory=tuple)
    rationale: tuple[str, ...] = field(default_factory=tuple)


def _clamp(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


def _read_csv_rows(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8") as handle:
        return [dict(row) for row in csv.DictReader(handle)]


@lru_cache(maxsize=1)
def _anti_patterns() -> tuple[dict[str, str], ...]:
    return tuple(_read_csv_rows(_ANTI_PATTERNS_PATH))


@lru_cache(maxsize=1)
def _error_patterns() -> tuple[dict[str, str], ...]:
    return tuple(_read_csv_rows(_ERROR_PATTERNS_PATH))


def _last_step_text(snapshot: TaskLoopSnapshot) -> str:
    parts = [
        str(snapshot.pending_step or ""),
        str(snapshot.last_user_visible_answer or ""),
    ]
    if isinstance(snapshot.last_step_result, dict):
        parts.extend(
            [
                str(snapshot.last_step_result.get("trace_reason") or ""),
                str(snapshot.last_step_result.get("user_visible_summary") or ""),
                str(snapshot.last_step_result.get("next_action") or ""),
            ]
        )
        execution_result = snapshot.last_step_result.get("execution_result")
        if isinstance(execution_result, dict):
            parts.extend(
                [
                    str(execution_result.get("done_reason") or ""),
                    str(execution_result.get("error") or ""),
                ]
            )
    return " ".join(part for part in parts if part).strip()


def _match_anti_patterns(text: str) -> tuple[list[str], list[str], bool, float, float, bool]:
    matched_ids: list[str] = []
    rationale: list[str] = []
    hard_blocked = False
    blocker_burden = 0.0
    progress_penalty = 0.0
    requires_recovery = False

    if not text or not _CAUSAL_CONTEXT_RE.search(text):
        return matched_ids, rationale, hard_blocked, blocker_burden, progress_penalty, requires_recovery

    lowered = text.lower()
    for row in _anti_patterns():
        pattern_id = str(row.get("pattern_id") or "").strip()
        keywords = str(row.get("trigger_keywords") or "").strip()
        if not pattern_id or not keywords:
            continue
        triggers = [token.strip().lower() for token in keywords.split("|") if token.strip()]
        if not triggers or not any(trigger in lowered for trigger in triggers):
            continue
        matched_ids.append(pattern_id)
        severity = str(row.get("severity") or "").strip().lower()
        rationale.append(f"anti_pattern={pattern_id}:{severity}")
        if severity == "critical":
            hard_blocked = True
            blocker_burden = max(blocker_burden, 0.90)
            progress_penalty += 0.35
            requires_recovery = True
        elif severity == "high":
            blocker_burden = max(blocker_burden, 0.70)
            progress_penalty += 0.20
            requires_recovery = True
        else:
            blocker_burden = max(blocker_burden, 0.45)
            progress_penalty += 0.08
    return matched_ids, rationale, hard_blocked, blocker_burden, progress_penalty, requires_recovery


def _match_error_patterns(text: str, snapshot: TaskLoopSnapshot) -> tuple[list[str], list[str], float, bool]:
    lowered = text.lower()
    matched_ids: list[str] = []
    rationale: list[str] = []
    blocker_burden = 0.0
    requires_recovery = False

    for row in _error_patterns():
        pattern_id = str(row.get("pattern_id") or "").strip()
        if not pattern_id:
            continue
        hit = False
        if pattern_id == "TIMEOUT" and ("timed out" in lowered or "timeout" in lowered):
            hit = True
        elif pattern_id == "RATE_LIMIT" and ("429" in lowered or "too many requests" in lowered):
            hit = True
        elif pattern_id == "SCHEMA_MISMATCH" and ("schema" in lowered or "validation" in lowered):
            hit = True
        elif pattern_id == "ERR-03" and ("required parameter" in lowered or "missing" in lowered):
            hit = True
        elif pattern_id == "ERR-01" and ("invalid type" in lowered or "expected" in lowered):
            hit = True
        if not hit:
            continue
        matched_ids.append(pattern_id)
        recovery_action = str(row.get("recovery_action") or "").strip().lower()
        retry_limit = str(row.get("retry_limit") or "").strip()
        rationale.append(f"error_pattern={pattern_id}:{recovery_action}:{retry_limit}")
        if recovery_action in {"retry", "fallback"}:
            requires_recovery = True
        blocker_burden = max(
            blocker_burden,
            0.65 if recovery_action == "retry" else 0.75 if recovery_action == "fallback" else 0.55,
        )

    last_status = ""
    if isinstance(snapshot.last_step_result, dict):
        last_status = str(snapshot.last_step_result.get("status") or "").strip().lower()
    if last_status in {"failed", "blocked"}:
        blocker_burden = max(blocker_burden, 0.60)
        rationale.append(f"last_step_status={last_status}")
    return matched_ids, rationale, blocker_burden, requires_recovery


def assess_task_loop_progress(snapshot: TaskLoopSnapshot) -> TaskLoopProgressAssessment:
    text = _last_step_text(snapshot)
    rationale: list[str] = []

    progress_score = 0.0
    if snapshot.completed_steps:
        progress_score += 0.18
        rationale.append(f"completed_steps={len(snapshot.completed_steps)}")
    if snapshot.step_index > 0:
        progress_score += 0.14
        rationale.append(f"step_index={snapshot.step_index}")
    if str(snapshot.pending_step or "").strip():
        progress_score += 0.12
        rationale.append("pending_step_present")
    if isinstance(snapshot.last_step_result, dict):
        status = str(snapshot.last_step_result.get("status") or "").strip().lower()
        if status == "completed":
            progress_score += 0.28
            rationale.append("last_step_completed")
        elif status in {"waiting_for_user", "waiting_for_approval"}:
            progress_score += 0.10
            rationale.append(f"last_step_status={status}")

    novelty_score = 0.20
    if snapshot.verified_artifacts:
        novelty_score += 0.25
        rationale.append(f"verified_artifacts={len(snapshot.verified_artifacts)}")
    if str(snapshot.last_user_visible_answer or "").strip():
        novelty_score += 0.20
        rationale.append("visible_answer_present")
    if isinstance(snapshot.last_step_result, dict) and snapshot.last_step_result:
        novelty_score += 0.20
        rationale.append("last_step_result_present")

    anti_pattern_ids, anti_rationale, hard_blocked, anti_blocker, anti_penalty, anti_recovery = (
        _match_anti_patterns(text)
    )
    rationale.extend(anti_rationale)

    error_pattern_ids, error_rationale, error_blocker, error_recovery = _match_error_patterns(text, snapshot)
    rationale.extend(error_rationale)

    progress_score = _clamp(progress_score - anti_penalty)
    novelty_score = _clamp(novelty_score - (0.10 if error_pattern_ids else 0.0))
    blocker_burden = _clamp(max(anti_blocker, error_blocker))

    return TaskLoopProgressAssessment(
        progress_score=progress_score,
        novelty_score=novelty_score,
        blocker_burden=blocker_burden,
        hard_blocked=hard_blocked,
        requires_recovery=anti_recovery or error_recovery,
        matched_anti_pattern_ids=tuple(anti_pattern_ids),
        matched_error_pattern_ids=tuple(error_pattern_ids),
        rationale=tuple(rationale),
    )


__all__ = ["TaskLoopProgressAssessment", "assess_task_loop_progress"]
