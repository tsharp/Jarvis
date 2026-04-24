from __future__ import annotations

from core.task_loop.capability_policy import requested_capability_from_tools
from core.task_loop.capabilities.container.recovery import (
    CONTAINER_INSPECT_STEP_TITLE,
    DISCOVERY_STEP_TITLE,
    RUNTIME_DISCOVERY_STEP_TITLE,
    build_container_recovery_hint as _build_container_recovery_hint,
)
from core.task_loop.contracts import RiskLevel, TaskLoopStepType
from core.task_loop.replan_engine import apply_replan_hint


def _build_discovery_step(
    *,
    current_step_meta: dict[str, object],
    recovery_hint: dict[str, object],
    title_override: str | None = None,
) -> dict[str, object]:
    next_tools = list(recovery_hint.get("next_tools") or [])
    step_id = str(current_step_meta.get("step_id") or "step").strip() or "step"
    title = str(title_override or recovery_hint.get("replan_step_title") or DISCOVERY_STEP_TITLE).strip() or DISCOVERY_STEP_TITLE
    if next_tools == ["container_list"]:
        goal = "Mit einem sicheren Query-Tool sichtbar pruefen, welche Container aktuell laufen oder bereits vorhanden sind."
        done_criteria = "Ein verifizierter Runtime-Inventar-Befund zu vorhandenen oder laufenden Containern liegt vor."
    elif next_tools == ["container_inspect"]:
        goal = "Einen konkreten Container gezielt inspizieren, um den verifizierten Runtime-Zustand sichtbar zu klaeren."
        done_criteria = "Ein verifizierter Befund zum konkreten Container-Zustand liegt vor."
    else:
        goal = "Die passende Container-Basis oder Blueprint-Auswahl mit einem sicheren Query-Tool sichtbar pruefen."
        done_criteria = "Ein verifizierter Discovery-Befund zu verfuegbaren Blueprints oder Container-Grundlagen liegt vor."
    return {
        "step_id": f"{step_id}-recovery-blueprint-list",
        "title": title,
        "goal": goal,
        "done_criteria": done_criteria,
        "risk_level": RiskLevel.SAFE.value,
        "requires_user": False,
        "suggested_tools": next_tools,
        "task_kind": str(current_step_meta.get("task_kind") or "implementation"),
        "objective": str(current_step_meta.get("objective") or ""),
        "step_type": TaskLoopStepType.TOOL_EXECUTION.value,
        "requested_capability": requested_capability_from_tools(next_tools),
        "capability_context": dict(current_step_meta.get("capability_context") or {}),
    }


def build_container_recovery_hint(**kwargs: object) -> dict[str, object]:
    kwargs = dict(kwargs)
    current_step_meta = dict(kwargs.pop("current_step_meta", {}) or {})
    hint = _build_container_recovery_hint(**kwargs)
    if not hint or str(hint.get("recovery_mode") or "").strip().lower() != "replan_with_tools":
        return hint
    next_tools = list(hint.get("next_tools") or [])
    request_family = str(hint.get("request_family") or "generic_container").strip().lower()
    if next_tools == ["blueprint_list"]:
        summary = (
            "Der Container-Start ist noch nicht sauber verifiziert. "
            "Ich schaue mir deshalb zuerst die verfuegbaren Blueprints an und nehme danach den naechsten passenden Schritt."
            if request_family == "python_container"
            else
            "Der Container-Start ist noch nicht sauber verifiziert. "
            "Ich schaue mir deshalb zuerst die verfuegbaren Blueprints an und nehme danach den naechsten passenden Schritt."
        )
    elif next_tools == ["container_list"]:
        summary = (
            "Ich brauche erst einen verifizierten Blick auf den aktuellen Container-Bestand. "
            "Danach kann ich sicher sagen, wie wir weitermachen."
        )
    elif next_tools == ["container_inspect"]:
        summary = (
            "Ich brauche erst den konkreten Zustand des betroffenen Containers. "
            "Danach kann ich den naechsten Schritt sauber ableiten."
        )
    else:
        summary = ""
    if summary:
        hint["summary"] = summary
    hint["replan_step"] = _build_discovery_step(
        current_step_meta=current_step_meta,
        recovery_hint=hint,
    )
    return hint


def apply_container_recovery_replan(
    snapshot,
    *,
    current_step_title: str,
    current_step_meta: dict[str, object],
    recovery_hint: dict[str, object],
):
    recovery_hint = dict(recovery_hint or {})
    if str(recovery_hint.get("recovery_mode") or "").strip().lower() != "replan_with_tools":
        return snapshot
    if not recovery_hint.get("replan_step"):
        recovery_hint["replan_step"] = _build_discovery_step(
            current_step_meta=current_step_meta,
            recovery_hint=recovery_hint,
        )
    return apply_replan_hint(
        snapshot,
        current_step_title=current_step_title,
        current_step_meta=current_step_meta,
        replan_hint=recovery_hint,
    )


__all__ = [
    "apply_container_recovery_replan",
    "build_container_recovery_hint",
]
