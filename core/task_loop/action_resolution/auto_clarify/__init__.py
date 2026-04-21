"""Auto-clarify package for controlled self-resolution inside the task loop."""

from core.task_loop.action_resolution.auto_clarify.contracts import (
    AutoClarifyAction,
    AutoClarifyAutonomyLevel,
    AutoClarifyBlocker,
    AutoClarifyDecision,
    AutoClarifyMode,
    AutoClarifySource,
    AutoClarifyValueSource,
    MissingField,
    ResolvedField,
)
from core.task_loop.action_resolution.auto_clarify.domain_dispatch import (
    dispatch_auto_clarify_proposal,
)
from core.task_loop.action_resolution.auto_clarify.parameter_completion import (
    DEFAULT_BUILD_OR_RUNTIME,
    DEFAULT_DEPENDENCY_SPEC,
    DEFAULT_PYTHON_VERSION,
    complete_container_parameters,
)
from core.task_loop.action_resolution.auto_clarify.policy import (
    evaluate_auto_clarify,
)
from core.task_loop.action_resolution.auto_clarify.safety_gates import (
    AutonomyCandidateScore,
    AutonomyGateConfig,
    AutonomyGateDecision,
    AutonomyGateResult,
    DEFAULT_AUTONOMY_THRESHOLD,
    DEFAULT_CONFIDENCE_MARGIN,
    DEFAULT_RECHECK_THRESHOLD,
    evaluate_autonomy_gates,
    should_ask_user,
    should_block,
    should_recheck,
    should_self_execute,
)

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
    "dispatch_auto_clarify_proposal",
    "DEFAULT_BUILD_OR_RUNTIME",
    "DEFAULT_DEPENDENCY_SPEC",
    "DEFAULT_PYTHON_VERSION",
    "complete_container_parameters",
    "evaluate_auto_clarify",
    "AutonomyCandidateScore",
    "AutonomyGateConfig",
    "AutonomyGateDecision",
    "AutonomyGateResult",
    "DEFAULT_AUTONOMY_THRESHOLD",
    "DEFAULT_CONFIDENCE_MARGIN",
    "DEFAULT_RECHECK_THRESHOLD",
    "evaluate_autonomy_gates",
    "should_ask_user",
    "should_block",
    "should_recheck",
    "should_self_execute",
]
