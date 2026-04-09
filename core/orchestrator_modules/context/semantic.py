from __future__ import annotations

import asyncio
import json
import os
from typing import Any, Callable, Dict, List, Optional

from core.plan_runtime_bridge import (
    get_runtime_grounding_evidence,
    set_runtime_grounding_evidence,
)


def derive_container_addon_tags_from_inspect(container_info: Dict[str, Any]) -> List[str]:
    if not isinstance(container_info, dict):
        return []
    import re

    tags = {
        "container-shell",
        str(container_info.get("blueprint_id", "")).strip().lower(),
        str(container_info.get("name", "")).strip().lower(),
    }
    image_ref = str(container_info.get("image", "")).strip().lower()
    if image_ref:
        tags.update(part for part in re.split(r"[^a-z0-9]+", image_ref) if len(part) >= 3)
    if bool(container_info.get("running")):
        tags.add("running")
    return sorted(tag for tag in tags if tag and tag != "(none)")


def parse_list_skills_runtime_snapshot(raw_result: Any) -> Dict[str, Any]:
    payload = raw_result
    if isinstance(payload, dict) and isinstance(payload.get("structuredContent"), dict):
        payload = payload.get("structuredContent", {})
    if not isinstance(payload, dict):
        return {}

    installed_rows = payload.get("installed") if isinstance(payload.get("installed"), list) else []
    available_rows = payload.get("available") if isinstance(payload.get("available"), list) else []
    installed_names: List[str] = []
    for row in installed_rows:
        if isinstance(row, dict):
            name = str(row.get("name") or "").strip()
        else:
            name = str(row or "").strip()
        if name:
            installed_names.append(name)

    try:
        installed_count = int(payload.get("installed_count"))
    except Exception:
        installed_count = len(installed_rows)
    try:
        available_count = int(payload.get("available_count"))
    except Exception:
        available_count = len(available_rows)

    return {
        "installed": installed_rows,
        "installed_names": installed_names,
        "installed_count": installed_count,
        "available": available_rows,
        "available_count": available_count,
        "raw_payload": payload,
    }


def parse_list_draft_skills_snapshot(raw_result: Any) -> Dict[str, Any]:
    payload = raw_result
    if isinstance(payload, dict) and isinstance(payload.get("structuredContent"), dict):
        payload = payload.get("structuredContent", {})
    if not isinstance(payload, dict):
        return {}

    draft_rows = payload.get("drafts") if isinstance(payload.get("drafts"), list) else []
    draft_names: List[str] = []
    for row in draft_rows:
        if isinstance(row, dict):
            name = str(row.get("name") or "").strip()
        else:
            name = str(row or "").strip()
        if name:
            draft_names.append(name)

    return {
        "drafts": draft_rows,
        "draft_names": draft_names,
        "draft_count": len(draft_rows),
        "raw_payload": payload,
    }


def summarize_skill_runtime_snapshot(snapshot: Dict[str, Any]) -> str:
    if not isinstance(snapshot, dict):
        return ""
    installed_count = snapshot.get("installed_count")
    draft_count = snapshot.get("draft_count")
    available_count = snapshot.get("available_count")
    installed_names = list(snapshot.get("installed_names") or [])
    draft_names = list(snapshot.get("draft_names") or [])

    lines = ["Live runtime skill snapshot:"]
    if installed_count is not None:
        lines.append(f"- installed_runtime_skills: {installed_count}")
    if draft_count is not None:
        lines.append(f"- draft_skills: {draft_count}")
    if available_count is not None:
        lines.append(f"- available_skills: {available_count}")
    if installed_names:
        lines.append(f"- installed_examples: {', '.join(installed_names[:6])}")
    if draft_names:
        lines.append(f"- draft_examples: {', '.join(draft_names[:6])}")
    return "\n".join(lines).strip() if len(lines) > 1 else ""


def summarize_skill_registry_snapshot(snapshot: Dict[str, Any]) -> str:
    if not isinstance(snapshot, dict):
        return ""
    active_names = list(snapshot.get("active_names") or [])
    draft_names = list(snapshot.get("draft_names") or [])
    lines = [
        f"active_count: {int(snapshot.get('active_count', len(active_names)) or 0)}",
        f"draft_count: {int(snapshot.get('draft_count', len(draft_names)) or 0)}",
    ]
    if active_names:
        lines.append("active_names: " + ", ".join(active_names[:8]))
    if draft_names:
        lines.append("draft_names: " + ", ".join(draft_names[:8]))
    return "\n".join(lines).strip()


