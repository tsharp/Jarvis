"""
core.layers.output.contracts.skill_catalog
===========================================
Skill-Catalog-Kontrakt — 3 Module:

  trace       → Erkennung + Trace-State
  snapshot    → Evidence-Parsing
  evaluation  → Prompt-Regeln, Postcheck, Safe-Fallback
"""
from core.layers.output.contracts.skill_catalog.trace import (
    is_skill_catalog_context_plan,
    skill_catalog_trace_state,
    update_skill_catalog_trace,
)
from core.layers.output.contracts.skill_catalog.snapshot import (
    collect_skill_catalog_fact_lines,
    extract_skill_catalog_snapshot,
)
from core.layers.output.contracts.skill_catalog.evaluation import (
    build_skill_catalog_prompt_rules,
    locate_skill_catalog_sections,
    evaluate_skill_catalog_semantic_leakage,
    build_skill_catalog_safe_fallback,
)

__all__ = [
    "is_skill_catalog_context_plan",
    "skill_catalog_trace_state",
    "update_skill_catalog_trace",
    "collect_skill_catalog_fact_lines",
    "extract_skill_catalog_snapshot",
    "build_skill_catalog_prompt_rules",
    "locate_skill_catalog_sections",
    "evaluate_skill_catalog_semantic_leakage",
    "build_skill_catalog_safe_fallback",
]
