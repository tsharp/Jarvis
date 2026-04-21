"""Tool-Utility-Policy: Capability-Routing fuer den Task-Loop.

Entscheidet bei einem Intent, welche Capability-Family genutzt werden soll
(container, skill, cron, mcp, direct) und ob der Auftrag one_shot oder
persistent ausgefuehrt werden soll.

Einstiegspunkt: assess_tool_utility(text, context=None) -> ToolUtilityAssessment
"""

from .contracts import CapabilityFamily, ExecutionMode, ToolUtilityAssessment
from .policy import assess_tool_utility

__all__ = [
    "assess_tool_utility",
    "ToolUtilityAssessment",
    "CapabilityFamily",
    "ExecutionMode",
]