def summarize_container_inspect_for_capability_context(container_info: Dict[str, Any]) -> str:
    if not isinstance(container_info, dict):
        return ""

    resource_limits = container_info.get("resource_limits") or {}
    cpu_count = resource_limits.get("cpu_count")
    memory_mb = resource_limits.get("memory_mb")
    mounts = container_info.get("mounts") if isinstance(container_info.get("mounts"), list) else []
    ports = container_info.get("ports") if isinstance(container_info.get("ports"), list) else []
    port_values: List[str] = []
    for item in ports[:6]:
        if isinstance(item, dict):
            host_port = str(item.get("host_port") or item.get("published") or "").strip()
            container_port = str(item.get("container_port") or item.get("target") or "").strip()
            protocol = str(item.get("protocol") or "").strip()
            if host_port and container_port:
                port_values.append(f"{host_port}->{container_port}/{protocol or 'tcp'}")
            elif host_port or container_port:
                port_values.append(host_port or container_port)
        elif str(item).strip():
            port_values.append(str(item).strip())

    lines = [
        "Active container identity:",
        f"- container_id: {str(container_info.get('container_id') or '').strip() or '(unknown)'}",
        f"- name: {str(container_info.get('name') or '').strip() or '(unknown)'}",
        f"- blueprint_id: {str(container_info.get('blueprint_id') or '').strip() or '(unknown)'}",
        f"- image: {str(container_info.get('image') or '').strip() or '(unknown)'}",
        f"- status: {str(container_info.get('status') or '').strip() or '(unknown)'}",
        f"- network: {str(container_info.get('network') or '').strip() or '(unknown)'}",
    ]
    if cpu_count or memory_mb:
        lines.append(f"- resource_limits: cpu={cpu_count or '?'} memory_mb={memory_mb or '?'}")
    if mounts:
        lines.append(f"- mounts: {', '.join(str(item).strip() for item in mounts[:4] if str(item).strip())}")
    if port_values:
        lines.append(f"- ports: {', '.join(port_values[:4])}")
    deploy_warnings = container_info.get("deploy_warnings")
    if isinstance(deploy_warnings, list) and deploy_warnings:
        lines.append(
            f"- deploy_warnings: {', '.join(str(item).strip() for item in deploy_warnings[:3] if str(item).strip())}"
        )
    return "\n".join(lines).strip()


