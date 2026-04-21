# core/layers/control/layer.py
"""
LAYER 2: ControlLayer (Qwen)
v4.0: Echtes Ollama Streaming für Progressive Steps
"""

import json
import httpx
import asyncio
from typing import Dict, Any, Optional, AsyncGenerator, List
from config import (
    OLLAMA_BASE,
    get_control_model,
    get_control_model_deep,
    get_control_provider,
    get_control_timeout_interactive_s,
    get_control_timeout_deep_s,
    get_control_endpoint_override,
    get_thinking_model,
    get_control_prompt_memory_chars,
    get_control_prompt_plan_chars,
    get_control_prompt_user_chars,
    get_memory_keys_max_per_request,
)
from utils.logger import log_info, log_error, log_debug, log_warning
from utils.json_parser import safe_parse_json
from utils.role_endpoint_resolver import resolve_role_endpoint, resolve_ollama_base_endpoint
from core.llm_provider_client import complete_prompt, resolve_role_provider, stream_chat
from core.control_decision_utils import (
    DEFAULT_HARD_BLOCK_REASON_CODES,
    is_allowed_hard_block_reason_code,
    make_hard_block_verification,
    normalize_block_reason_code,
)
from core.control_policy_utils import (
    has_hard_safety_markers,
    is_cron_tool_name,
    is_light_cim_hard_denial,
    is_runtime_operation_tool,
    looks_like_capability_mismatch,
    looks_like_spurious_policy_block,
    sanitize_warning_messages,
    user_text_has_explicit_skill_intent,
    verification_text,
    warning_list,
)
from core.safety import LightCIM
from core.sequential_registry import get_registry
from .runtime.models import (
    resolve_control_model as _runtime_resolve_control_model,
    resolve_sequential_model as _runtime_resolve_sequential_model,
)
from .runtime.timeouts import (
    normalize_response_mode as _runtime_normalize_response_mode,
    resolve_verify_timeout_s as _runtime_resolve_verify_timeout_s,
)
from .runtime.endpoints import (
    resolve_control_endpoint_override as _runtime_resolve_control_endpoint_override,
)
from .prompting.constants import (
    CONTROL_PROMPT,
    SEQUENTIAL_SYSTEM_PROMPT,
)
from .prompting.payload import (
    build_control_prompt_payload as _prompting_build_control_prompt_payload,
    clip_text as _prompting_clip_text,
    memory_keys as _prompting_memory_keys,
    tool_names as _prompting_tool_names,
)
from .tools.normalization import (
    cim_tool_args as _tools_cim_tool_args,
    normalize_suggested_tools as _tools_normalize_suggested_tools,
    normalize_tool_arguments as _tools_normalize_tool_arguments,
    sanitize_tool_name as _tools_sanitize_tool_name,
)
from .tools.skills import (
    extract_skill_names as _tools_extract_skill_names,
    get_available_skills as _tools_get_available_skills,
    get_available_skills_async as _tools_get_available_skills_async,
)
from .tools.availability import (
    is_tool_available as _tools_is_tool_available,
    set_mcp_hub as _tools_set_mcp_hub,
)
from .tools.decision import (
    decide_tools as _tools_decide_tools,
)
from .policy.warnings import (
    sanitize_warning_messages_for_policy as _policy_sanitize_warning_messages,
    verification_text_for_policy as _policy_verification_text,
    warning_list_for_policy as _policy_warning_list,
)
from .policy.false_blocks import (
    combined_suggested_tools as _policy_combined_suggested_tools,
    has_container_context as _policy_has_container_context,
    has_cron_context as _policy_has_cron_context,
    has_solution_oriented_action_signal as _policy_has_solution_oriented_action_signal,
    is_cron_tool_name_for_policy as _policy_is_cron_tool_name,
    is_runtime_operation_tool_for_policy as _policy_is_runtime_operation_tool,
    looks_like_capability_mismatch_for_policy as _policy_looks_like_capability_mismatch,
    looks_like_spurious_policy_block_for_policy as _policy_looks_like_spurious_policy_block,
    should_lift_container_false_block as _policy_should_lift_container_false_block,
    should_lift_cron_false_block as _policy_should_lift_cron_false_block,
    should_lift_query_budget_fast_path_false_block as _policy_should_lift_query_budget_fast_path_false_block,
    should_lift_solution_oriented_false_block as _policy_should_lift_solution_oriented_false_block,
)
from .policy.authority import (
    enforce_block_authority as _policy_enforce_block_authority,
    infer_block_reason_code as _policy_infer_block_reason_code,
)
from .policy.safety import (
    has_hard_safety_markers_for_policy as _policy_has_hard_safety_markers,
    is_light_cim_hard_denial_for_policy as _policy_is_light_cim_hard_denial,
    user_text_has_explicit_skill_intent_for_policy as _policy_user_text_has_explicit_skill_intent,
    user_text_has_hard_safety_keywords as _policy_user_text_has_hard_safety_keywords,
    user_text_has_malicious_intent as _policy_user_text_has_malicious_intent,
)
from .strategy.skill_intent import (
    extract_requested_skill_name as _strategy_extract_requested_skill_name,
    is_skill_creation_sensitive as _strategy_is_skill_creation_sensitive,
)
from .strategy.resolution import (
    apply_resolution_strategy_authority as _strategy_apply_resolution_strategy_authority,
    normalize_resolution_strategy as _strategy_normalize_resolution_strategy,
)
from .strategy.turn_mode import (
    derive_authoritative_turn_mode as _strategy_derive_authoritative_turn_mode,
    normalize_turn_mode as _strategy_normalize_turn_mode,
)
from .strategy.execution_mode import (
    derive_authoritative_execution_mode as _strategy_derive_authoritative_execution_mode,
    normalize_execution_mode as _strategy_normalize_execution_mode,
)
from .strategy.container_selection import (
    apply_container_candidate_resolution as _strategy_apply_container_candidate_resolution,
    is_container_request_plan as _strategy_is_container_request_plan,
    normalize_container_candidates as _strategy_normalize_container_candidates,
)
from .verification.defaults import (
    default_verification as _verification_default_verification,
)
from .verification.corrections import (
    apply_corrections as _verification_apply_corrections,
)
from .verification.stabilization import (
    stabilize_verification_result as _verification_stabilize_verification_result,
)
from .verification.verify_flow import (
    verify_flow as _verification_verify_flow,
)
from .cim.context import (
    CIM_URL,
    get_cim_context as _cim_get_context,
)
from .cim.policy_engine import (
    CIM_POLICY_AVAILABLE,
    process_cim_policy,
    run_cim_policy_engine as _cim_run_policy_engine,
)
from .sequential.prompts import (
    build_sequential_system_prompt as _sequential_build_system_prompt,
    build_sequential_user_prompt as _sequential_build_user_prompt,
)
from .sequential.parse import (
    parse_sequential_steps as _sequential_parse_steps,
)
from .sequential.run import (
    check_sequential_thinking as _sequential_check_thinking,
)
from .sequential.stream import (
    check_sequential_thinking_stream as _sequential_check_thinking_stream,
)

