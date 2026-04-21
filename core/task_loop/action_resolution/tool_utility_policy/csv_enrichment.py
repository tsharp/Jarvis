"""CSV-gestuetzte Score-Anreicherung.

Laedt (gecacht) folgende Dateien aus CIM-skill_rag/:

  capability_intent_map.csv     — intent_pattern → capability_family + confidence
                                  (neu, von ChatGPT generiert)

  execution_mode_signals.csv    — signal_phrase → one_shot|persistent + confidence
                                  (neu, von ChatGPT generiert)

  capability_feature_weights.csv — capability × feature → weight
                                  (optional, ersetzt Fallback-Matrix in affinity_matrix.py)

  intent_category_map.csv       — intent_pattern → skill-Kategorie + confidence
                                  (bestehend, boosted SKILL-Score)

  skill_templates.csv           — intent_keywords → template-Kategorie
                                  (bestehend, sekundaeres SKILL-Signal)

Alle Ladeoperationen sind lru_cache-gesichert.
"""
from __future__ import annotations

import csv
import re
from functools import lru_cache
from pathlib import Path

_RAG = Path(__file__).parents[4] / "CIM-skill_rag"
_CATEGORY_CSV = _RAG / "intent_category_map.csv"
_TEMPLATES_CSV = _RAG / "skill_templates.csv"

_SKILL_BOOST_CATEGORY = 0.12
_SKILL_BOOST_TEMPLATE = 0.08


@lru_cache(maxsize=1)
def _load_category_patterns() -> list[tuple[re.Pattern, float]]:
    patterns: list[tuple[re.Pattern, float]] = []
    with open(_CATEGORY_CSV, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            try:
                pat = re.compile(row["intent_pattern"], re.IGNORECASE)
                patterns.append((pat, float(row["confidence"])))
            except re.error:
                pass
    return patterns


@lru_cache(maxsize=1)
def _load_template_keywords() -> list[re.Pattern]:
    patterns: list[re.Pattern] = []
    with open(_TEMPLATES_CSV, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            kw = row.get("intent_keywords", "").strip()
            if kw:
                try:
                    patterns.append(re.compile(kw, re.IGNORECASE))
                except re.error:
                    pass
    return patterns


def enrich_scores(text: str, scores: dict[str, float]) -> tuple[dict[str, float], list[str]]:
    """Boost skill-Score via Sekundaer-CSVs; re-normalisiert danach."""
    boost = 0.0
    reasons: list[str] = []

    for pat, conf in _load_category_patterns():
        if pat.search(text):
            boost += _SKILL_BOOST_CATEGORY * conf
            reasons.append(f"category pattern match (conf {conf:.2f})")
            break

    for pat in _load_template_keywords():
        if pat.search(text):
            boost += _SKILL_BOOST_TEMPLATE
            reasons.append("skill template keyword match")
            break

    if boost == 0.0:
        return scores, reasons

    enriched = dict(scores)
    enriched["skill"] = min(1.0, enriched.get("skill", 0.0) + boost)
    total = sum(enriched.values()) or 1.0
    normalized = {cap: v / total for cap, v in enriched.items()}
    return normalized, reasons