async def maybe_build_active_container_capability_context(
    *,
    user_text: str,
    conversation_id: str,
    verified_plan: Dict[str, Any],
    history_len: int = 0,
    is_active_container_capability_query_fn: Callable[[str], bool],
    get_recent_container_state_fn: Callable[[str, int], Optional[Dict[str, Any]]],
    container_state_has_active_target_fn: Callable[[Optional[Dict[str, Any]]], bool],
    get_hub_fn: Callable[[], Any],
    resolve_pending_container_id_async_fn: Callable[..., Any],
    safe_str_fn: Callable[[Any, int], str],
    update_container_state_from_tool_result_fn: Callable[..., None],
    build_tool_result_card_fn: Callable[[str, Any, str, str], Any],
    build_grounding_evidence_entry_fn: Callable[[str, Any, str, str], Dict[str, Any]],
    merge_grounding_evidence_items_fn: Callable[[Any, Any], List[Dict[str, Any]]],
    log_warn_fn: Callable[[str], None],
) -> Dict[str, str]:
    if not isinstance(verified_plan, dict):
        return {}
    if not is_active_container_capability_query_fn(user_text):
        return {}

    container_state = get_recent_container_state_fn(conversation_id, history_len)
    if not container_state_has_active_target_fn(container_state):
        return {}

    tool_hub = get_hub_fn()
    tool_hub.initialize()
    preferred_ids: List[str] = []
    if isinstance(container_state, dict):
        preferred_ids.extend(
            [
                str(container_state.get("last_active_container_id", "")).strip(),
                str(container_state.get("home_container_id", "")).strip(),
            ]
        )

    container_id = ""
    for candidate in preferred_ids:
        if candidate:
            container_id = candidate
            break
    if not container_id:
        container_id, _reason = await resolve_pending_container_id_async_fn(
            tool_hub,
            conversation_id,
            preferred_ids=preferred_ids,
            history_len=history_len,
        )
    if not container_id:
        return {}

    try:
        if hasattr(tool_hub, "call_tool_async"):
            inspect_result = await tool_hub.call_tool_async(
                "container_inspect",
                {"container_id": container_id},
            )
        else:
            inspect_result = await asyncio.to_thread(
                tool_hub.call_tool,
                "container_inspect",
                {"container_id": container_id},
            )
    except Exception as exc:
        log_warn_fn(
            f"[Orchestrator] Active-container capability inspect skipped: {safe_str_fn(exc, 160)}"
        )
        return {}

    if not isinstance(inspect_result, dict) or str(inspect_result.get("error", "")).strip():
        return {}

    update_container_state_from_tool_result_fn(
        conversation_id,
        "container_inspect",
        {"container_id": container_id},
        inspect_result,
        history_len=history_len,
    )

    inspect_summary = summarize_container_inspect_for_capability_context(inspect_result)
    if not inspect_summary:
        return {}

    inspect_card, inspect_ref = build_tool_result_card_fn(
        "container_inspect",
        inspect_summary,
        "ok",
        conversation_id,
    )
    evidence_items = [
        build_grounding_evidence_entry_fn(
            "container_inspect",
            inspect_summary,
            "ok",
            inspect_ref,
        )
    ]

    addon_context_text = ""
    addon_docs_text = ""
    addon_tool_results = ""
    try:
        from intelligence_modules.container_addons.loader import load_container_addon_context

        addon_context = await load_container_addon_context(
            blueprint_id=str(inspect_result.get("blueprint_id") or "").strip(),
            image_ref=str(inspect_result.get("image") or "").strip(),
            instruction=user_text,
            query_class="active_container_capability",
            shell_tail="",
            container_tags=derive_container_addon_tags_from_inspect(inspect_result),
        )
        selected_docs = list(addon_context.get("selected_docs") or [])
        addon_context_text = str(addon_context.get("context_text") or "").strip()
        if selected_docs:
            addon_docs_text = ", ".join(
                str(item.get("id") or item.get("title") or "").strip()
                for item in selected_docs[:4]
                if isinstance(item, dict) and str(item.get("id") or item.get("title") or "").strip()
            )
        if addon_context_text:
            addon_summary_parts = []
            if addon_docs_text:
                addon_summary_parts.append(f"selected_docs: {addon_docs_text}")
            addon_summary_parts.append(addon_context_text)
            addon_summary = "\n".join(addon_summary_parts).strip()
            addon_card, addon_ref = build_tool_result_card_fn(
                "container_addons",
                addon_summary,
                "ok",
                conversation_id,
            )
            addon_tool_results = addon_card
            evidence_items.append(
                build_grounding_evidence_entry_fn(
                    "container_addons",
                    addon_summary,
                    "ok",
                    addon_ref,
                )
            )
    except Exception as exc:
        log_warn_fn(
            "[Orchestrator] Active-container addon context skipped: "
            f"{safe_str_fn(exc, 160)}"
        )

    merged_evidence = merge_grounding_evidence_items_fn(
        get_runtime_grounding_evidence(verified_plan),
        evidence_items,
    )
    set_runtime_grounding_evidence(verified_plan, merged_evidence)

    context_lines = [
        "### ACTIVE CONTAINER CAPABILITY CONTEXT:",
        inspect_summary,
        "Treat the active container identity and addon excerpts below as higher priority than generic Linux assumptions.",
    ]
    if addon_docs_text:
        context_lines.append(f"Relevant addon docs: {addon_docs_text}")
    if addon_context_text:
        context_lines.append("Relevant container addon context:")
        context_lines.append(addon_context_text)

    verified_plan["_active_container_capability_context"] = {
        "container_id": container_id,
        "blueprint_id": str(inspect_result.get("blueprint_id") or "").strip(),
        "image": str(inspect_result.get("image") or "").strip(),
        "addon_docs": addon_docs_text,
    }
    return {
        "context_text": "\n".join(line for line in context_lines if str(line).strip()).strip(),
        "tool_results_text": f"{inspect_card}{addon_tool_results}",
    }


