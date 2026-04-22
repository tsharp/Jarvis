from core.tool_intelligence.reflection_loop import _extract_errors_from_context


def test_extract_errors_from_context_parses_legacy_tool_fehler_block():
    ctx = """
### TOOL-FEHLER (home_read):
No such file or directory
Try home_list instead.
"""

    assert _extract_errors_from_context(ctx) == [
        {
            "tool": "home_read",
            "error": "No such file or directory | Try home_list instead.",
        }
    ]


def test_extract_errors_from_context_parses_error_tool_card_blocks():
    ctx = """
[TOOL-CARD: exec_in_container | ❌ error | ref:abc123]
- permission denied
- container is not running
ts:2026-04-21T00:00:00Z
"""

    assert _extract_errors_from_context(ctx) == [
        {
            "tool": "exec_in_container",
            "error": "permission denied | container is not running",
        }
    ]


def test_extract_errors_from_context_dedupes_legacy_header_and_error_card():
    ctx = """
### TOOL-FEHLER (exec_in_container):
[TOOL-CARD: exec_in_container | ❌ error | ref:abc123]
- permission denied
ts:2026-04-21T00:00:00Z
"""

    assert _extract_errors_from_context(ctx) == [
        {
            "tool": "exec_in_container",
            "error": "permission denied",
        }
    ]
