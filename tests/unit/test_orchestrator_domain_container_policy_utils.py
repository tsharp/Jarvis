from core.orchestrator_domain_container_policy_utils import (
    apply_container_query_policy,
    apply_domain_route_to_plan,
    apply_domain_tool_policy,
    container_state_has_active_target,
    finalize_execution_suggested_tools,
    get_effective_resolution_strategy,
    is_active_container_capability_query,
    is_container_blueprint_catalog_query,
    is_container_inventory_query,
    is_container_request_query,
    is_container_state_binding_query,
    is_skill_catalog_context_query,
    looks_like_host_runtime_lookup,
    materialize_container_query_policy,
    materialize_skill_catalog_policy,
    prioritize_active_container_capability_tools,
    prioritize_home_container_tools,
    record_execution_tool_trace,
    rewrite_home_start_request_tools,
    select_read_only_skill_tool_for_query,
    seed_tool_for_domain_route,
    should_prioritize_skill_catalog_route,
    tool_name_list,
)


DOMAIN_CRON_TOOLS = {"autonomy_cron_status", "autonomy_cron_create_job"}
READ_ONLY_SKILL_TOOLS = {"list_skills", "list_draft_skills", "get_skill_info"}
DOMAIN_SKILL_TOOLS = set(READ_ONLY_SKILL_TOOLS).union({"autonomous_skill_task"})
DOMAIN_CONTAINER_TOOLS = {
    "request_container",
    "home_start",
    "container_list",
    "container_inspect",
    "exec_in_container",
}
DOMAIN_CRON_OP_TO_TOOL = {
    "status": "autonomy_cron_status",
    "create": "autonomy_cron_create_job",
}
DOMAIN_CONTAINER_OP_TO_TOOL = {
    "list": "container_list",
    "inspect": "container_inspect",
    "exec": "exec_in_container",
    "deploy": "request_container",
}


def _extract_tool_name(tool_spec):
    if isinstance(tool_spec, dict):
        return str(tool_spec.get("tool") or tool_spec.get("name") or "").strip()
    return str(tool_spec or "").strip()


def _tool_name_list(suggested_tools):
    return [_extract_tool_name(tool) for tool in (suggested_tools or []) if _extract_tool_name(tool)]


def _looks_like_host_runtime_lookup(user_text):
    return "host" in str(user_text or "").lower() and "ip" in str(user_text or "").lower()


def _should_prioritize_skill_catalog_route(verified_plan, user_text):
    return bool((verified_plan or {}).get("resolution_strategy") == "skill_catalog_context")


def _select_read_only_skill_tool_for_query(user_text, verified_plan):
    if "draft" in str(user_text or "").lower():
        return "list_draft_skills"
    return "list_skills"


def test_looks_like_host_runtime_lookup_requires_target_and_lookup_verb():
    assert looks_like_host_runtime_lookup("finde bitte die host ip adresse") is True
    assert looks_like_host_runtime_lookup("host ip adresse") is False
    assert looks_like_host_runtime_lookup("prüfe bitte die logs") is False


def test_container_state_has_active_target_detects_ids_and_running_rows():
    assert container_state_has_active_target({"last_active_container_id": "ctr-1"}) is True
    assert container_state_has_active_target({"home_container_id": "home-1"}) is True
    assert container_state_has_active_target(
        {"known_containers": [{"status": "running"}, {"status": "exited"}]}
    ) is True
    assert container_state_has_active_target({"known_containers": [{"status": "exited"}]}) is False