async def maybe_build_skill_semantic_context(
    *,
    user_text: str,
    conversation_id: str,
    verified_plan: Dict[str, Any],
    get_effective_resolution_strategy_fn: Callable[[Optional[Dict[str, Any]]], str],
    is_skill_catalog_context_query_fn: Callable[[str], bool],
    materialize_skill_catalog_policy_fn: Callable[[Optional[Dict[str, Any]]], Dict[str, Any]],
    get_hub_fn: Callable[[], Any],
    build_tool_result_card_fn: Callable[[str, Any, str, str], Any],
    build_grounding_evidence_entry_fn: Callable[[str, Any, str, str], Dict[str, Any]],
    merge_grounding_evidence_items_fn: Callable[[Any, Any], List[Dict[str, Any]]],
    safe_str_fn: Callable[[Any, int], str],
    log_warn_fn: Callable[[str], None],
) -> Dict[str, str]:
    if not isinstance(verified_plan, dict):
        return {}
    effective_strategy = get_effective_resolution_strategy_fn(verified_plan)
    if effective_strategy != "skill_catalog_context" and not is_skill_catalog_context_query_fn(user_text):
        return {}
    if not bool(verified_plan.get("is_fact_query", False)):
        return {}

    skill_policy = verified_plan.get("_skill_catalog_policy")
    if not isinstance(skill_policy, dict):
        skill_policy = materialize_skill_catalog_policy_fn(verified_plan)
    skill_policy = skill_policy if isinstance(skill_policy, dict) else {}
    required_tools = [
        str(tool or "").strip()
        for tool in list(skill_policy.get("required_tools") or [])
        if str(tool or "").strip()
    ]
    if not required_tools:
        required_tools = ["list_skills"]
    selected_hints = [
        str(hint or "").strip().lower()
        for hint in list(
            skill_policy.get("selected_hints")
            or verified_plan.get("strategy_hints")
            or []
        )
        if str(hint or "").strip()
    ]

    tool_hub = get_hub_fn()
    tool_hub.initialize()

    evidence_items: List[Dict[str, Any]] = []
    runtime_snapshot: Dict[str, Any] = {}
    tool_result_cards: List[str] = []

    if "list_skills" in required_tools:
        try:
            if hasattr(tool_hub, "call_tool_async"):
                list_skills_result = await tool_hub.call_tool_async(
                    "list_skills",
                    {"include_available": False},
                )
            else:
                list_skills_result = await asyncio.to_thread(
                    tool_hub.call_tool,
                    "list_skills",
                    {"include_available": False},
                )
            parsed_snapshot = parse_list_skills_runtime_snapshot(list_skills_result)
            if parsed_snapshot:
                runtime_snapshot.update(parsed_snapshot)
                raw_payload = parsed_snapshot.get("raw_payload") or {}
                raw_json = json.dumps(raw_payload, ensure_ascii=False, default=str)
                skills_card, skills_ref = build_tool_result_card_fn(
                    "list_skills",
                    raw_json,
                    "ok",
                    conversation_id,
                )
                tool_result_cards.append(skills_card)
                evidence_items.append(
                    build_grounding_evidence_entry_fn(
                        "list_skills",
                        raw_json,
                        "ok",
                        skills_ref,
                    )
                )
        except Exception as exc:
            log_warn_fn(
                "[Orchestrator] Skill runtime snapshot via list_skills skipped: "
                f"{safe_str_fn(exc, 160)}"
            )

    if "list_draft_skills" in required_tools:
        try:
            if hasattr(tool_hub, "call_tool_async"):
                list_drafts_result = await tool_hub.call_tool_async(
                    "list_draft_skills",
                    {},
                )
            else:
                list_drafts_result = await asyncio.to_thread(
                    tool_hub.call_tool,
                    "list_draft_skills",
                    {},
                )
            parsed_drafts = parse_list_draft_skills_snapshot(list_drafts_result)
            if parsed_drafts:
                runtime_snapshot["drafts"] = parsed_drafts.get("drafts") or []
                runtime_snapshot["draft_names"] = list(parsed_drafts.get("draft_names") or [])
                runtime_snapshot["draft_count"] = parsed_drafts.get("draft_count")
                raw_payload = parsed_drafts.get("raw_payload") or {}
                raw_json = json.dumps(raw_payload, ensure_ascii=False, default=str)
                drafts_card, drafts_ref = build_tool_result_card_fn(
                    "list_draft_skills",
                    raw_json,
                    "ok",
                    conversation_id,
                )
                tool_result_cards.append(drafts_card)
                evidence_items.append(
                    build_grounding_evidence_entry_fn(
                        "list_draft_skills",
                        raw_json,
                        "ok",
                        drafts_ref,
                    )
                )
        except Exception as exc:
            log_warn_fn(
                "[Orchestrator] Skill draft snapshot via list_draft_skills skipped: "
                f"{safe_str_fn(exc, 160)}"
            )

    try:
        import urllib.request as _ur

        skill_server = os.getenv("SKILL_SERVER_URL", "http://trion-skill-server:8088")
        with _ur.urlopen(f"{skill_server}/v1/skills", timeout=2) as response:
            registry_payload = json.loads(response.read())
        active_names = [
            str(item).strip()
            for item in list(registry_payload.get("active") or [])
            if str(item).strip()
        ]
        draft_names = [
            str(item).strip()
            for item in list(registry_payload.get("drafts") or [])
            if str(item).strip()
        ]
        registry_snapshot = {
            "active_names": active_names,
            "active_count": len(active_names),
            "draft_names": draft_names,
            "draft_count": len(draft_names),
        }
        if registry_snapshot["active_count"] or registry_snapshot["draft_count"]:
            runtime_snapshot.setdefault("installed_names", active_names[:])
            runtime_snapshot.setdefault("installed_count", len(active_names))
            runtime_snapshot["draft_names"] = draft_names
            runtime_snapshot["draft_count"] = len(draft_names)

            registry_summary = summarize_skill_registry_snapshot(registry_snapshot)
            registry_card, registry_ref = build_tool_result_card_fn(
                "skill_registry_snapshot",
                registry_summary,
                "ok",
                conversation_id,
            )
            tool_result_cards.append(registry_card)
            evidence_items.append(
                build_grounding_evidence_entry_fn(
                    "skill_registry_snapshot",
                    registry_summary,
                    "ok",
                    registry_ref,
                )
            )
    except Exception as exc:
        log_warn_fn(
            "[Orchestrator] Skill registry snapshot skipped: "
            f"{safe_str_fn(exc, 160)}"
        )

    addon_context_text = ""
    addon_docs_text = ""
    addon_doc_ids: List[str] = []
    try:
        from intelligence_modules.skill_addons.loader import load_skill_addon_context

        addon_context = await load_skill_addon_context(
            query=user_text,
            tags=selected_hints,
            runtime_snapshot=runtime_snapshot,
        )
        selected_docs = list(addon_context.get("selected_docs") or [])
        addon_context_text = str(addon_context.get("context_text") or "").strip()
        if selected_docs:
            addon_doc_ids = [
                str(item.get("id") or item.get("title") or "").strip()
                for item in selected_docs[:8]
                if isinstance(item, dict) and str(item.get("id") or item.get("title") or "").strip()
            ]
            addon_docs_text = ", ".join(addon_doc_ids[:4])
        if addon_context_text:
            addon_summary_parts = []
            if addon_docs_text:
                addon_summary_parts.append(f"selected_docs: {addon_docs_text}")
            addon_summary_parts.append(addon_context_text)
            addon_summary = "\n".join(addon_summary_parts).strip()
            addon_card, addon_ref = build_tool_result_card_fn(
                "skill_addons",
                addon_summary,
                "ok",
                conversation_id,
            )
            tool_result_cards.append(addon_card)
            evidence_items.append(
                build_grounding_evidence_entry_fn(
                    "skill_addons",
                    addon_summary,
                    "ok",
                    addon_ref,
                )
            )
    except Exception as exc:
        log_warn_fn(
            "[Orchestrator] Skill addon context skipped: "
            f"{safe_str_fn(exc, 160)}"
        )

    runtime_summary = summarize_skill_runtime_snapshot(runtime_snapshot)
    if not runtime_summary and not addon_context_text:
        return {}

    merged_evidence = merge_grounding_evidence_items_fn(
        get_runtime_grounding_evidence(verified_plan),
        evidence_items,
    )
    set_runtime_grounding_evidence(verified_plan, merged_evidence)

    context_lines = [
        "### SKILL CATALOG CONTEXT:",
        "Treat live runtime snapshot facts as the inventory authority. Treat addon excerpts only as taxonomy and answering rules.",
    ]
    if runtime_summary:
        context_lines.append(runtime_summary)
    if addon_docs_text:
        context_lines.append(f"Relevant skill addon docs: {addon_docs_text}")
    if addon_context_text:
        context_lines.append("Relevant skill addon context:")
        context_lines.append(addon_context_text)

    verified_plan["_skill_catalog_context"] = {
        "installed_count": runtime_snapshot.get("installed_count"),
        "draft_count": runtime_snapshot.get("draft_count"),
        "available_count": runtime_snapshot.get("available_count"),
        "selected_docs": addon_docs_text,
        "selected_doc_ids": addon_doc_ids,
        "policy_mode": str(skill_policy.get("mode") or "").strip(),
        "required_tools": required_tools,
        "selected_hints": selected_hints,
    }
    return {
        "context_text": "\n".join(line for line in context_lines if str(line).strip()).strip(),
        "tool_results_text": "".join(tool_result_cards),
    }
