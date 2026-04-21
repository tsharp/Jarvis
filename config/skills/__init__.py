"""
config.skills
=============
Skill-Management, Secrets & Autosave-Dedupe.

Module:
  registry  → Graph-Reconcile, Key-Mode, Authority, Package-Policy, Discovery,
              Auto-Create, Autosave-Dedupe
  rendering → Kontext-Renderer, Selection-Mode, Top-K, Char-Cap
  secrets   → C8 Secret-Policy: Enforcement, Resolve-Token, Rate-Limit, TTLs

Re-Exports für bequemen Zugriff via `from config.skills import ...`:
"""
from config.skills.registry import (
    get_skill_graph_reconcile,
    get_skill_key_mode,
    get_skill_control_authority,
    get_skill_package_install_mode,
    get_skill_discovery_enable,
    get_skill_auto_create_on_low_risk,
    get_autosave_dedupe_enable,
    get_autosave_dedupe_window_s,
    get_autosave_dedupe_max_entries,
)

from config.skills.rendering import (
    get_skill_context_renderer,
    get_skill_selection_mode,
    get_skill_selection_top_k,
    get_skill_selection_char_cap,
)

from config.skills.secrets import (
    get_skill_secret_enforcement,
    get_secret_resolve_token,
    get_secret_rate_limit,
    get_secret_resolve_miss_ttl_s,
    get_secret_resolve_not_found_ttl_s,
)

__all__ = [
    # registry
    "get_skill_graph_reconcile", "get_skill_key_mode", "get_skill_control_authority",
    "get_skill_package_install_mode", "get_skill_discovery_enable",
    "get_skill_auto_create_on_low_risk", "get_autosave_dedupe_enable",
    "get_autosave_dedupe_window_s", "get_autosave_dedupe_max_entries",
    # rendering
    "get_skill_context_renderer", "get_skill_selection_mode",
    "get_skill_selection_top_k", "get_skill_selection_char_cap",
    # secrets
    "get_skill_secret_enforcement", "get_secret_resolve_token",
    "get_secret_rate_limit", "get_secret_resolve_miss_ttl_s",
    "get_secret_resolve_not_found_ttl_s",
]
