"""Dispatch auto-clarify requests into capability-specific handlers."""

from __future__ import annotations

from typing import Any, Dict

from core.task_loop.action_resolution.auto_clarify.capabilities.container import (
    build_container_auto_clarify_proposal,
)
from core.task_loop.action_resolution.auto_clarify.capabilities.generic import (
    build_generic_auto_clarify_proposal,
)
from core.task_loop.capability_policy import capability_type_from_tools


def _capability_family(step_request: Any) -> str:
    requested_capability = dict(getattr(step_request, "requested_capability", {}) or {})
    family = str(requested_capability.get("capability_type") or "").strip().lower()
    if family:
        return family
    return capability_type_from_tools(list(getattr(step_request, "suggested_tools", []) or []))


def dispatch_auto_clarify_proposal(
    snapshot: Any,
    step_request: Any,
    *,
    step_result: Any | None = None,
) -> Dict[str, Any]:
    family = _capability_family(step_request)
    if family == "container_manager":
        return build_container_auto_clarify_proposal(
            snapshot,
            step_request,
            step_result=step_result,
        )
    return build_generic_auto_clarify_proposal(
        snapshot,
        step_request,
        step_result=step_result,
        capability_family=family,
    )


__all__ = ["dispatch_auto_clarify_proposal"]
