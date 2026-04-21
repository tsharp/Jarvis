from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List


class ActionResolutionMode(str, Enum):
    EXECUTE_EXISTING_STEP = "execute_existing_step"
    INSERT_DISCOVERY_STEP = "insert_discovery_step"
    INSERT_VERIFICATION_STEP = "insert_verification_step"
    REPLAN_WITH_ACTION = "replan_with_action"
    ASK_USER = "ask_user"
    BLOCK = "block"


class ActionResolutionSource(str, Enum):
    GENERIC = "generic"
    READ_FIRST_POLICY = "read_first_policy"
    AUTO_CLARIFY_POLICY = "auto_clarify_policy"
    RECOVERY_RESOLUTION = "recovery_resolution"
    DOMAIN_DISPATCH = "domain_dispatch"
    CAPABILITY = "capability"


@dataclass(frozen=True)
class ResolvedLoopAction:
    mode: ActionResolutionMode
    title: str = ""
    step_type: str = ""
    suggested_tools: List[str] = field(default_factory=list)
    requested_capability: Dict[str, Any] = field(default_factory=dict)
    capability_context: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "mode": self.mode.value,
            "title": self.title,
            "step_type": self.step_type,
            "suggested_tools": list(self.suggested_tools),
            "requested_capability": dict(self.requested_capability),
            "capability_context": dict(self.capability_context),
            "metadata": dict(self.metadata),
        }


@dataclass(frozen=True)
class ActionResolutionDecision:
    resolved: bool
    action: ResolvedLoopAction | None = None
    source: ActionResolutionSource = ActionResolutionSource.GENERIC
    rationale: List[str] = field(default_factory=list)
    blockers: List[str] = field(default_factory=list)
    detail: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "resolved": bool(self.resolved),
            "action": self.action.to_dict() if self.action is not None else None,
            "source": self.source.value,
            "rationale": list(self.rationale),
            "blockers": list(self.blockers),
            "detail": self.detail,
        }


__all__ = [
    "ActionResolutionDecision",
    "ActionResolutionMode",
    "ActionResolutionSource",
    "ResolvedLoopAction",
]
