"""
MemoryResolution — Einzige Wahrheitsquelle fuer Memory-Retrieval-Ergebnis.

Ersetzt die verteilten Stellvertreter:
  needs_memory, memory_keys, memory_used,
  memory_keys_requested/found/not_found, memory_required_but_missing

Wird einmal in build_effective_context() gebaut und unveraendert weitergereicht.
Kein Pfad berechnet required_missing selbst.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List


@dataclass
class MemoryResolution:
    requested_keys: List[str] = field(default_factory=list)
    found_keys: List[str] = field(default_factory=list)
    missing_keys: List[str] = field(default_factory=list)
    required_missing: bool = False

    @classmethod
    def from_context_result(cls, ctx: Any, thinking_plan: Dict) -> "MemoryResolution":
        """Baut MemoryResolution aus ContextResult + Thinking-Plan."""
        requested = list(getattr(ctx, "memory_keys_requested", []))
        found = list(getattr(ctx, "memory_keys_found", []))
        missing = list(getattr(ctx, "memory_keys_not_found", []))
        needs = bool(
            thinking_plan.get("needs_memory") or thinking_plan.get("is_fact_query")
        )
        return cls(
            requested_keys=requested,
            found_keys=found,
            missing_keys=missing,
            required_missing=needs and bool(missing),
        )

    def to_trace(self) -> Dict:
        """Rueckwaertskompatible Trace-Felder fuer bestehende Consumer."""
        return {
            "memory_keys_requested": self.requested_keys,
            "memory_keys_found": self.found_keys,
            "memory_keys_not_found": self.missing_keys,
            "memory_required_but_missing": self.required_missing,
        }
