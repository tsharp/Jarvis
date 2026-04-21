from __future__ import annotations


def _msg_risk_gate(step_name: str) -> str:
    """Risk gate fired before executing a step (plan-level NEEDS_CONFIRMATION)."""
    return (
        f'\nFür den nächsten Schritt „{step_name}" brauche ich deine Freigabe — '
        "dieser Schritt würde etwas wirklich verändern (z.B. einen Container starten "
        "oder eine Datei schreiben). "
        'Schreib "freigeben" wenn ich weitermachen soll, '
        "oder gib mir zusätzliche Informationen."
    )


def _msg_control_soft_block(detail: str) -> str:
    """Control Layer denied the step but it's not a hard block."""
    msg = "\nIch brauche deine Bestätigung bevor ich weitermache"
    if detail:
        msg += f": {detail}"
    msg += (
        '\n\nSchreib "freigeben" um den Schritt trotzdem auszuführen, '
        "oder sag mir was ich stattdessen tun soll."
    )
    return msg


def _msg_hard_block(detail: str) -> str:
    """Control Layer hard-blocked the step."""
    msg = "\nDieser Schritt wurde blockiert"
    if detail:
        msg += f": {detail}"
    return msg + "\n\nIch kann hier nicht automatisch weitermachen."


def _msg_waiting(detail: str) -> str:
    """Reflection loop decided it needs user input."""
    if detail:
        return f"\n{detail}"
    return "\nIch brauche mehr Informationen um weiterzumachen — bitte sag mir was ich als Nächstes tun soll."


def _msg_verify_before_complete(detail: str) -> str:
    """Loop adds a verification step before final completion."""
    msg = "\nIch prüfe das Ergebnis noch kurz gegen belastbare Hinweise, bevor ich abschließe."
    if detail:
        msg += f"\n{detail}"
    return msg


__all__ = [
    "_msg_control_soft_block",
    "_msg_hard_block",
    "_msg_risk_gate",
    "_msg_verify_before_complete",
    "_msg_waiting",
]
