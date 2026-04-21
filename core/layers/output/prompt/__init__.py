"""
core.layers.output.prompt
==========================
Prompt-Aufbau für den Output-Layer — 3 Module:

  budget         → hard_cap + soft_target Berechnung
  tool_injection → Tool-Liste für System-Prompt
  system_prompt  → System-Prompt + Messages-Array-Konstruktion
"""
from core.layers.output.prompt.budget import (  # noqa: F401
    normalize_length_hint,
    resolve_output_budgets,
)
from core.layers.output.prompt.tool_injection import (  # noqa: F401
    extract_selected_tool_names,
    resolve_tools_for_prompt,
)
from core.layers.output.prompt.system_prompt import (  # noqa: F401
    build_system_prompt,
    build_messages,
    build_full_prompt,
)

__all__ = [
    "normalize_length_hint", "resolve_output_budgets",
    "extract_selected_tool_names", "resolve_tools_for_prompt",
    "build_system_prompt", "build_messages", "build_full_prompt",
]
