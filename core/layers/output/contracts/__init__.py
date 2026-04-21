"""
core.layers.output.contracts
==============================
Domain-Kontrakte für Output Layer.

  skill_catalog/  → Skill-Catalog-Kontrakt (trace, snapshot, evaluation)
  container.py    → Container-Query-Kontrakt (inventory, blueprint, binding)
"""
from core.layers.output.contracts.skill_catalog import (
    is_skill_catalog_context_plan,
    skill_catalog_trace_state,
    update_skill_catalog_trace,
    collect_skill_catalog_fact_lines,
    extract_skill_catalog_snapshot,
    build_skill_catalog_prompt_rules,
    locate_skill_catalog_sections,
    evaluate_skill_catalog_semantic_leakage,
    build_skill_catalog_safe_fallback,
)
from core.layers.output.contracts.container import (
    get_container_query_policy,
    is_container_query_contract_plan,
    build_container_prompt_rules,
    extract_container_contract_snapshot,
    build_container_safe_fallback,
    evaluate_container_contract_leakage,
)

__all__ = [
    # skill_catalog
    "is_skill_catalog_context_plan",
    "skill_catalog_trace_state",
    "update_skill_catalog_trace",
    "collect_skill_catalog_fact_lines",
    "extract_skill_catalog_snapshot",
    "build_skill_catalog_prompt_rules",
    "locate_skill_catalog_sections",
    "evaluate_skill_catalog_semantic_leakage",
    "build_skill_catalog_safe_fallback",
    # container
    "get_container_query_policy",
    "is_container_query_contract_plan",
    "build_container_prompt_rules",
    "extract_container_contract_snapshot",
    "build_container_safe_fallback",
    "evaluate_container_contract_leakage",
]
