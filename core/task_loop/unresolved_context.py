from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from core.task_loop.contracts import TaskLoopSnapshot, TaskLoopState
from core.work_context.normalization import (
    build_terminal_task_loop_projection,
    build_terminal_task_loop_work_context,
)
from core.work_context.selectors import (
    has_open_work_context,
    is_actionable_unresolved_followup,
    is_explanatory_unresolved_followup,
    visible_next_step,
)


@dataclass(frozen=True)
class UnresolvedTaskContext:
    conversation_id: str
    source_state: str
    task_topic: str
    blocker: str
    next_step: str
    capability_context: Dict[str, Any]
    selected_blueprint: Dict[str, str]
    discovered_blueprints: List[Dict[str, Any]]
    next_tools: List[str]

def maybe_build_unresolved_task_context(snapshot: Optional[TaskLoopSnapshot]) -> Optional[UnresolvedTaskContext]:
    projection = build_terminal_task_loop_projection(snapshot)
    if projection is None:
        return None

    return UnresolvedTaskContext(
        conversation_id=projection.conversation_id,
        source_state=projection.source_state,
        task_topic=projection.topic,
        blocker=projection.blocker,
        next_step=projection.next_step,
        capability_context=dict(projection.capability_context or {}),
        selected_blueprint=dict(projection.selected_blueprint or {}),
        discovered_blueprints=[row for row in projection.discovered_blueprints if isinstance(row, dict)],
        next_tools=list(projection.next_tools or []),
    )


def _missing_items(ctx: UnresolvedTaskContext) -> List[str]:
    items: List[str] = []
    request_family = str((ctx.capability_context or {}).get("request_family") or "").strip().lower()
    if request_family == "python_container":
        python_rows = [
            row
            for row in ctx.discovered_blueprints
            if "python"
            in " ".join(
                str(row.get(key) or "")
                for key in ("id", "blueprint_id", "name", "description")
            ).lower()
        ]
        if not python_rows:
            items.append("ein verifizierter passender Python-Blueprint")
        elif not ctx.selected_blueprint:
            items.append("eine eindeutige Python-Blueprint-Auswahl")
    elif ctx.discovered_blueprints and not ctx.selected_blueprint:
        items.append("eine eindeutige Blueprint-Auswahl")
    if ctx.blocker:
        items.append(f"ein geklaerter Blockierungsgrund ({ctx.blocker})")
    return items


def build_unresolved_task_response(ctx: UnresolvedTaskContext) -> str:
    work_context = build_terminal_task_loop_work_context(
        conversation_id=ctx.conversation_id,
        topic=ctx.task_topic,
        source_state=ctx.source_state,
        next_step=ctx.next_step,
        blocker=ctx.blocker,
        capability_context=ctx.capability_context,
        selected_blueprint=ctx.selected_blueprint,
        discovered_blueprints=ctx.discovered_blueprints,
        next_tools=ctx.next_tools,
    )
    lines: List[str] = []
    topic = ctx.task_topic or "die offene Aufgabe"
    lines.append(f"Offen ist aktuell noch: {topic}.")

    verified: List[str] = []
    if ctx.selected_blueprint:
        verified.append(
            "ausgewaehlter Blueprint "
            f"{str(ctx.selected_blueprint.get('label') or ctx.selected_blueprint.get('blueprint_id') or '').strip()}"
        )
    elif ctx.discovered_blueprints:
        labels = []
        for row in ctx.discovered_blueprints[:4]:
            label = str(row.get("name") or row.get("blueprint_id") or row.get("id") or "").strip()
            if label:
                labels.append(label)
        if labels:
            verified.append(f"verifizierte Blueprints: {', '.join(labels)}")

    if verified:
        lines.append("Verifiziert: " + "; ".join(verified) + ".")

    missing = _missing_items(ctx)
    if missing:
        lines.append("Es fehlt noch: " + "; ".join(missing) + ".")
    elif ctx.blocker:
        lines.append(f"Blocker: {ctx.blocker}.")

    next_step = visible_next_step(work_context)
    if next_step and has_open_work_context(work_context):
        lines.append(f"Naechster sinnvoller Schritt: {next_step}.")
    elif ctx.next_tools:
        lines.append("Naechster sinnvoller Schritt: " + ", ".join(ctx.next_tools) + ".")
    return "\n".join(lines)


def build_seeded_followup_user_text(user_text: str, ctx: UnresolvedTaskContext) -> str:
    topic = str(ctx.task_topic or "").strip() or "Offene Aufgabe weiterbearbeiten"
    next_step = str(ctx.next_step or "").strip()
    followup = " ".join(str(user_text or "").split()).strip()
    parts = [topic]
    if next_step:
        parts.append(f"Naechster sinnvoller Schritt: {next_step}")
    if followup and followup.casefold() not in topic.casefold():
        parts.append(f"Folgeauftrag: {followup}")
    return ". ".join(part for part in parts if part).strip()


def enrich_followup_thinking_plan(
    thinking_plan: Optional[Dict[str, Any]],
    ctx: UnresolvedTaskContext,
) -> Dict[str, Any]:
    plan = dict(thinking_plan) if isinstance(thinking_plan, dict) else {}
    current_intent = str(plan.get("intent") or "").strip().lower()
    if not current_intent or current_intent == "unknown" or "unklar" in current_intent:
        plan["intent"] = ctx.task_topic or plan.get("intent") or ""
    if ctx.capability_context:
        existing = dict(plan.get("_container_capability_context") or {})
        merged = dict(existing)
        merged.update(ctx.capability_context)
        existing_known = dict(existing.get("known_fields") or {})
        merged_known = dict(ctx.capability_context.get("known_fields") or {})
        existing_known.update(merged_known)
        if existing_known:
            merged["known_fields"] = existing_known
        plan["_container_capability_context"] = merged
    if ctx.next_tools and not list(plan.get("suggested_tools") or []):
        plan["suggested_tools"] = list(ctx.next_tools)
    plan["_unresolved_task_context"] = {
        "task_topic": ctx.task_topic,
        "blocker": ctx.blocker,
        "next_step": ctx.next_step,
        "next_tools": list(ctx.next_tools),
        "source_state": ctx.source_state,
    }
    return plan


__all__ = [
    "UnresolvedTaskContext",
    "build_seeded_followup_user_text",
    "build_unresolved_task_response",
    "enrich_followup_thinking_plan",
    "is_actionable_unresolved_followup",
    "is_explanatory_unresolved_followup",
    "maybe_build_unresolved_task_context",
]
