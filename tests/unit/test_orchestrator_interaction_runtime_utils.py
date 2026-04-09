from unittest.mock import patch

from core.orchestrator_interaction_runtime_utils import (
    apply_response_mode_policy,
    detect_skill_by_trigger,
    detect_tools_by_keyword,
    extract_requested_skill_name,
    extract_tool_name,
    filter_think_tools,
    is_explicit_deep_request,
    is_explicit_think_request,
    is_home_container_info_query,
    is_home_container_start_query,
    recover_home_read_directory_with_fast_lane,
    resolve_runtime_output_model,
    route_blueprint_request,
    route_skill_request,
    sanitize_skill_name_candidate,
)


def test_recover_home_read_directory_with_fast_lane_reads_listing_and_files():
    class _Result:
        def __init__(self, content):
            self.content = content

    class _FastLane:
        def execute(self, tool_name, args):
            if tool_name == "home_list":
                return _Result(["foo.txt", "bar/"])
            if tool_name == "home_read":
                return _Result("hello")
            raise AssertionError(tool_name)

    ok, payload = recover_home_read_directory_with_fast_lane(
        ".",
        fast_lane_executor_cls=_FastLane,
    )

    assert ok is True
    assert "listing:" in payload
    assert "file[foo.txt]: hello" in payload


def test_extract_requested_skill_name_sanitizes_valid_name():
    out = extract_requested_skill_name(
        "Bitte führe den Skill system-hardware-info aus",
        sanitize_skill_name_candidate_fn=sanitize_skill_name_candidate,
    )
    assert out == "system_hardware_info"


def test_filter_think_tools_drops_think_when_not_needed():
    out = filter_think_tools(
        ["think", "list_skills"],
        user_text="zeige skills",
        thinking_plan={"_response_mode": "interactive"},
        source="unit",
        is_explicit_think_request_fn=lambda _text: False,
        extract_tool_name_fn=lambda tool: str(tool),
        log_info_fn=lambda _msg: None,
    )
    assert out == ["list_skills"]


def test_is_explicit_deep_request_detects_marker():
    assert is_explicit_deep_request("Mach bitte eine ausführlichere /deep Analyse") is True


def test_is_explicit_think_request_detects_stepwise_marker():
    assert is_explicit_think_request("Bitte denk schrittweise über das Problem nach") is True


def test_extract_tool_name_prefers_tool_key():
    assert extract_tool_name({"tool": "container_list", "name": "ignored"}) == "container_list"


def test_is_home_container_queries_distinguish_start_vs_info():
    start = is_home_container_start_query(
        "starte den trion home workspace",
        home_container_query_markers=["trion home", "home workspace"],
        home_container_start_markers=["starte", "start"],
    )
    info = is_home_container_info_query(
        "welcher container ist mein trion home container",
        home_container_query_markers=["trion home", "home workspace"],
        home_container_purpose_markers=["welcher", "info", "status"],
        is_home_container_start_query_fn=lambda text: is_home_container_start_query(
            text,
            home_container_query_markers=["trion home", "home workspace"],
            home_container_start_markers=["starte", "start"],
        ),
    )
    assert start is True
    assert info is True


def test_apply_response_mode_policy_defers_heavy_sequential_and_filters_think():
    plan = {
        "needs_sequential_thinking": True,
        "sequential_complexity": 9,
        "suggested_tools": ["think", "list_skills"],
    }

    mode = apply_response_mode_policy(
        "analysiere pipeline",
        plan,
        get_default_response_mode_fn=lambda: "interactive",
        get_response_mode_sequential_threshold_fn=lambda: 7,
        is_explicit_deep_request_fn=lambda _text: False,
        filter_think_tools_fn=lambda tools, **kwargs: [t for t in tools if t != "think"],
        log_info_fn=lambda _msg: None,
    )

    assert mode == "interactive"
    assert plan["_sequential_deferred"] is True
    assert plan["suggested_tools"] == ["list_skills"]