def test_container_query_classifiers_split_capability_inventory_blueprint_binding_and_request():
    assert is_active_container_capability_query(
        "was kannst du in diesem container tun?",
        active_container_capability_exclude_markers=["blueprint", "starten"],
        active_container_deictic_markers=["diesem container", "dieser container"],
        active_container_capability_markers=["kannst du", "tun"],
    ) is True
    assert is_container_request_query(
        "starte bitte einen neuen container",
        container_request_query_markers=["starte", "deploy", "neuen container"],
    ) is True
    assert is_container_blueprint_catalog_query(
        "welche blueprints gibt es?",
        container_blueprint_query_markers=["blueprints", "vorlagen"],
        is_container_request_query_fn=lambda text: is_container_request_query(
            text,
            container_request_query_markers=["starte", "deploy", "neuen container"],
        ),
    ) is True
    assert is_container_inventory_query(
        "welche container laufen gerade?",
        container_inventory_query_markers=["welche container", "laufen", "gestoppt"],
        is_container_blueprint_catalog_query_fn=lambda text: is_container_blueprint_catalog_query(
            text,
            container_blueprint_query_markers=["blueprints", "vorlagen"],
            is_container_request_query_fn=lambda inner: is_container_request_query(
                inner,
                container_request_query_markers=["starte", "deploy", "neuen container"],
            ),
        ),
        is_container_request_query_fn=lambda text: is_container_request_query(
            text,
            container_request_query_markers=["starte", "deploy", "neuen container"],
        ),
    ) is True
    assert is_container_state_binding_query(
        "verwende diesen container für den nächsten schritt",
        container_state_query_markers=["verwende", "diesen container", "nächsten schritt"],
        is_active_container_capability_query_fn=lambda text: is_active_container_capability_query(
            text,
            active_container_capability_exclude_markers=["blueprint", "starten"],
            active_container_deictic_markers=["diesem container", "dieser container"],
            active_container_capability_markers=["kannst du", "tun"],
        ),
    ) is True


def test_skill_catalog_context_query_and_priority_respect_exclusions_and_resolution():
    assert is_skill_catalog_context_query(
        "zeige mir meine skills und tools",
        skill_catalog_exclude_markers=["skill ausführen", "run skill"],
        skill_catalog_query_markers=["skills", "tools", "draft skills"],
    ) is True
    assert is_skill_catalog_context_query(
        "run skill test_skill",
        skill_catalog_exclude_markers=["run skill", "skill ausführen"],
        skill_catalog_query_markers=["skills", "tools", "draft skills"],
    ) is False

    assert should_prioritize_skill_catalog_route(
        {"resolution_strategy": "skill_catalog_context"},
        user_text="",
        get_effective_resolution_strategy_fn=get_effective_resolution_strategy,
        is_skill_catalog_context_query_fn=lambda _text: False,
    ) is True
    assert should_prioritize_skill_catalog_route(
        {},
        user_text="zeige mir skills",
        get_effective_resolution_strategy_fn=get_effective_resolution_strategy,
        is_skill_catalog_context_query_fn=lambda text: "skills" in text,
    ) is True


def _seed_tool(route, *, user_text="", suggested_tools=None, verified_plan=None):
    return seed_tool_for_domain_route(
        route,
        user_text=user_text,
        suggested_tools=suggested_tools,
        verified_plan=verified_plan,
        domain_cron_op_to_tool=DOMAIN_CRON_OP_TO_TOOL,
        domain_container_op_to_tool=DOMAIN_CONTAINER_OP_TO_TOOL,
        domain_container_tools=DOMAIN_CONTAINER_TOOLS,
        should_prioritize_skill_catalog_route_fn=_should_prioritize_skill_catalog_route,
        select_read_only_skill_tool_for_query_fn=_select_read_only_skill_tool_for_query,
        looks_like_host_runtime_lookup_fn=_looks_like_host_runtime_lookup,
        extract_tool_name_fn=_extract_tool_name,
    )


def test_apply_domain_route_to_plan_seeds_exec_for_host_runtime_lookup():
    plan = {"suggested_tools": ["home_read"]}
    signal = {
        "domain_tag": "CONTAINER",
        "domain_locked": True,
        "operation": "unknown",
    }

    out = apply_domain_route_to_plan(
        plan,
        signal,
        user_text="finde die host ip",
        domain_cron_tools=DOMAIN_CRON_TOOLS,
        read_only_skill_tools=READ_ONLY_SKILL_TOOLS,
        domain_skill_tools=DOMAIN_SKILL_TOOLS,
        domain_container_tools=DOMAIN_CONTAINER_TOOLS,
        should_prioritize_skill_catalog_route_fn=_should_prioritize_skill_catalog_route,
        extract_tool_name_fn=_extract_tool_name,
        seed_tool_for_domain_route_fn=_seed_tool,
    )

    assert out["suggested_tools"] == ["exec_in_container"]
    assert out["_domain_tool_seeded"] is True


