"""Haupt-Einstiegspunkt der Tool-Utility-Policy.

assess_tool_utility(text, context=None) -> ToolUtilityAssessment

Pipeline:
  1. feature_extraction.extract_features(text)         → f in [0,1]^6
  2. affinity_matrix.score_all(f)                      → raw scores pro Capability
  3. csv_enrichment.enrich_scores(text, raw_scores)    → adjustierte Scores + Rationale
  4. Normalisieren → [0,1]
  5. mode_decision.decide(f, text, context)            → ExecutionMode
  6. Confidence = gap zwischen Top-1 und Top-2 Score
  7. ToolUtilityAssessment zusammenbauen und zurueckgeben
"""
from __future__ import annotations

from .affinity_matrix import compute_scores
from .contracts import CapabilityFamily, ExecutionMode, ToolUtilityAssessment
from .csv_enrichment import enrich_scores
from .feature_extraction import extract_features
from .mode_decision import decide_mode


def assess_tool_utility(
    text: str,
    context: dict | None = None,
) -> ToolUtilityAssessment:
    # Context-Override: force_capability bypasses scoring
    if context and "force_capability" in context:
        cap = CapabilityFamily(context["force_capability"])
        mode, mode_reason = decide_mode(text, {}, context)
        scores = {c.value: (1.0 if c == cap else 0.0) for c in CapabilityFamily}
        return ToolUtilityAssessment(
            capability=cap,
            mode=mode,
            scores=scores,
            confidence=1.0,
            rationale=f"force_capability={cap.value}; mode: {mode_reason}",
        )

    features = extract_features(text)
    scores = compute_scores(features)
    scores, enrich_reasons = enrich_scores(text, scores)

    sorted_caps = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    top_cap_name, top_score = sorted_caps[0]
    second_score = sorted_caps[1][1] if len(sorted_caps) > 1 else 0.0
    confidence = min(1.0, (top_score - second_score) * 2.0)

    cap = CapabilityFamily(top_cap_name)
    mode, mode_reason = decide_mode(text, features, context)

    dominant = max(features, key=features.get)
    rationale_parts = [
        f"capability='{cap.value}' (score {top_score:.3f}, conf {confidence:.2f})",
        f"dominant feature: {dominant} ({features[dominant]:.2f})",
        f"mode: {mode.value} ({mode_reason})",
    ]
    if enrich_reasons:
        rationale_parts.append("boost: " + "; ".join(enrich_reasons))

    return ToolUtilityAssessment(
        capability=cap,
        mode=mode,
        scores=scores,
        confidence=confidence,
        rationale=" | ".join(rationale_parts),
        features=features,
    )
