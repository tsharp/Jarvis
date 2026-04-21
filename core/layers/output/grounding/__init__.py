"""
core.layers.output.grounding
==============================
Grounding-Engine für den Output Layer — 6 Module:

  state     → Zentraler Grounding-State-Container (set/get flags)
  evidence  → Evidence sammeln, prüfen, zusammenfassen
  fallback  → Generische Fallback-Antworten bei fehlender Evidence
  precheck  → Vor der Generierung: Evidence-Check + frühe Fallbacks
  postcheck → Nach der Generierung: Kontrakt- und Novelty-Prüfung
  stream    → Stream-Puffer-Steuerung für den Postcheck
"""
from core.layers.output.grounding.state import (
    runtime_grounding_state,
    set_runtime_grounding_value,
)
from core.layers.output.grounding.evidence import (
    collect_grounding_evidence,
    evidence_item_has_extractable_content,
    summarize_evidence_item,
    collect_evidence_text_parts,
)
from core.layers.output.grounding.fallback import (
    build_grounding_fallback,
    build_tool_failure_fallback,
)
from core.layers.output.grounding.precheck import grounding_precheck
from core.layers.output.grounding.postcheck import (
    grounding_postcheck,
    attempt_grounding_repair_once,
)
from core.layers.output.grounding.stream import (
    resolve_stream_postcheck_mode,
    should_buffer_stream_postcheck,
    stream_postcheck_enabled,
)

__all__ = [
    "runtime_grounding_state", "set_runtime_grounding_value",
    "collect_grounding_evidence", "evidence_item_has_extractable_content",
    "summarize_evidence_item", "collect_evidence_text_parts",
    "build_grounding_fallback", "build_tool_failure_fallback",
    "grounding_precheck",
    "grounding_postcheck", "attempt_grounding_repair_once",
    "resolve_stream_postcheck_mode", "should_buffer_stream_postcheck",
    "stream_postcheck_enabled",
]
