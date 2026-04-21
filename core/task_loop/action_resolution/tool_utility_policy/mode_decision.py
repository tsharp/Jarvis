"""Execution-Mode-Entscheidung: one_shot vs. persistent.

Nutzt:
  1. Feature-Vektor (temporal + persistent Dimensionen als Primaersignal)
  2. execution_mode_signals.csv fuer phrasenbasierte Ueberschreibung
  3. Context-Override (z.B. {"force_mode": "persistent"})

Gibt ExecutionMode zurueck plus Rationale-Eintraege.
"""
from __future__ import annotations

import csv
from functools import lru_cache
from pathlib import Path

from .contracts import ExecutionMode

_CSV = Path(__file__).parents[4] / "CIM-skill_rag" / "execution_mode_signals_v2.csv"


@lru_cache(maxsize=1)
def _load_signals() -> list[tuple[str, str, float]]:
    signals: list[tuple[str, str, float]] = []
    with open(_CSV, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            signals.append((row["signal_phrase"].lower(), row["mode"], float(row["confidence"])))
    return signals


def decide_mode(
    text: str,
    features: dict[str, float],
    context: dict | None = None,
) -> tuple[ExecutionMode, str]:
    if context and "force_mode" in context:
        mode = ExecutionMode(context["force_mode"])
        return mode, f"force_mode={mode.value}"

    text_lower = text.lower()
    best_mode: str | None = None
    best_conf = 0.0
    best_phrase = ""
    for phrase, mode, conf in _load_signals():
        if phrase in text_lower and conf > best_conf:
            best_mode = mode
            best_conf = conf
            best_phrase = phrase

    if best_mode:
        return ExecutionMode(best_mode), f"phrase match: '{best_phrase}' (conf {best_conf:.2f})"

    if features.get("temporal", 0.0) >= 0.3:
        return ExecutionMode.persistent, "temporal feature >= 0.3"

    return ExecutionMode.one_shot, "fallback: one_shot"