def test_resolve_runtime_output_model_passthrough_for_non_ollama():
    resolved, details = resolve_runtime_output_model(
        "deepseek-v3.1:671b",
        ollama_base="http://ollama:11434",
        get_output_model_fn=lambda: "deepseek-v3.1:671b",
        get_output_provider_fn=lambda: "ollama_cloud",
        resolve_role_endpoint_fn=lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("unused")),
        resolve_runtime_chat_model_fn=lambda **_kwargs: (_ for _ in ()).throw(AssertionError("unused")),
        log_info_fn=lambda _msg: None,
        log_warn_fn=lambda _msg: None,
    )
    assert resolved == "deepseek-v3.1:671b"
    assert details["reason"] == "provider_passthrough_non_ollama"


def test_detect_tools_by_keyword_routes_home_start_and_blueprint_queries():
    out = detect_tools_by_keyword(
        "starte bitte den trion home workspace",
        is_home_container_info_query_fn=lambda _text: False,
        is_home_container_start_query_fn=lambda _text: True,
        is_active_container_capability_query_fn=lambda _text: False,
        is_container_state_binding_query_fn=lambda _text: False,
        is_container_blueprint_catalog_query_fn=lambda _text: False,
        is_container_inventory_query_fn=lambda _text: False,
        is_container_request_query_fn=lambda _text: False,
    )
    assert out == ["home_start"]


def test_detect_skill_by_trigger_returns_best_match():
    class _Resp:
        def __init__(self, payload):
            self._payload = payload

        def read(self):
            return self._payload

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    def _urlopen(url, timeout=2):
        if url.endswith("/v1/skills"):
            return _Resp(b'{"active":["alpha","beta"]}')
        if url.endswith("/v1/skills/alpha"):
            return _Resp(b'{"triggers":["foo"]}')
        if url.endswith("/v1/skills/beta"):
            return _Resp(b'{"triggers":["foo bar"]}')
        raise AssertionError(url)

    out = detect_skill_by_trigger(
        "please run foo bar now",
        skill_server_url="http://skills",
        urlopen_fn=_urlopen,
        log_info_fn=lambda _msg: None,
    )
    assert out == ["beta"]


def test_route_skill_request_respects_env_fallback_disable():
    out = route_skill_request(
        "Erstelle einen Skill",
        {"intent": "create_skill"},
        get_skill_discovery_enable_fn=lambda: (_ for _ in ()).throw(RuntimeError("config missing")),
        env_get_fn=lambda key, default="": "false" if key == "SKILL_DISCOVERY_ENABLE" else default,
        log_info_fn=lambda _msg: None,
        log_error_fn=lambda _msg: None,
    )
    assert out is None


def test_route_skill_request_fail_closed_on_router_exception():
    out = route_skill_request(
        "Erstelle einen Skill",
        {"intent": "create_skill"},
        get_skill_discovery_enable_fn=lambda: True,
        get_skill_router_fn=lambda: (_ for _ in ()).throw(RuntimeError("router down")),
        log_info_fn=lambda _msg: None,
        log_error_fn=lambda _msg: None,
    )
    assert out["blocked"] is True
    assert out["reason"] == "skill_router_unavailable"


def test_route_blueprint_request_returns_suggestion_shape():
    class _Decision:
        decision = "suggest_blueprint"
        blueprint_id = "python-sandbox"
        score = 0.91
        candidates = ["python-sandbox", "node-sandbox"]

    class _Router:
        def route(self, **_kwargs):
            return _Decision()

    out = route_blueprint_request(
        "Starte einen Container",
        {"intent": "container start"},
        get_blueprint_router_fn=lambda: _Router(),
        log_error_fn=lambda _msg: None,
    )
    assert out == {
        "blueprint_id": "python-sandbox",
        "score": 0.91,
        "suggest": True,
        "candidates": ["python-sandbox", "node-sandbox"],
    }