CONTAINER_AUTO_SELECT_MIN_SCORE = 0.80
CONTAINER_AUTO_SELECT_MIN_MARGIN = 0.10

class ControlLayer:
    def __init__(self, model: str = None):
        self._model_override = (model or "").strip() or None
        self.ollama_base = OLLAMA_BASE
        self.light_cim = LightCIM()
        self.mcp_hub = None
        self.registry = get_registry()

    def _resolve_model(self, response_mode: str = "interactive") -> str:
        return _runtime_resolve_control_model(
            self._model_override,
            response_mode,
            get_control_model_fn=get_control_model,
            get_control_model_deep_fn=get_control_model_deep,
        )

    @staticmethod
    def _normalize_response_mode(response_mode: str) -> str:
        return _runtime_normalize_response_mode(response_mode)

    def _resolve_verify_timeout_s(self, response_mode: str = "interactive") -> float:
        return _runtime_resolve_verify_timeout_s(
            response_mode,
            get_control_timeout_interactive_s_fn=get_control_timeout_interactive_s,
            get_control_timeout_deep_s_fn=get_control_timeout_deep_s,
        )

    def _resolve_control_endpoint_override(self, response_mode: str = "interactive") -> str:
        return _runtime_resolve_control_endpoint_override(
            response_mode,
            get_control_endpoint_override_fn=get_control_endpoint_override,
            resolve_ollama_base_endpoint_fn=resolve_ollama_base_endpoint,
        )

    def _resolve_sequential_model(self) -> str:
        return _runtime_resolve_sequential_model(
            get_thinking_model_fn=get_thinking_model,
        )

    @staticmethod
    def _clip_text(text: str, max_chars: int) -> str:
        return _prompting_clip_text(text, max_chars)

    @staticmethod
    def _tool_names(raw_tools: List[Any], limit: int = 8) -> List[str]:
        return _prompting_tool_names(raw_tools, limit=limit)

    @staticmethod
    def _memory_keys(keys: List[Any]) -> List[str]:
        return _prompting_memory_keys(
            keys,
            get_memory_keys_max_per_request_fn=get_memory_keys_max_per_request,
        )

    def _build_control_prompt_payload(
        self,
        user_text: str,
        thinking_plan: Dict[str, Any],
        retrieved_memory: str,
    ) -> Dict[str, Any]:
        return _prompting_build_control_prompt_payload(
            user_text,
            thinking_plan,
            retrieved_memory,
            get_control_prompt_user_chars_fn=get_control_prompt_user_chars,
            get_control_prompt_plan_chars_fn=get_control_prompt_plan_chars,
            get_control_prompt_memory_chars_fn=get_control_prompt_memory_chars,
            memory_keys_fn=self._memory_keys,
            tool_names_fn=self._tool_names,
            clip_text_fn=self._clip_text,
            tool_availability_snapshot_fn=self._tool_availability_snapshot,
        )

    def _tool_availability_snapshot(self, suggested_tools: List[Any]) -> Dict[str, List[str]]:
        names = self._tool_names(suggested_tools, limit=10)
        available: List[str] = []
        unavailable: List[str] = []
        for name in names:
            if self._is_tool_available(name):
                available.append(name)
            else:
                unavailable.append(name)
        return {"available": available, "unavailable": unavailable}

    @staticmethod
    def _verification_text(verification: Dict[str, Any]) -> str:
        return _policy_verification_text(
            verification,
            verification_text_fn=verification_text,
        )

    @classmethod
    def _looks_like_capability_mismatch(cls, verification: Dict[str, Any]) -> bool:
        return _policy_looks_like_capability_mismatch(
            verification,
            looks_like_capability_mismatch_fn=looks_like_capability_mismatch,
        )

    @staticmethod
    def _is_cron_tool_name(tool_name: str) -> bool:
        return _policy_is_cron_tool_name(
            tool_name,
            is_cron_tool_name_fn=is_cron_tool_name,
        )

    @classmethod
    def _looks_like_spurious_policy_block(cls, verification: Dict[str, Any]) -> bool:
        return _policy_looks_like_spurious_policy_block(
            verification,
            looks_like_spurious_policy_block_fn=looks_like_spurious_policy_block,
        )

    @classmethod
    def _has_hard_safety_markers(cls, verification: Dict[str, Any]) -> bool:
        return _policy_has_hard_safety_markers(
            verification,
            has_hard_safety_markers_fn=has_hard_safety_markers,
        )

    @staticmethod
    def _warning_list(raw: Any) -> List[str]:
        return _policy_warning_list(
            raw,
            warning_list_fn=warning_list,
        )

    @classmethod
    def _is_light_cim_hard_denial(cls, cim_result: Dict[str, Any]) -> bool:
        return _policy_is_light_cim_hard_denial(
            cim_result,
            is_light_cim_hard_denial_fn=is_light_cim_hard_denial,
        )

    def _has_cron_context(
        self,
        verification: Dict[str, Any],
        thinking_plan: Dict[str, Any],
    ) -> bool:
        return _policy_has_cron_context(
            verification,
            thinking_plan,
            tool_names_fn=self._tool_names,
            is_cron_tool_name_fn=self._is_cron_tool_name,
        )

    def _should_lift_cron_false_block(
        self,
        verification: Dict[str, Any],
        thinking_plan: Dict[str, Any],
    ) -> bool:
        return _policy_should_lift_cron_false_block(
            verification,
            thinking_plan,
            has_hard_safety_markers_fn=self._has_hard_safety_markers,
            has_cron_context_fn=self._has_cron_context,
            looks_like_capability_mismatch_fn=self._looks_like_capability_mismatch,
            looks_like_spurious_policy_block_fn=self._looks_like_spurious_policy_block,
        )

    def _has_container_context(
        self,
        verification: Dict[str, Any],
        thinking_plan: Dict[str, Any],
    ) -> bool:
        return _policy_has_container_context(
            verification,
            thinking_plan,
            tool_names_fn=self._tool_names,
        )

    def _should_lift_container_false_block(
        self,
        verification: Dict[str, Any],
        thinking_plan: Dict[str, Any],
    ) -> bool:
        return _policy_should_lift_container_false_block(
            verification,
            thinking_plan,
            has_hard_safety_markers_fn=self._has_hard_safety_markers,
            has_container_context_fn=self._has_container_context,
            verification_text_fn=self._verification_text,
            looks_like_capability_mismatch_fn=self._looks_like_capability_mismatch,
            looks_like_spurious_policy_block_fn=self._looks_like_spurious_policy_block,
        )

    def _combined_suggested_tools(
        self,
        verification: Dict[str, Any],
        thinking_plan: Dict[str, Any],
        *,
        limit: int = 16,
    ) -> List[str]:
        return _policy_combined_suggested_tools(
            verification,
            thinking_plan,
            tool_names_fn=self._tool_names,
            limit=limit,
        )

    @staticmethod
    def _is_runtime_operation_tool(tool_name: str) -> bool:
        return _policy_is_runtime_operation_tool(
            tool_name,
            is_runtime_operation_tool_fn=is_runtime_operation_tool,
        )

    def _has_solution_oriented_action_signal(
        self,
        verification: Dict[str, Any],
        thinking_plan: Dict[str, Any],
        *,
        user_text: str = "",
    ) -> bool:
        return _policy_has_solution_oriented_action_signal(
            verification,
            thinking_plan,
            user_text=user_text,
            combined_suggested_tools_fn=self._combined_suggested_tools,
            is_runtime_operation_tool_fn=self._is_runtime_operation_tool,
        )

    def _should_lift_solution_oriented_false_block(
        self,
        verification: Dict[str, Any],
        thinking_plan: Dict[str, Any],
        *,
        user_text: str = "",
    ) -> bool:
        return _policy_should_lift_solution_oriented_false_block(
            verification,
            thinking_plan,
            user_text=user_text,
            has_hard_safety_markers_fn=self._has_hard_safety_markers,
            user_text_has_hard_safety_keywords_fn=self._user_text_has_hard_safety_keywords,
            user_text_has_malicious_intent_fn=self._user_text_has_malicious_intent,
            verification_text_fn=self._verification_text,
            looks_like_capability_mismatch_fn=self._looks_like_capability_mismatch,
            looks_like_spurious_policy_block_fn=self._looks_like_spurious_policy_block,
            has_solution_oriented_action_signal_fn=self._has_solution_oriented_action_signal,
            combined_suggested_tools_fn=self._combined_suggested_tools,
            is_tool_available_fn=self._is_tool_available,
        )

    def _user_text_has_hard_safety_keywords(self, user_text: str) -> bool:
        return _policy_user_text_has_hard_safety_keywords(
            user_text,
            light_cim=self.light_cim,
        )

    def _user_text_has_malicious_intent(self, user_text: str) -> bool:
        return _policy_user_text_has_malicious_intent(user_text)

    @staticmethod
    def _user_text_has_explicit_skill_intent(user_text: str) -> bool:
        return _policy_user_text_has_explicit_skill_intent(
            user_text,
            user_text_has_explicit_skill_intent_fn=user_text_has_explicit_skill_intent,
        )

    def _should_lift_query_budget_fast_path_false_block(
        self,
        verification: Dict[str, Any],
        thinking_plan: Dict[str, Any],
        user_text: str = "",
    ) -> bool:
        return _policy_should_lift_query_budget_fast_path_false_block(
            verification,
            thinking_plan,
            user_text=user_text,
            has_hard_safety_markers_fn=self._has_hard_safety_markers,
            user_text_has_hard_safety_keywords_fn=self._user_text_has_hard_safety_keywords,
            verification_text_fn=self._verification_text,
            looks_like_spurious_policy_block_fn=self._looks_like_spurious_policy_block,
            has_cron_context_fn=self._has_cron_context,
            user_text_has_malicious_intent_fn=self._user_text_has_malicious_intent,
        )

    @staticmethod
    def _sanitize_warning_messages(warnings: Any) -> List[str]:
        return _policy_sanitize_warning_messages(
            warnings,
            sanitize_warning_messages_fn=sanitize_warning_messages,
        )

    @classmethod
    def _infer_block_reason_code(
        cls,
        verification: Dict[str, Any],
        *,
        user_text: str = "",
        thinking_plan: Dict[str, Any],
    ) -> str:
        return _policy_infer_block_reason_code(
            verification,
            user_text=user_text,
            thinking_plan=thinking_plan,
            verification_text_fn=cls._verification_text,
        )

    def _enforce_block_authority(
        self,
        verification: Dict[str, Any],
        thinking_plan: Dict[str, Any],
        *,
        user_text: str = "",
    ) -> Dict[str, Any]:
        return _policy_enforce_block_authority(
            verification,
            thinking_plan,
            user_text=user_text,
            warning_list_fn=self._warning_list,
            normalize_block_reason_code_fn=normalize_block_reason_code,
            infer_block_reason_code_fn=self._infer_block_reason_code,
            is_allowed_hard_block_reason_code_fn=is_allowed_hard_block_reason_code,
            default_hard_block_reason_codes=DEFAULT_HARD_BLOCK_REASON_CODES,
            has_hard_safety_markers_fn=self._has_hard_safety_markers,
            user_text_has_hard_safety_keywords_fn=self._user_text_has_hard_safety_keywords,
            user_text_has_malicious_intent_fn=self._user_text_has_malicious_intent,
        )

    def _stabilize_verification_result(
        self,
        verification: Dict[str, Any],
        thinking_plan: Dict[str, Any],
        user_text: str = "",
    ) -> Dict[str, Any]:
        return _verification_stabilize_verification_result(
            verification,
            thinking_plan,
            user_text=user_text,
            default_verification_fn=self._default_verification,
            sanitize_warning_messages_fn=self._sanitize_warning_messages,
            enforce_block_authority_fn=self._enforce_block_authority,
            has_hard_safety_markers_fn=self._has_hard_safety_markers,
            user_text_has_hard_safety_keywords_fn=self._user_text_has_hard_safety_keywords,
            user_text_has_malicious_intent_fn=self._user_text_has_malicious_intent,
            tool_names_fn=self._tool_names,
            is_tool_available_fn=self._is_tool_available,
            looks_like_capability_mismatch_fn=self._looks_like_capability_mismatch,
            should_lift_cron_false_block_fn=self._should_lift_cron_false_block,
            should_lift_container_false_block_fn=self._should_lift_container_false_block,
            should_lift_query_budget_fast_path_false_block_fn=self._should_lift_query_budget_fast_path_false_block,
            should_lift_solution_oriented_false_block_fn=self._should_lift_solution_oriented_false_block,
            apply_container_candidate_resolution_fn=self._apply_container_candidate_resolution,
            apply_resolution_strategy_authority_fn=self._apply_resolution_strategy_authority,
            log_warning_fn=log_warning,
        )

    def set_mcp_hub(self, hub):
        self.mcp_hub = _tools_set_mcp_hub(
            hub,
            log_info_fn=log_info,
        )

    @staticmethod
    def _extract_skill_names(result: Any) -> List[str]:
        return _tools_extract_skill_names(result)

    def _get_available_skills(self) -> list:
        return _tools_get_available_skills(
            self.mcp_hub,
            extract_skill_names_fn=self._extract_skill_names,
            log_debug_fn=log_debug,
        )

    async def _get_available_skills_async(self) -> list:
        return await _tools_get_available_skills_async(
            self.mcp_hub,
            extract_skill_names_fn=self._extract_skill_names,
            log_debug_fn=log_debug,
        )

    def _is_tool_available(self, tool_name: str) -> bool:
        from mcp.hub import get_hub

        return _tools_is_tool_available(
            tool_name,
            mcp_hub=self.mcp_hub,
            get_hub_fn=get_hub,
            log_info_fn=log_info,
            log_warning_fn=log_warning,
            get_available_skills_fn=self._get_available_skills,
        )

    @staticmethod
    def _normalize_tool_arguments(raw_args: Any) -> Dict[str, Any]:
        return _tools_normalize_tool_arguments(
            raw_args,
            safe_parse_json_fn=safe_parse_json,
        )

    @staticmethod
    def _sanitize_tool_name(raw_name: Any) -> str:
        return _tools_sanitize_tool_name(raw_name)

    @staticmethod
    def _normalize_suggested_tools(verified_plan: Dict[str, Any]) -> List[Dict[str, Any]]:
        return _tools_normalize_suggested_tools(
            verified_plan,
            sanitize_tool_name_fn=ControlLayer._sanitize_tool_name,
            normalize_tool_arguments_fn=ControlLayer._normalize_tool_arguments,
        )

    @staticmethod
    def _cim_tool_args(
        verified_plan: Dict[str, Any],
        tool_name: str,
        user_text: str = "",
    ) -> Dict[str, Any]:
        return _tools_cim_tool_args(
            verified_plan,
            tool_name,
            user_text=user_text,
        )

    @staticmethod
    def _normalize_container_candidates(thinking_plan: Dict[str, Any]) -> List[Dict[str, Any]]:
        return _strategy_normalize_container_candidates(thinking_plan)

    @staticmethod
    def _normalize_resolution_strategy(value: Any) -> str:
        return _strategy_normalize_resolution_strategy(value)

    @staticmethod
    def _normalize_turn_mode(value: Any) -> str:
        return _strategy_normalize_turn_mode(value)

    @staticmethod
    def _normalize_execution_mode(value: Any) -> str:
        return _strategy_normalize_execution_mode(value)

    def _derive_authoritative_execution_mode(
        self,
        verification: Dict[str, Any],
        thinking_plan: Dict[str, Any],
    ) -> tuple[str, list[str], list[str]]:
        return _strategy_derive_authoritative_execution_mode(
            verification,
            thinking_plan,
            normalize_execution_mode_fn=self._normalize_execution_mode,
            normalize_turn_mode_fn=self._normalize_turn_mode,
        )

    def _derive_authoritative_turn_mode(
        self,
        verification: Dict[str, Any],
        thinking_plan: Dict[str, Any],
    ) -> tuple[str, list[str], list[str]]:
        return _strategy_derive_authoritative_turn_mode(
            verification,
            thinking_plan,
            normalize_turn_mode_fn=self._normalize_turn_mode,
        )

    def _apply_resolution_strategy_authority(
        self,
        verification: Dict[str, Any],
        thinking_plan: Dict[str, Any],
        *,
        user_text: str = "",
    ) -> Dict[str, Any]:
        return _strategy_apply_resolution_strategy_authority(
            verification,
            thinking_plan,
            user_text=user_text,
            has_hard_safety_markers_fn=self._has_hard_safety_markers,
            user_text_has_hard_safety_keywords_fn=self._user_text_has_hard_safety_keywords,
            user_text_has_malicious_intent_fn=self._user_text_has_malicious_intent,
            normalize_resolution_strategy_fn=self._normalize_resolution_strategy,
            warning_list_fn=self._warning_list,
            tool_names_fn=self._tool_names,
        )

    @staticmethod
    def _is_container_request_plan(thinking_plan: Dict[str, Any]) -> bool:
        return _strategy_is_container_request_plan(thinking_plan)

    def _apply_container_candidate_resolution(
        self,
        verification: Dict[str, Any],
        thinking_plan: Dict[str, Any],
        *,
        user_text: str = "",
    ) -> Dict[str, Any]:
        return _strategy_apply_container_candidate_resolution(
            verification,
            thinking_plan,
            user_text=user_text,
            is_container_request_plan_fn=self._is_container_request_plan,
            has_hard_safety_markers_fn=self._has_hard_safety_markers,
            user_text_has_hard_safety_keywords_fn=self._user_text_has_hard_safety_keywords,
            user_text_has_malicious_intent_fn=self._user_text_has_malicious_intent,
            normalize_container_candidates_fn=self._normalize_container_candidates,
            warning_list_fn=self._warning_list,
            container_auto_select_min_score=CONTAINER_AUTO_SELECT_MIN_SCORE,
            container_auto_select_min_margin=CONTAINER_AUTO_SELECT_MIN_MARGIN,
        )

    @staticmethod
    def _extract_requested_skill_name(user_text: str) -> str:
        return _strategy_extract_requested_skill_name(user_text)

    @staticmethod
    def _is_skill_creation_sensitive(thinking_plan: Dict[str, Any]) -> bool:
        return _strategy_is_skill_creation_sensitive(
            thinking_plan,
            tool_names_fn=ControlLayer._tool_names,
        )

    async def decide_tools(self, user_text: str, verified_plan: Dict[str, Any]) -> List[Dict[str, Any]]:
        return await _tools_decide_tools(
            user_text,
            verified_plan,
            normalize_suggested_tools_fn=self._normalize_suggested_tools,
            user_text_has_explicit_skill_intent_fn=self._user_text_has_explicit_skill_intent,
            is_tool_available_fn=self._is_tool_available,
            cim_tool_args_fn=self._cim_tool_args,
            log_info_fn=log_info,
        )

    async def verify(
        self,
        user_text: str,
        thinking_plan: Dict[str, Any],
        retrieved_memory: str = "",
        response_mode: str = "interactive",
    ) -> Dict[str, Any]:
        return await _verification_verify_flow(
            user_text,
            thinking_plan,
            retrieved_memory=retrieved_memory,
            response_mode=response_mode,
            light_cim=self.light_cim,
            ollama_base=self.ollama_base,
            control_prompt=CONTROL_PROMPT,
            get_control_provider_fn=get_control_provider,
            resolve_role_provider_fn=resolve_role_provider,
            resolve_role_endpoint_fn=resolve_role_endpoint,
            complete_prompt_fn=complete_prompt,
            safe_parse_json_fn=safe_parse_json,
            make_hard_block_verification_fn=make_hard_block_verification,
            cim_policy_available=CIM_POLICY_AVAILABLE,
            process_cim_policy_fn=process_cim_policy,
            run_cim_policy_engine_fn=_cim_run_policy_engine,
            user_text_has_malicious_intent_fn=self._user_text_has_malicious_intent,
            get_available_skills_async_fn=self._get_available_skills_async,
            is_skill_creation_sensitive_fn=self._is_skill_creation_sensitive,
            extract_requested_skill_name_fn=self._extract_requested_skill_name,
            is_light_cim_hard_denial_fn=self._is_light_cim_hard_denial,
            warning_list_fn=self._warning_list,
            normalize_response_mode_fn=self._normalize_response_mode,
            resolve_verify_timeout_s_fn=self._resolve_verify_timeout_s,
            resolve_model_fn=self._resolve_model,
            build_control_prompt_payload_fn=self._build_control_prompt_payload,
            resolve_control_endpoint_override_fn=self._resolve_control_endpoint_override,
            default_verification_fn=self._default_verification,
            stabilize_verification_result_fn=self._stabilize_verification_result,
            log_info_fn=log_info,
            log_warning_fn=log_warning,
            log_error_fn=log_error,
        )

    async def _check_sequential_thinking(self, user_text: str, thinking_plan: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        return await _sequential_check_thinking(
            user_text,
            thinking_plan,
            mcp_hub=self.mcp_hub,
            registry=self.registry,
            asyncio_module=asyncio,
            log_info_fn=log_info,
            log_error_fn=log_error,
        )

    async def _get_cim_context(self, user_text: str, mode: str = None) -> Optional[str]:
        return await _cim_get_context(
            user_text,
            mode=mode,
            async_client_cls=httpx.AsyncClient,
            cim_url=CIM_URL,
            log_debug_fn=log_debug,
        )

    async def _check_sequential_thinking_stream(
        self,
        user_text: str,
        thinking_plan: Dict[str, Any]
    ):
        async for event in _sequential_check_thinking_stream(
            user_text,
            thinking_plan,
            mcp_hub=self.mcp_hub,
            registry=self.registry,
            ollama_base=self.ollama_base,
            asyncio_module=asyncio,
            json_module=json,
            async_client_cls=httpx.AsyncClient,
            resolve_role_provider_fn=resolve_role_provider,
            resolve_role_endpoint_fn=resolve_role_endpoint,
            stream_chat_fn=stream_chat,
            resolve_sequential_model_fn=self._resolve_sequential_model,
            build_system_prompt_fn=_sequential_build_system_prompt,
            build_user_prompt_fn=_sequential_build_user_prompt,
            parse_steps_fn=_sequential_parse_steps,
            log_info_fn=log_info,
            log_error_fn=log_error,
            log_debug_fn=log_debug,
            log_warning_fn=log_warning,
        ):
            yield event
    def _default_verification(self, thinking_plan: Dict[str, Any]) -> Dict[str, Any]:
        return _verification_default_verification(thinking_plan)

    def apply_corrections(self, thinking_plan: Dict[str, Any], verification: Dict[str, Any]) -> Dict[str, Any]:
        return _verification_apply_corrections(
            thinking_plan,
            verification,
            sanitize_warning_messages_fn=self._sanitize_warning_messages,
            tool_names_fn=self._tool_names,
            normalize_resolution_strategy_fn=self._normalize_resolution_strategy,
            derive_authoritative_execution_mode_fn=self._derive_authoritative_execution_mode,
            derive_authoritative_turn_mode_fn=self._derive_authoritative_turn_mode,
        )
