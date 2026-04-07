"""
Contract tests: MemoryResolution Domaenobjekt

Prueft:
- from_context_result() baut korrekt aus ContextResult + Thinking-Plan
- required_missing=True nur wenn needs_memory UND missing_keys vorhanden
- to_trace() liefert alle rueckwaertskompatiblen Keys
- build_effective_context() gibt 3-Tupel zurueck
- Tupel[2].required_missing stimmt mit bisherigem Guard-Ergebnis ueberein
"""

from unittest.mock import MagicMock, patch
from core.memory_resolution import MemoryResolution


# ---------------------------------------------------------------------------
# from_context_result()
# ---------------------------------------------------------------------------

def _make_ctx(requested=None, found=None, not_found=None):
    ctx = MagicMock()
    ctx.memory_keys_requested = requested or []
    ctx.memory_keys_found = found or []
    ctx.memory_keys_not_found = not_found or []
    return ctx


def test_required_missing_true_when_needs_memory_and_missing():
    ctx = _make_ctx(requested=["user_name"], not_found=["user_name"])
    plan = {"needs_memory": True}
    res = MemoryResolution.from_context_result(ctx, plan)
    assert res.required_missing is True
    assert res.missing_keys == ["user_name"]


def test_required_missing_false_when_key_found():
    ctx = _make_ctx(requested=["user_name"], found=["user_name"])
    plan = {"needs_memory": True}
    res = MemoryResolution.from_context_result(ctx, plan)
    assert res.required_missing is False
    assert res.found_keys == ["user_name"]
    assert res.missing_keys == []


def test_required_missing_false_without_needs_memory():
    ctx = _make_ctx(requested=["user_name"], not_found=["user_name"])
    plan = {"needs_memory": False}
    res = MemoryResolution.from_context_result(ctx, plan)
    assert res.required_missing is False


def test_required_missing_true_for_is_fact_query():
    ctx = _make_ctx(requested=["fav_color"], not_found=["fav_color"])
    plan = {"needs_memory": False, "is_fact_query": True}
    res = MemoryResolution.from_context_result(ctx, plan)
    assert res.required_missing is True


def test_required_missing_false_when_no_keys_requested():
    ctx = _make_ctx()
    plan = {"needs_memory": True}
    res = MemoryResolution.from_context_result(ctx, plan)
    assert res.required_missing is False
    assert res.requested_keys == []


def test_all_fields_populated_correctly():
    ctx = _make_ctx(
        requested=["user_name", "preferences"],
        found=["preferences"],
        not_found=["user_name"],
    )
    plan = {"needs_memory": True}
    res = MemoryResolution.from_context_result(ctx, plan)
    assert res.requested_keys == ["user_name", "preferences"]
    assert res.found_keys == ["preferences"]
    assert res.missing_keys == ["user_name"]
    assert res.required_missing is True


# ---------------------------------------------------------------------------
# to_trace()
# ---------------------------------------------------------------------------

def test_to_trace_contains_all_expected_keys():
    res = MemoryResolution(
        requested_keys=["user_name"],
        found_keys=[],
        missing_keys=["user_name"],
        required_missing=True,
    )
    trace = res.to_trace()
    assert "memory_keys_requested" in trace
    assert "memory_keys_found" in trace
    assert "memory_keys_not_found" in trace
    assert "memory_required_but_missing" in trace


def test_to_trace_values_match_fields():
    res = MemoryResolution(
        requested_keys=["a"],
        found_keys=["b"],
        missing_keys=["c"],
        required_missing=True,
    )
    trace = res.to_trace()
    assert trace["memory_keys_requested"] == ["a"]
    assert trace["memory_keys_found"] == ["b"]
    assert trace["memory_keys_not_found"] == ["c"]
    assert trace["memory_required_but_missing"] is True


def test_to_trace_required_missing_false():
    res = MemoryResolution()
    trace = res.to_trace()
    assert trace["memory_required_but_missing"] is False


# ---------------------------------------------------------------------------
# build_effective_context() — 3-Tupel
# ---------------------------------------------------------------------------

def test_build_effective_context_returns_three_tuple():
    from core.orchestrator_flow_utils import build_effective_context

    mock_ctx = MagicMock()
    mock_ctx.memory_used = False
    mock_ctx.system_tools = ""
    mock_ctx.memory_data = ""
    mock_ctx.memory_keys_requested = ["user_name"]
    mock_ctx.memory_keys_found = []
    mock_ctx.memory_keys_not_found = ["user_name"]

    mock_orch = MagicMock()
    mock_orch.context.get_context.return_value = mock_ctx
    mock_orch._get_compact_context.return_value = ""

    with patch("config.get_context_trace_dryrun", return_value=False), \
         patch("config.get_small_model_char_cap", return_value=10000):
        result = build_effective_context(
            mock_orch,
            "wie heiße ich?",
            "conv-test",
            small_model_mode=True,
            cleanup_payload={"needs_memory": True, "memory_keys": ["user_name"]},
        )

    assert len(result) == 3, "build_effective_context muss ein 3-Tupel zurueckgeben"
    text, trace, resolution = result
    assert isinstance(text, str)
    assert isinstance(trace, dict)
    assert isinstance(resolution, MemoryResolution)


def test_build_effective_context_resolution_required_missing_true():
    from core.orchestrator_flow_utils import build_effective_context

    mock_ctx = MagicMock()
    mock_ctx.memory_used = False
    mock_ctx.system_tools = ""
    mock_ctx.memory_data = ""
    mock_ctx.memory_keys_requested = ["user_name"]
    mock_ctx.memory_keys_found = []
    mock_ctx.memory_keys_not_found = ["user_name"]

    mock_orch = MagicMock()
    mock_orch.context.get_context.return_value = mock_ctx
    mock_orch._get_compact_context.return_value = ""

    with patch("config.get_context_trace_dryrun", return_value=False), \
         patch("config.get_small_model_char_cap", return_value=10000):
        _, trace, resolution = build_effective_context(
            mock_orch,
            "wie heiße ich?",
            "conv-test",
            small_model_mode=True,
            cleanup_payload={"needs_memory": True, "memory_keys": ["user_name"]},
        )

    assert resolution.required_missing is True
    # Trace ist rueckwaertskompatibel befuellt
    assert trace["memory_required_but_missing"] is True
    assert trace["memory_keys_not_found"] == ["user_name"]


def test_build_effective_context_resolution_required_missing_false_when_found():
    from core.orchestrator_flow_utils import build_effective_context

    mock_ctx = MagicMock()
    mock_ctx.memory_used = True
    mock_ctx.system_tools = ""
    mock_ctx.memory_data = "user_name=Danny"
    mock_ctx.memory_keys_requested = ["user_name"]
    mock_ctx.memory_keys_found = ["user_name"]
    mock_ctx.memory_keys_not_found = []

    mock_orch = MagicMock()
    mock_orch.context.get_context.return_value = mock_ctx
    mock_orch._get_compact_context.return_value = ""

    with patch("config.get_context_trace_dryrun", return_value=False), \
         patch("config.get_small_model_char_cap", return_value=10000):
        _, _, resolution = build_effective_context(
            mock_orch,
            "wie heiße ich?",
            "conv-test",
            small_model_mode=True,
            cleanup_payload={"needs_memory": True, "memory_keys": ["user_name"]},
        )

    assert resolution.required_missing is False