def test_tool_name_list_filters_empty_entries():
    out = tool_name_list(
        ["list_skills", {"tool": "run_skill"}, {"tool": ""}, None],
        extract_tool_name_fn=_extract_tool_name,
    )

    assert out == ["list_skills", "run_skill"]


def test_get_effective_resolution_strategy_prefers_authoritative_value():
    out = get_effective_resolution_strategy(
        {
            "_authoritative_resolution_strategy": "container_state_binding",
            "resolution_strategy": "container_inventory",
        }
    )

    assert out == "container_state_binding"


def test_select_read_only_skill_tool_for_query_prefers_draft_hint():
    out = select_read_only_skill_tool_for_query(
        "zeige mir meine skills",
        {"strategy_hints": ["draft_skills"]},
    )

    assert out == "list_draft_skills"


def test_materialize_skill_catalog_policy_builds_inventory_read_only_contract():
    verified_plan = {
        "_authoritative_resolution_strategy": "skill_catalog_context",
        "strategy_hints": ["draft_skills", "fact_then_followup"],
        "suggested_tools": ["list_draft_skills", "list_skills"],
    }

    out = materialize_skill_catalog_policy(
        verified_plan,
        effective_resolution_strategy=get_effective_resolution_strategy(verified_plan),
        read_only_skill_tools=READ_ONLY_SKILL_TOOLS,
        skill_action_tools={"autonomous_skill_task", "create_skill", "run_skill"},
        tool_name_list_fn=_tool_name_list,
    )

    assert out["mode"] == "inventory_read_only"
    assert out["required_tools"] == ["list_draft_skills", "list_skills"]
    assert out["force_sections"] == ["Runtime-Skills", "Einordnung", "Wunsch-Skills"]
    assert out["draft_explanation_required"] is True
    assert verified_plan["_skill_catalog_policy"] == out


def test_record_and_finalize_execution_tool_trace_capture_skill_catalog_reroute():
    verified_plan = {
        "_authoritative_resolution_strategy": "skill_catalog_context",
        "suggested_tools": ["autonomous_skill_task"],
        "_domain_tool_seeded": False,
        "_domain_gate": {"dropped": 1},
        "_skill_catalog_domain_priority": True,
    }

    out = finalize_execution_suggested_tools(
        verified_plan,
        ["list_draft_skills"],
        tool_name_list_fn=_tool_name_list,
        record_execution_tool_trace_fn=lambda plan, tools: record_execution_tool_trace(
            plan,
            tools,
            tool_name_list_fn=_tool_name_list,
            get_effective_resolution_strategy_fn=get_effective_resolution_strategy,
        ),
    )

    assert out == ["list_draft_skills"]
    assert verified_plan["_selected_tools_for_prompt"] == ["list_draft_skills"]
    assert verified_plan["_thinking_suggested_tools"] == ["autonomous_skill_task"]
    assert verified_plan["_final_execution_tools"] == ["list_draft_skills"]
    assert verified_plan["_skill_catalog_tool_route"]["status"] == "rerouted"
    assert "skill_catalog_priority" in verified_plan["_skill_catalog_tool_route"]["reason"]


def test_apply_domain_tool_policy_replaces_request_container_on_host_runtime_lookup():
    logs = []
    verified_plan = {
        "_domain_route": {
            "domain_tag": "CONTAINER",
            "domain_locked": True,
            "operation": "deploy",
        }
    }

    out = apply_domain_tool_policy(
        verified_plan,
        ["request_container"],
        user_text="prüfe bitte die host ip im container",
        domain_cron_tools=DOMAIN_CRON_TOOLS,
        read_only_skill_tools=READ_ONLY_SKILL_TOOLS,
        domain_skill_tools=DOMAIN_SKILL_TOOLS,
        domain_container_tools=DOMAIN_CONTAINER_TOOLS,
        should_prioritize_skill_catalog_route_fn=_should_prioritize_skill_catalog_route,
        seed_tool_for_domain_route_fn=_seed_tool,
        looks_like_host_runtime_lookup_fn=_looks_like_host_runtime_lookup,
        extract_tool_name_fn=_extract_tool_name,
        log_info_fn=logs.append,
    )

    assert out == ["exec_in_container"]
    assert any("replaced request_container with exec_in_container" in entry for entry in logs)


