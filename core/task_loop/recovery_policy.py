from __future__ import annotations

from typing import Any, Dict

from core.task_loop.capabilities.container.recovery import (
    CONTAINER_INSPECT_STEP_TITLE,
    DISCOVERY_STEP_TITLE,
    RECOVERY_ARTIFACT_TYPE,
    RUNTIME_DISCOVERY_STEP_TITLE,
    extract_container_recovery_hint,
)
from core.task_loop.capabilities.container.replan_policy import (
    apply_container_recovery_replan,
)
from core.task_loop.contracts import TaskLoopSnapshot
from core.task_loop.replan_engine import apply_replan_hint

# Kanonische Titel von Recovery-/Discovery-Schritten, die der Replan-Engine selbst eingefuegt hat.
# Wenn der gerade abgeschlossene Schritt einen dieser Titel traegt, ist er selbst ein Recovery-Step —
# ein erneuter Replan wuerde einen Ping-Pong-Loop erzeugen.
_RECOVERY_STEP_TITLES: frozenset[str] = frozenset(
    {
        DISCOVERY_STEP_TITLE,
        RUNTIME_DISCOVERY_STEP_TITLE,
        CONTAINER_INSPECT_STEP_TITLE,
    }
)


def _is_recovery_step(step_title: str) -> bool:
    """True wenn step_title selbst ein eingefuegter Recovery-/Discovery-Schritt ist."""
    title = step_title.strip()
    if title in _RECOVERY_STEP_TITLES:
        return True
    # apply_replan_hint haengt " (Recovery)" an, wenn der Titel bereits im Plan war
    if title.endswith(" (Recovery)"):
        base = title[: -len(" (Recovery)")].strip()
        if base in _RECOVERY_STEP_TITLES:
            return True
    return False


def derive_recovery_hint(verified_artifacts: list[dict[str, Any]] | None) -> Dict[str, Any]:
    container_hint = extract_container_recovery_hint(verified_artifacts)
    if container_hint:
        return container_hint
    return {}


def maybe_apply_recovery_replan(
    snapshot: TaskLoopSnapshot,
    *,
    current_step_title: str,
    current_step_meta: Dict[str, Any],
    recovery_hint: Dict[str, Any] | None,
) -> TaskLoopSnapshot:
    hint = dict(recovery_hint or {})
    if not hint:
        return snapshot

    # Guard 1: wenn der gerade abgeschlossene Schritt selbst ein Recovery-/Discovery-Step war,
    # keinen weiteren Replan einfuegen — die alten verified_artifacts enthalten noch den
    # urspruenglichen Hint und wuerden sonst denselben Step endlos neu einplanen.
    if _is_recovery_step(current_step_title):
        return snapshot

    # Guard 2: wenn eine "(Recovery)"-Variante des replan_step_title bereits in completed_steps
    # liegt, wurde ein explizit eingefuegter Recovery-Step bereits erfolgreich ausgefuehrt.
    # Denselben Recovery-Step nochmal einzufuegen wuerde einen Ping-Pong-Loop erzeugen, weil
    # der nachfolgende Original-Step (z.B. "Container-Anfrage") denselben Hint erneut generiert.
    #
    # Wichtig: nur die "(Recovery)"-Variante pruefen — der exakte Originaltitel darf noch einen
    # Recovery-Versuch ausloesen. Das passiert, wenn der Titel bereits im initialen Plan war
    # (apply_replan_hint wuerde dann die "(Recovery)"-Variante einfuegen, nicht den Originaltitel).
    replan_title = str(hint.get("replan_step_title") or "").strip()
    if replan_title:
        recovery_prefix = f"{replan_title} (Recovery"
        for done in list(snapshot.completed_steps or []):
            if done.startswith(recovery_prefix):
                return snapshot

    artifact_type = str(hint.get("artifact_type") or "").strip().lower()
    if artifact_type == RECOVERY_ARTIFACT_TYPE:
        return apply_container_recovery_replan(
            snapshot,
            current_step_title=current_step_title,
            current_step_meta=current_step_meta,
            recovery_hint=hint,
        )

    if str(hint.get("recovery_mode") or "").strip().lower() != "replan_with_tools":
        return snapshot

    return apply_replan_hint(
        snapshot,
        current_step_title=current_step_title,
        current_step_meta=current_step_meta,
        replan_hint=hint,
    )


__all__ = ["derive_recovery_hint", "maybe_apply_recovery_replan"]
