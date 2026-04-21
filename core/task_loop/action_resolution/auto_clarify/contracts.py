from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List


class AutoClarifyMode(str, Enum):
    NO_ACTION = "no_action"
    SELF_DISCOVER = "self_discover"
    SELF_COMPLETE = "self_complete"
    RESOLVE_SECRET = "resolve_secret"
    ASK_USER = "ask_user"
    BLOCK = "block"


class AutoClarifyAutonomyLevel(str, Enum):
    READ_ONLY = "read_only"
    SAFE_WRITE = "safe_write"
    PRIVILEGED = "privileged"


class AutoClarifySource(str, Enum):
    POLICY = "policy"
    DOMAIN_DISPATCH = "domain_dispatch"
    SAFETY_GATES = "safety_gates"
    PARAMETER_COMPLETION = "parameter_completion"
    SECRET_RESOLUTION = "secret_resolution"
    CAPABILITY = "capability"


class AutoClarifyValueSource(str, Enum):
    EXISTING_CONTEXT = "existing_context"
    DISCOVERY = "discovery"
    DEFAULT = "default"
    SECRET = "secret"
    CAPABILITY_POLICY = "capability_policy"
    USER_REPLY = "user_reply"


@dataclass(frozen=True)
class MissingField:
    name: str
    reason: str = ""
    expected_type: str = ""
    required: bool = True
    current_value: Any = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "reason": self.reason,
            "expected_type": self.expected_type,
            "required": bool(self.required),
            "current_value": self.current_value,
            "metadata": dict(self.metadata),
        }


@dataclass(frozen=True)
class ResolvedField:
    name: str
    value: Any
    source: AutoClarifyValueSource
    confidence: float = 1.0
    detail: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "value": self.value,
            "source": self.source.value,
            "confidence": float(self.confidence),
            "detail": self.detail,
            "metadata": dict(self.metadata),
        }


@dataclass(frozen=True)
class AutoClarifyBlocker:
    code: str
    detail: str = ""
    retryable: bool = True
    requires_user: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "code": self.code,
            "detail": self.detail,
            "retryable": bool(self.retryable),
            "requires_user": bool(self.requires_user),
            "metadata": dict(self.metadata),
        }


@dataclass(frozen=True)
class AutoClarifyAction:
    mode: AutoClarifyMode
    title: str = ""
    step_type: str = ""
    capability_family: str = ""
    suggested_tools: List[str] = field(default_factory=list)
    requested_capability: Dict[str, Any] = field(default_factory=dict)
    capability_context: Dict[str, Any] = field(default_factory=dict)
    fields_to_resolve: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "mode": self.mode.value,
            "title": self.title,
            "step_type": self.step_type,
            "capability_family": self.capability_family,
            "suggested_tools": list(self.suggested_tools),
            "requested_capability": dict(self.requested_capability),
            "capability_context": dict(self.capability_context),
            "fields_to_resolve": list(self.fields_to_resolve),
            "metadata": dict(self.metadata),
        }


@dataclass(frozen=True)
class AutoClarifyDecision:
    resolved: bool
    mode: AutoClarifyMode
    autonomy_level: AutoClarifyAutonomyLevel
    source: AutoClarifySource = AutoClarifySource.POLICY
    capability_family: str = ""
    action: AutoClarifyAction | None = None
    missing_fields: List[MissingField] = field(default_factory=list)
    resolved_fields: List[ResolvedField] = field(default_factory=list)
    blockers: List[AutoClarifyBlocker] = field(default_factory=list)
    rationale: List[str] = field(default_factory=list)
    detail: str = ""
    ask_user_message: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "resolved": bool(self.resolved),
            "mode": self.mode.value,
            "autonomy_level": self.autonomy_level.value,
            "source": self.source.value,
            "capability_family": self.capability_family,
            "action": self.action.to_dict() if self.action is not None else None,
            "missing_fields": [item.to_dict() for item in self.missing_fields],
            "resolved_fields": [item.to_dict() for item in self.resolved_fields],
            "blockers": [item.to_dict() for item in self.blockers],
            "rationale": list(self.rationale),
            "detail": self.detail,
            "ask_user_message": self.ask_user_message,
            "metadata": dict(self.metadata),
        }


__all__ = [
    "AutoClarifyAction",
    "AutoClarifyAutonomyLevel",
    "AutoClarifyBlocker",
    "AutoClarifyDecision",
    "AutoClarifyMode",
    "AutoClarifySource",
    "AutoClarifyValueSource",
    "MissingField",
    "ResolvedField",
]
