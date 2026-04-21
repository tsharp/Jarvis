"""Safe parameter completion hooks for missing loop-action fields."""

from __future__ import annotations

from typing import Any, Dict, List

from core.task_loop.action_resolution.auto_clarify.contracts import (
    AutoClarifyValueSource,
    ResolvedField,
)
from core.task_loop.capabilities.container.context import (
    capability_request_params,
    merge_container_context,
)
from core.task_loop.capabilities.container.parameter_policy import (
    build_container_parameter_context,
)

DEFAULT_PYTHON_VERSION = "3.11"
DEFAULT_DEPENDENCY_SPEC = "none"
DEFAULT_BUILD_OR_RUNTIME = "runtime"


def complete_container_parameters(
    snapshot: Any,
    *,
    requested_capability: Dict[str, Any],
    capability_context: Dict[str, Any] | None = None,
    user_reply: str = "",
) -> Dict[str, Any]:
    capability_action = str(requested_capability.get("capability_action") or "").strip().lower()
    if capability_action != "request_container":
        return {
            "capability_context": dict(capability_context or {}),
            "parameter_context": {},
            "resolved_fields": [],
            "rationale": [],
        }

    merged_context = merge_container_context(
        capability_context,
        snapshot=snapshot,
        user_reply=user_reply,
    )
    known_fields = dict(merged_context.get("known_fields") or {})
    request_family = str(merged_context.get("request_family") or "generic_container").strip().lower()
    resolved_fields: List[ResolvedField] = []
    rationale: List[str] = []

    if request_family == "python_container":
        if not str(known_fields.get("python_version") or "").strip():
            known_fields["python_version"] = DEFAULT_PYTHON_VERSION
            resolved_fields.append(
                ResolvedField(
                    name="python_version",
                    value=DEFAULT_PYTHON_VERSION,
                    source=AutoClarifyValueSource.DEFAULT,
                    confidence=0.82,
                    detail="Sicherer Default fuer Python-Container ohne explizite Versionsangabe.",
                )
            )
            rationale.append("default_python_version_applied")

        if not str(known_fields.get("dependency_spec") or "").strip():
            known_fields["dependency_spec"] = DEFAULT_DEPENDENCY_SPEC
            resolved_fields.append(
                ResolvedField(
                    name="dependency_spec",
                    value=DEFAULT_DEPENDENCY_SPEC,
                    source=AutoClarifyValueSource.DEFAULT,
                    confidence=0.88,
                    detail="Ohne explizite Abhaengigkeiten wird standardmaessig kein zusaetzliches Paket installiert.",
                )
            )
            rationale.append("default_dependency_spec_applied")

        if not str(known_fields.get("build_or_runtime") or "").strip():
            known_fields["build_or_runtime"] = DEFAULT_BUILD_OR_RUNTIME
            resolved_fields.append(
                ResolvedField(
                    name="build_or_runtime",
                    value=DEFAULT_BUILD_OR_RUNTIME,
                    source=AutoClarifyValueSource.DEFAULT,
                    confidence=0.90,
                    detail="Python-Container werden ohne gegenteilige Angabe als Runtime-Container behandelt.",
                )
            )
            rationale.append("default_build_or_runtime_applied")

    merged_context["known_fields"] = known_fields
    parameter_context = build_container_parameter_context(
        snapshot,
        requested_capability=requested_capability,
        capability_context=merged_context,
        user_reply=user_reply,
    )
    parameter_context["params"] = capability_request_params(merged_context)

    return {
        "capability_context": merged_context,
        "parameter_context": parameter_context,
        "resolved_fields": resolved_fields,
        "rationale": rationale,
    }


__all__ = [
    "DEFAULT_BUILD_OR_RUNTIME",
    "DEFAULT_DEPENDENCY_SPEC",
    "DEFAULT_PYTHON_VERSION",
    "complete_container_parameters",
]
