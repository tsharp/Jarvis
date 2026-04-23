"""Contracts fuer den gemeinsamen Work Context."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from types import MappingProxyType
from typing import Any, Dict, Iterable, Mapping, Optional, Sequence, Tuple


def _normalize_text(value: Any, *, max_len: int = 400) -> str:
    text = " ".join(str(value or "").strip().split())
    if len(text) > max_len:
        return text[:max_len].rstrip()
    return text


def _normalize_string_tuple(
    values: Iterable[Any],
    *,
    max_items: int = 24,
    max_len: int = 200,
) -> Tuple[str, ...]:
    out = []
    seen = set()
    for raw in values or []:
        item = _normalize_text(raw, max_len=max_len)
        if not item or item in seen:
            continue
        seen.add(item)
        out.append(item)
        if len(out) >= max(1, int(max_items or 24)):
            break
    return tuple(out)


def _sanitize_mapping(raw: Any, *, max_items: int = 32) -> Mapping[str, Any]:
    if not isinstance(raw, dict):
        return MappingProxyType({})
    cleaned: Dict[str, Any] = {}
    for key, value in raw.items():
        name = _normalize_text(key, max_len=80)
        if not name:
            continue
        cleaned[name] = value
        if len(cleaned) >= max(1, int(max_items or 32)):
            break
    return MappingProxyType(cleaned)


class WorkContextStatus(str, Enum):
    UNKNOWN = "unknown"
    ACTIVE = "active"
    WAITING = "waiting"
    BLOCKED = "blocked"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class WorkContextSource(str, Enum):
    TASK_LOOP = "task_loop"
    WORKSPACE_EVENTS = "workspace_events"
    COMPACT_CONTEXT = "compact_context"
    CHAT_MEMORY = "chat_memory"
    ROLLING_SUMMARY = "rolling_summary"
    INFERENCE = "inference"
    MIXED = "mixed"


@dataclass(frozen=True)
class WorkContextFact:
    key: str
    value: str
    source: WorkContextSource = WorkContextSource.INFERENCE
    confidence: float = 1.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "key": _normalize_text(self.key, max_len=80),
            "value": _normalize_text(self.value, max_len=240),
            "source": self.source.value,
            "confidence": max(0.0, min(1.0, float(self.confidence))),
        }


def _normalize_fact_tuple(
    values: Sequence[Any],
    *,
    max_items: int = 24,
) -> Tuple[WorkContextFact, ...]:
    out = []
    seen = set()
    for raw in values or []:
        if isinstance(raw, WorkContextFact):
            fact = raw
        elif isinstance(raw, dict):
            key = _normalize_text(raw.get("key"), max_len=80)
            value = _normalize_text(raw.get("value"), max_len=240)
            if not key or not value:
                continue
            raw_source = str(raw.get("source") or "").strip().lower()
            try:
                source = WorkContextSource(raw_source) if raw_source else WorkContextSource.INFERENCE
            except ValueError:
                source = WorkContextSource.INFERENCE
            try:
                confidence = float(raw.get("confidence", 1.0))
            except Exception:
                confidence = 1.0
            fact = WorkContextFact(
                key=key,
                value=value,
                source=source,
                confidence=max(0.0, min(1.0, confidence)),
            )
        else:
            continue
        dedupe_key = (fact.key, fact.value)
        if dedupe_key in seen:
            continue
        seen.add(dedupe_key)
        out.append(fact)
        if len(out) >= max(1, int(max_items or 24)):
            break
    return tuple(out)


@dataclass(frozen=True)
class WorkContext:
    conversation_id: str
    topic: str = ""
    status: WorkContextStatus = WorkContextStatus.UNKNOWN
    source: WorkContextSource = WorkContextSource.INFERENCE
    updated_at: str = ""
    last_step: str = ""
    next_step: str = ""
    blocker: str = ""
    verified_facts: Tuple[WorkContextFact, ...] = field(default_factory=tuple)
    missing_facts: Tuple[str, ...] = field(default_factory=tuple)
    capability_context: Mapping[str, Any] = field(default_factory=lambda: MappingProxyType({}))
    metadata: Mapping[str, Any] = field(default_factory=lambda: MappingProxyType({}))

    def __post_init__(self) -> None:
        object.__setattr__(self, "conversation_id", _normalize_text(self.conversation_id, max_len=120))
        object.__setattr__(self, "topic", _normalize_text(self.topic, max_len=240))
        object.__setattr__(self, "updated_at", _normalize_text(self.updated_at, max_len=64))
        object.__setattr__(self, "last_step", _normalize_text(self.last_step, max_len=240))
        object.__setattr__(self, "next_step", _normalize_text(self.next_step, max_len=240))
        object.__setattr__(self, "blocker", _normalize_text(self.blocker, max_len=240))
        object.__setattr__(self, "verified_facts", _normalize_fact_tuple(self.verified_facts))
        object.__setattr__(self, "missing_facts", _normalize_string_tuple(self.missing_facts))
        object.__setattr__(self, "capability_context", _sanitize_mapping(self.capability_context))
        object.__setattr__(self, "metadata", _sanitize_mapping(self.metadata))

    @property
    def is_terminal(self) -> bool:
        return self.status in {WorkContextStatus.COMPLETED, WorkContextStatus.CANCELLED}

    @property
    def is_open(self) -> bool:
        return self.status in {
            WorkContextStatus.ACTIVE,
            WorkContextStatus.WAITING,
            WorkContextStatus.BLOCKED,
        }

    @property
    def has_blocker(self) -> bool:
        return bool(self.blocker)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "conversation_id": self.conversation_id,
            "topic": self.topic,
            "status": self.status.value,
            "source": self.source.value,
            "updated_at": self.updated_at,
            "last_step": self.last_step,
            "next_step": self.next_step,
            "blocker": self.blocker,
            "verified_facts": [item.to_dict() for item in self.verified_facts],
            "missing_facts": list(self.missing_facts),
            "capability_context": dict(self.capability_context),
            "metadata": dict(self.metadata),
        }


@dataclass(frozen=True)
class WorkContextUpdate:
    topic: Optional[str] = None
    status: Optional[WorkContextStatus] = None
    source: Optional[WorkContextSource] = None
    updated_at: Optional[str] = None
    last_step: Optional[str] = None
    next_step: Optional[str] = None
    blocker: Optional[str] = None
    verified_facts: Tuple[WorkContextFact, ...] = field(default_factory=tuple)
    missing_facts: Tuple[str, ...] = field(default_factory=tuple)
    capability_context: Mapping[str, Any] = field(default_factory=lambda: MappingProxyType({}))
    metadata: Mapping[str, Any] = field(default_factory=lambda: MappingProxyType({}))

    def __post_init__(self) -> None:
        if self.topic is not None:
            object.__setattr__(self, "topic", _normalize_text(self.topic, max_len=240))
        if self.updated_at is not None:
            object.__setattr__(self, "updated_at", _normalize_text(self.updated_at, max_len=64))
        if self.last_step is not None:
            object.__setattr__(self, "last_step", _normalize_text(self.last_step, max_len=240))
        if self.next_step is not None:
            object.__setattr__(self, "next_step", _normalize_text(self.next_step, max_len=240))
        if self.blocker is not None:
            object.__setattr__(self, "blocker", _normalize_text(self.blocker, max_len=240))
        object.__setattr__(self, "verified_facts", _normalize_fact_tuple(self.verified_facts))
        object.__setattr__(self, "missing_facts", _normalize_string_tuple(self.missing_facts))
        object.__setattr__(self, "capability_context", _sanitize_mapping(self.capability_context))
        object.__setattr__(self, "metadata", _sanitize_mapping(self.metadata))

    def to_dict(self) -> Dict[str, Any]:
        out: Dict[str, Any] = {}
        if self.topic is not None:
            out["topic"] = self.topic
        if self.status is not None:
            out["status"] = self.status.value
        if self.source is not None:
            out["source"] = self.source.value
        if self.updated_at is not None:
            out["updated_at"] = self.updated_at
        if self.last_step is not None:
            out["last_step"] = self.last_step
        if self.next_step is not None:
            out["next_step"] = self.next_step
        if self.blocker is not None:
            out["blocker"] = self.blocker
        if self.verified_facts:
            out["verified_facts"] = [item.to_dict() for item in self.verified_facts]
        if self.missing_facts:
            out["missing_facts"] = list(self.missing_facts)
        if self.capability_context:
            out["capability_context"] = dict(self.capability_context)
        if self.metadata:
            out["metadata"] = dict(self.metadata)
        return out


__all__ = [
    "WorkContext",
    "WorkContextFact",
    "WorkContextSource",
    "WorkContextStatus",
    "WorkContextUpdate",
]
