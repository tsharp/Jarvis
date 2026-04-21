"""Datentypen fuer die Tool-Utility-Policy.

Definiert:
- CapabilityFamily  — welche Capability-Klasse (container, skill, cron, mcp, direct)
- ExecutionMode     — one_shot vs. persistent
- ToolUtilityAssessment — Ergebnis einer assess_tool_utility()-Bewertung
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class CapabilityFamily(str, Enum):
    container = "container"
    skill = "skill"
    cron = "cron"
    mcp = "mcp"
    direct = "direct"


class ExecutionMode(str, Enum):
    one_shot = "one_shot"
    persistent = "persistent"


@dataclass
class ToolUtilityAssessment:
    capability: CapabilityFamily
    mode: ExecutionMode
    scores: dict[str, float]
    confidence: float
    rationale: str
    features: dict[str, float] = field(default_factory=dict)