def test_rewrite_home_start_request_tools_marks_fast_path():
    logs = []
    verified_plan = {}

    out = rewrite_home_start_request_tools(
        "starte bitte den TRION Home Workspace",
        verified_plan,
        ["request_container", "container_list"],
        is_home_container_start_query_fn=lambda text: "trion home" in text.lower(),
        extract_tool_name_fn=_extract_tool_name,
        log_info_fn=logs.append,
    )

    assert out == ["home_start", "container_list"]
    assert verified_plan["_trion_home_start_fast_path"] is True
    assert verified_plan["needs_chat_history"] is True
    assert any("TRION Home start fast-path" in entry for entry in logs)


def test_prioritize_home_container_tools_prepends_container_discovery_and_normalizes_home_read():
    logs = []
    verified_plan = {"is_fact_query": True}

    out = prioritize_home_container_tools(
        "was weist du über den trion home container?",
        verified_plan,
        ["query_skill_knowledge", {"tool": "home_read", "args": {}}],
        is_home_container_info_query_fn=lambda text: "trion home" in text.lower(),
        extract_tool_name_fn=_extract_tool_name,
        log_info_fn=logs.append,
    )

    assert out == ["container_list", {"tool": "home_read", "args": {"path": "."}}]
    assert verified_plan["needs_chat_history"] is True
    assert any("Home-container routing override" in entry for entry in logs)


def test_prioritize_active_container_capability_tools_prefers_inspect_and_filters_noise():
    logs = []
    verified_plan = {"is_fact_query": True}

    out = prioritize_active_container_capability_tools(
        "was kannst du in diesem container tun?",
        verified_plan,
        ["container_stats", "exec_in_container", "memory_graph_search"],
        conversation_id="conv-cap",
        force=False,
        is_active_container_capability_query_fn=lambda text: "diesem container" in text.lower(),
        get_recent_container_state_fn=lambda conversation_id: {"last_active_container_id": "ctr-1"},
        container_state_has_active_target_fn=lambda state: bool(
            state and state.get("last_active_container_id")
        ),
        extract_tool_name_fn=_extract_tool_name,
        log_info_fn=logs.append,
    )

    assert out == ["container_inspect", "memory_graph_search"]
    assert verified_plan["needs_chat_history"] is True
    assert any("Active-container capability override" in entry for entry in logs)


def test_materialize_container_query_policy_for_blueprint_catalog():
    verified_plan = {}

    out = materialize_container_query_policy(
        verified_plan,
        strategy="container_blueprint_catalog",
    )

    assert out == {
        "query_class": "container_blueprint_catalog",
        "required_tools": ["blueprint_list"],
        "truth_mode": "blueprint_catalog",
    }
    assert verified_plan["_container_query_policy"] == out


