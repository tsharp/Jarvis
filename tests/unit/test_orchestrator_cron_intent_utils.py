from datetime import datetime

from core.orchestrator_cron_intent_utils import (
    bind_cron_conversation_id,
    build_direct_cron_create_response,
    contains_explicit_skill_intent,
    contains_explicit_tool_intent,
    extract_one_shot_run_at_from_text,
    extract_tool_domain_tag,
    normalize_tools,
    prevalidate_cron_policy_args,
)
from core.orchestrator_policy_catalog import (
    CRON_META_GUARD_MARKERS,
    SKILL_INTENT_KEYWORDS,
    SKILL_INTENT_WORD_KEYWORDS,
    TOOL_DOMAIN_TAG_RE,
    TOOL_DOMAIN_TAG_SHORT_RE,
    TOOL_INTENT_KEYWORDS,
    TOOL_INTENT_WORD_KEYWORDS,
)


def test_extract_tool_domain_tag_and_explicit_intent_helpers():
    extract_tag = lambda text: extract_tool_domain_tag(
        text,
        tool_domain_tag_re=TOOL_DOMAIN_TAG_RE,
        tool_domain_tag_short_re=TOOL_DOMAIN_TAG_SHORT_RE,
    )

    assert extract_tag("{TOOL:MCP_CALL} probe") == "MCP_CALL"
    assert contains_explicit_tool_intent(
        "{CRONJOB} erstelle einen job",
        extract_tool_domain_tag_fn=extract_tag,
        contains_keyword_intent_fn=lambda text, keyword, whole_word=False: (
            keyword in text if not whole_word else f" {keyword} " in f" {text} "
        ),
        tool_intent_keywords=TOOL_INTENT_KEYWORDS,
        tool_intent_word_keywords=TOOL_INTENT_WORD_KEYWORDS,
    ) is True
    assert contains_explicit_skill_intent(
        "Bitte starte den Skill diagnostics.",
        extract_tool_domain_tag_fn=extract_tag,
        contains_keyword_intent_fn=lambda text, keyword, whole_word=False: (
            keyword in text if not whole_word else f" {keyword} " in f" {text} "
        ),
        skill_intent_keywords=SKILL_INTENT_KEYWORDS,
        skill_intent_word_keywords=SKILL_INTENT_WORD_KEYWORDS,
    ) is True


def test_extract_one_shot_run_at_rounds_up_safely():
    class _FixedDateTime(datetime):
        @classmethod
        def utcnow(cls):
            return cls(2026, 3, 9, 22, 48, 50)

    run_at = extract_one_shot_run_at_from_text(
        "erstelle einen cronjob in 1 minute",
        verified_plan={},
        datetime_cls=_FixedDateTime,
    )

    assert run_at == "2026-03-09T22:50:00Z"


def test_build_direct_cron_create_response_and_bind_conversation():
    tool_args = {
        "name": "cron-test",
        "objective": "user_request::kannst du mir sagen wie du dich beim trigger fühlst?",
        "conversation_id": "webui-default",
    }
    bind_cron_conversation_id(
        "autonomy_cron_create_job",
        tool_args,
        "webui-2",
        log_info_fn=lambda _msg: None,
    )

    text = build_direct_cron_create_response(
        {
            "id": "abc124",
            "name": "cron-self-state",
            "objective": tool_args["objective"],
            "schedule_mode": "one_shot",
            "run_at": "2026-03-09T16:05:00+00:00",
            "conversation_id": tool_args["conversation_id"],
        },
        tool_args={},
        conversation_id="webui-2",
        detect_tool_error_fn=lambda payload: (False, ""),
        format_utc_compact_fn=lambda raw: "2026-03-09 16:05 UTC",
        extract_cron_ack_message_from_objective_fn=lambda objective: "Selbststatus beim Trigger ausgeben.",
    )

    assert tool_args["conversation_id"] == "webui-2"
    assert "Selbststatus beim Trigger ausgeben." in text


def test_prevalidate_cron_policy_args_auto_heals_small_past_drift():
    class _FixedDateTime(datetime):
        @classmethod
        def utcnow(cls):
            return cls(2026, 3, 9, 22, 49, 20)

    args = {"schedule_mode": "one_shot", "run_at": "2026-03-09T22:49:00Z"}
    ok, reason = prevalidate_cron_policy_args(
        "autonomy_cron_create_job",
        args,
        datetime_cls=_FixedDateTime,
        suggest_cron_expression_for_min_interval_fn=lambda min_s: "*/5 * * * *",
        extract_interval_hint_from_cron_fn=lambda expr: {"minutes": 5},
    )

    assert ok is True
    assert reason == ""
    assert args["run_at"] == "2026-03-09T22:50:00Z"


def test_normalize_tools_maps_installed_skill_and_filters_home_write():
    class _FakeHub:
        _tool_definitions = {}

        def initialize(self):
            return None

        def call_tool(self, tool_name, args):
            assert tool_name == "list_skills"
            return {"structuredContent": {"installed": [{"name": "diagnostics"}]}}

        def get_mcp_for_tool(self, tool_name):
            return None

    out = normalize_tools(
        ["diagnostics", "home_write", "exec_in_container"],
        get_hub_fn=lambda: _FakeHub(),
        log_info_fn=lambda _msg: None,
    )

    assert any(isinstance(item, dict) and item.get("tool") == "run_skill" for item in out)
    assert "home_write" not in out
