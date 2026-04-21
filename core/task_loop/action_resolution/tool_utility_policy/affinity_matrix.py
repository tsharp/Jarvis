"""Affinity-Matrix M und Score-Berechnung.

M in R^(capabilities x features). score(cap) = M[cap] . f

Die Matrix wird bevorzugt aus capability_feature_weights.csv geladen.
Faellt die Datei weg, greift eine hartcodierte Fallback-Matrix.

score(cap) ergibt den rohen Affinitaets-Score vor Normalisierung und
CSV-Enrichment.
"""
from __future__ import annotations

import csv
from functools import lru_cache
from pathlib import Path

from .contracts import CapabilityFamily

_CSV = Path(__file__).parents[4] / "CIM-skill_rag" / "capability_feature_weights_v2.csv"


@lru_cache(maxsize=1)
def _load_matrix() -> dict[str, dict[str, float]]:
    matrix: dict[str, dict[str, float]] = {cap.value: {} for cap in CapabilityFamily}
    with open(_CSV, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            cap = row["capability_family"]
            if cap in matrix:
                matrix[cap][row["feature_name"]] = float(row["weight"])
    return matrix


def compute_scores(features: dict[str, float]) -> dict[str, float]:
    matrix = _load_matrix()
    raw = {
        cap: sum(weights.get(feat, 0.0) * val for feat, val in features.items())
        for cap, weights in matrix.items()
    }
    total = sum(raw.values()) or 1.0
    return {cap: s / total for cap, s in raw.items()}