def test_apply_container_query_policy_prefers_container_inspect_for_binding_with_active_target():
    logs = []
    verified_plan = {"_authoritative_resolution_strategy": "container_state_binding"}

    out = apply_container_query_policy(
        "welcher container ist gerade aktiv?",
        verified_plan,
        ["container_list", "container_stats"],
        conversation_id="conv-1",
        get_effective_resolution_strategy_fn=lambda plan: str(
            (plan or {}).get("_authoritative_resolution_strategy") or ""
        ),
        is_active_container_capability_query_fn=lambda text: False,
        is_container_state_binding_query_fn=lambda text: "aktiv" in text.lower(),
        is_container_blueprint_catalog_query_fn=lambda text: False,
        is_container_request_query_fn=lambda text: False,
        is_container_inventory_query_fn=lambda text: False,
        materialize_container_query_policy_fn=lambda plan, strategy: materialize_container_query_policy(
            plan,
            strategy=strategy,
        ),
        get_recent_container_state_fn=lambda conversation_id: {
            "last_active_container_id": "ctr-1",
            "known_containers": [{"container_id": "ctr-1", "status": "running"}],
        },
        container_state_has_active_target_fn=lambda state: bool(
            state and state.get("last_active_container_id")
        ),
        is_home_container_start_query_fn=lambda text: False,
        extract_tool_name_fn=_extract_tool_name,
        tool_name_list_fn=_tool_name_list,
        log_info_fn=logs.append,
    )

    assert out == ["container_inspect"]
    assert verified_plan["needs_chat_history"] is True
    assert verified_plan["_container_query_policy"]["query_class"] == "container_state_binding"
    assert verified_plan["_container_query_policy"]["selected_tools"] == ["container_inspect"]
    assert any("strategy=container_state_binding" in entry for entry in logs)


def test_apply_container_query_policy_marks_home_start_reuse_mode():
    verified_plan = {"_authoritative_resolution_strategy": "container_request"}

    out = apply_container_query_policy(
        "starte bitte den TRION Home Workspace",
        verified_plan,
        ["request_container"],
        conversation_id="conv-2",
        get_effective_resolution_strategy_fn=lambda plan: str(
            (plan or {}).get("_authoritative_resolution_strategy") or ""
        ),
        is_active_container_capability_query_fn=lambda text: False,
        is_container_state_binding_query_fn=lambda text: False,
        is_container_blueprint_catalog_query_fn=lambda text: False,
        is_container_request_query_fn=lambda text: True,
        is_container_inventory_query_fn=lambda text: False,
        materialize_container_query_policy_fn=lambda plan, strategy: materialize_container_query_policy(
            plan,
            strategy=strategy,
        ),
        get_recent_container_state_fn=lambda conversation_id: {},
        container_state_has_active_target_fn=lambda state: False,
        is_home_container_start_query_fn=lambda text: "trion home" in text.lower(),
        extract_tool_name_fn=_extract_tool_name,
        tool_name_list_fn=_tool_name_list,
        log_info_fn=lambda msg: None,
    )

    assert out == ["home_start"]
    assert verified_plan["_trion_home_start_fast_path"] is True
    assert verified_plan["needs_chat_history"] is True
    assert verified_plan["_container_query_policy"]["truth_mode"] == "home_start_reuse"
    assert verified_plan["_container_query_policy"]["selected_tools"] == ["home_start"]


def test_apply_container_query_policy_preserves_task_loop_blueprint_discovery_step():
    logs = []
    verified_plan = {
        "_task_loop_step_runtime": True,
        "_authoritative_resolution_strategy": "container_request",
    }

    out = apply_container_query_policy(
        "Task-Loop Schritt 2/5",
        verified_plan,
        ["blueprint_list"],
        conversation_id="conv-loop",
        get_effective_resolution_strategy_fn=lambda plan: str(
            (plan or {}).get("_authoritative_resolution_strategy") or ""
        ),
        is_active_container_capability_query_fn=lambda text: False,
        is_container_state_binding_query_fn=lambda text: False,
        is_container_blueprint_catalog_query_fn=lambda text: False,
        is_container_request_query_fn=lambda text: True,
        is_container_inventory_query_fn=lambda text: False,
        materialize_container_query_policy_fn=lambda plan, strategy: materialize_container_query_policy(
            plan,
            strategy=strategy,
        ),
        get_recent_container_state_fn=lambda conversation_id: {},
        container_state_has_active_target_fn=lambda state: False,
        is_home_container_start_query_fn=lambda text: False,
        extract_tool_name_fn=_extract_tool_name,
        tool_name_list_fn=_tool_name_list,
        log_info_fn=logs.append,
    )

    assert out == ["blueprint_list"]
    assert verified_plan["_container_query_policy"]["query_class"] == "container_blueprint_catalog"
    assert verified_plan["_container_query_policy"]["selected_tools"] == ["blueprint_list"]
    assert any("Task-loop container discovery preserved" in entry for entry in logs)
