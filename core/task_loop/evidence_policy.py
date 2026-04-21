from __future__ import annotations

import csv
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Any, Iterable

from core.task_loop.contracts import TaskLoopSnapshot


_REPO_ROOT = Path(__file__).resolve().parents[2]
_OUTPUT_STANDARDS_PATH = _REPO_ROOT / "CIM-skill_rag" / "output_standards.csv"
_VALIDATION_TESTS_PATH = _REPO_ROOT / "CIM-skill_rag" / "validation_tests.csv"


@dataclass(frozen=True)
class TaskLoopEvidenceAssessment:
    evidence_score: float
    completion_confidence: float
    requires_verification: bool
    matched_standard_id: str = ""
    matched_template_id: str = ""
    rationale: tuple[str, ...] = field(default_factory=tuple)


def _clamp(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


def _read_csv_rows(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8") as handle:
        return [dict(row) for row in csv.DictReader(handle)]


@lru_cache(maxsize=1)
def _output_standards() -> tuple[dict[str, str], ...]:
    return tuple(_read_csv_rows(_OUTPUT_STANDARDS_PATH))


@lru_cache(maxsize=1)
def _validation_tests() -> tuple[dict[str, str], ...]:
    return tuple(_read_csv_rows(_VALIDATION_TESTS_PATH))


def _schema_keys(schema_text: str) -> set[str]:
    raw = str(schema_text or "").strip().strip("{}")
    keys: set[str] = set()
    for chunk in raw.split(","):
        head = chunk.split(":", 1)[0].strip().strip("'\"")
        if head:
            keys.add(head)
    return keys


def _collect_payloads(snapshot: TaskLoopSnapshot) -> list[dict[str, Any]]:
    payloads: list[dict[str, Any]] = []
    last_step_result = snapshot.last_step_result if isinstance(snapshot.last_step_result, dict) else {}
    execution_result = last_step_result.get("execution_result")
    if isinstance(execution_result, dict) and execution_result:
        payloads.append(dict(execution_result))
    for artifact in snapshot.verified_artifacts or []:
        if not isinstance(artifact, dict):
            continue
        if str(artifact.get("artifact_type") or "").strip().lower() != "execution_result":
            continue
        payloads.append(dict(artifact))
    return payloads


def _last_status(snapshot: TaskLoopSnapshot) -> str:
    if isinstance(snapshot.last_step_result, dict):
        return str(snapshot.last_step_result.get("status") or "").strip().lower()
    return ""


def _last_source(snapshot: TaskLoopSnapshot) -> str:
    if isinstance(snapshot.last_step_result, dict):
        return str(snapshot.last_step_result.get("step_execution_source") or "").strip().lower()
    return str(snapshot.step_execution_source.value or "").strip().lower()


def _last_step_type(snapshot: TaskLoopSnapshot) -> str:
    if isinstance(snapshot.last_step_result, dict):
        return str(snapshot.last_step_result.get("step_type") or "").strip().lower()
    return str(snapshot.current_step_type.value or "").strip().lower()


def _infer_template_id(snapshot: TaskLoopSnapshot, payloads: Iterable[dict[str, Any]]) -> str:
    last_step_result = snapshot.last_step_result if isinstance(snapshot.last_step_result, dict) else {}
    candidates: list[Any] = [
        last_step_result.get("template_id"),
        (last_step_result.get("execution_result") or {}).get("template_id")
        if isinstance(last_step_result.get("execution_result"), dict)
        else None,
        ((last_step_result.get("execution_result") or {}).get("metadata") or {}).get("template_id")
        if isinstance((last_step_result.get("execution_result") or {}).get("metadata"), dict)
        else None,
    ]
    for payload in payloads:
        candidates.extend(
            [
                payload.get("template_id"),
                (payload.get("metadata") or {}).get("template_id")
                if isinstance(payload.get("metadata"), dict)
                else None,
            ]
        )
    for candidate in candidates:
        value = str(candidate or "").strip()
        if value:
            return value
    return ""


def _match_output_standard(payloads: Iterable[dict[str, Any]]) -> tuple[str, list[str], float]:
    rationale: list[str] = []
    for payload in payloads:
        if not isinstance(payload, dict):
            continue
        payload_keys = set(payload.keys())
        if not payload_keys:
            continue
        for row in _output_standards():
            success_keys = _schema_keys(row.get("success_format", ""))
            error_keys = _schema_keys(row.get("error_format", ""))
            if error_keys and error_keys.issubset(payload_keys):
                rationale.append(
                    "output_standard_error="
                    f"{row.get('standard_id', '')}:{row.get('category', '')}:{row.get('schema_validation', '')}"
                )
                return str(row.get("standard_id") or "").strip(), rationale, 0.12
            if success_keys and success_keys.issubset(payload_keys):
                rationale.append(
                    "output_standard_success="
                    f"{row.get('standard_id', '')}:{row.get('category', '')}:{row.get('schema_validation', '')}"
                )
                return str(row.get("standard_id") or "").strip(), rationale, 0.22
    return "", rationale, 0.0


def _match_validation_template(template_id: str) -> tuple[str, list[str], float]:
    if not template_id:
        return "", [], 0.0
    for row in _validation_tests():
        row_template_id = str(row.get("template_id") or "").strip()
        if row_template_id != template_id:
            continue
        rationale = [
            f"validation_template={row_template_id}",
            f"validation_logic={str(row.get('expected_output_logic') or '').strip()}",
        ]
        return row_template_id, rationale, 0.15
    return "", [], 0.0


def assess_task_loop_evidence(snapshot: TaskLoopSnapshot) -> TaskLoopEvidenceAssessment:
    payloads = _collect_payloads(snapshot)
    last_status = _last_status(snapshot)
    last_source = _last_source(snapshot)
    last_step_type = _last_step_type(snapshot)
    plan_complete = not str(snapshot.pending_step or "").strip()

    rationale: list[str] = []
    evidence_score = 0.0

    if snapshot.completed_steps:
        evidence_score += 0.12
        rationale.append(f"completed_steps={len(snapshot.completed_steps)}")

    if last_status == "completed":
        evidence_score += 0.18
        rationale.append("last_step_status=completed")
    elif last_status in {"failed", "blocked"}:
        evidence_score -= 0.22
        rationale.append(f"last_step_status={last_status}")

    if payloads:
        evidence_score += 0.18
        rationale.append(f"execution_payloads={len(payloads)}")

    if any(isinstance(payload.get("grounding"), dict) and payload.get("grounding") for payload in payloads):
        evidence_score += 0.16
        rationale.append("grounding_present")

    if any(list(payload.get("tool_statuses") or []) for payload in payloads):
        evidence_score += 0.12
        rationale.append("tool_statuses_present")

    matched_standard_id, standard_rationale, standard_bonus = _match_output_standard(payloads)
    rationale.extend(standard_rationale)
    evidence_score += standard_bonus

    matched_template_id, validation_rationale, validation_bonus = _match_validation_template(
        _infer_template_id(snapshot, payloads)
    )
    rationale.extend(validation_rationale)
    evidence_score += validation_bonus

    if any("error" in payload for payload in payloads):
        evidence_score -= 0.20
        rationale.append("payload_error_present")

    evidence_score = _clamp(evidence_score)

    completion_confidence = _clamp(
        (0.55 if plan_complete else 0.0)
        + (0.35 * evidence_score)
        + (0.10 if last_status == "completed" else 0.0)
    )

    requires_verification = False
    if plan_complete and (
        "orchestrator" in last_source
        or "tool_" in last_step_type
        or snapshot.verified_artifacts
        or last_step_type == "response_step"
    ):
        requires_verification = evidence_score < 0.55
    if any("error" in payload for payload in payloads):
        requires_verification = True

    return TaskLoopEvidenceAssessment(
        evidence_score=evidence_score,
        completion_confidence=completion_confidence,
        requires_verification=requires_verification,
        matched_standard_id=matched_standard_id,
        matched_template_id=matched_template_id,
        rationale=tuple(rationale),
    )


__all__ = ["TaskLoopEvidenceAssessment", "assess_task_loop_evidence"]
