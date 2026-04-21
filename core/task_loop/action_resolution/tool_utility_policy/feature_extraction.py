"""Feature-Extraktion aus Intent-Text.

Gibt einen Vektor f in [0,1]^N_FEATURES zurueck. Jede Dimension repraesentiert
ein Signal-Merkmal des Intents (temporal, compute, data, persistent, network, system).

Quelle: Keyword-Listen (hartcodiert als Baseline) plus optionale CSV-Anreicherung
aus capability_intent_map.csv und execution_mode_signals.csv.
"""
from __future__ import annotations

import csv
import re
from functools import lru_cache
from pathlib import Path

_CSV = Path(__file__).parents[4] / "CIM-skill_rag" / "capability_intent_map_v2.csv"
FEATURES = ["temporal", "system", "tooling", "document", "integration", "simplicity"]


@lru_cache(maxsize=1)
def _load_patterns() -> list[tuple[re.Pattern, str, float]]:
    patterns: list[tuple[re.Pattern, str, float]] = []
    with open(_CSV, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            try:
                pat = re.compile(row["intent_pattern"], re.IGNORECASE)
                signal = row["feature_signal"]
                conf = float(row["confidence"])
                patterns.append((pat, signal, conf))
            except re.error:
                pass
    return patterns


def extract_features(text: str) -> dict[str, float]:
    features = {f: 0.0 for f in FEATURES}
    for pattern, signal, confidence in _load_patterns():
        if signal in features and pattern.search(text):
            features[signal] = min(1.0, features[signal] + confidence * 0.4)
    return features
