"""
core.layers.output
==================
Output Layer — aufgesplittet in 5 Sub-Packages.

Sub-Packages:
  analysis    → Text-Analyse: numeric, qualitative, evidence_summary
  grounding   → Grounding-Engine: evidence, state, checks, fallback, stream
  contracts   → Domain-Kontrakte: skill_catalog, container
  prompt      → Prompt-Bausteine: system_prompt, budget, tool_injection, rules
  generation  → LLM-Generierung: async_stream, sync_stream, tool_check

Die OutputLayer-Klasse liegt in core/layers/output/layer.py
bis zur vollständigen Mixin-Migration.
"""
from core.layers.output.layer import OutputLayer  # noqa: F401
