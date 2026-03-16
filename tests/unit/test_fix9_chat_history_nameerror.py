"""
Fix #9: NameError: name 'chat_history' is not defined

Ursache: Im Blueprint-Router-Block (STEP 1.8) in process_stream_with_events()
wird `chat_history` als bare Variable referenziert, obwohl sie kein Parameter
der Funktion ist. Getriggert wenn request_container in suggested_tools und
needs_chat_history=False (z.B. Gaming/Steam-Container Request).

Fix: `chat_history` → `getattr(request, "messages", None)`
"""
import ast
import re
from pathlib import Path


def _src() -> str:
    root = Path(__file__).resolve().parents[2]
    return (root / "core/orchestrator_stream_flow_utils.py").read_text(encoding="utf-8")


def test_chat_history_bare_name_gone_from_blueprint_router_block():
    """The bare name 'chat_history' must not appear in the STEP 1.8 block anymore."""
    src = _src()
    # Isolate the STEP 1.8 block
    step18_start = src.find("STEP 1.8: BLUEPRINT ROUTER")
    assert step18_start != -1, "STEP 1.8 block not found"
    # Find next STEP after 1.8
    step_next = src.find("# STEP ", step18_start + 50)
    if step_next == -1:
        step_next = step18_start + 2000  # fallback: take enough context
    block = src[step18_start:step_next]

    # Must NOT contain bare `chat_history` variable (only as part of getattr call or request.messages)
    # Simple check: find `chat_history` not preceded by "request." and not in comment
    bad_occurrences = []
    for line in block.splitlines():
        stripped = line.strip()
        if stripped.startswith("#"):
            continue
        # Match standalone `chat_history` variable (not as part of needs_chat_history, getattr, or string literal)
        # Pattern: `chat_history` that is NOT preceded by `needs_` and NOT in getattr call
        if re.search(r'(?<!needs_)\bchat_history\b', stripped):
            # Exclude getattr(request, "messages") assignment and string literals
            if "getattr(request" not in stripped and '"needs_chat_history"' not in stripped:
                bad_occurrences.append(stripped)

    assert not bad_occurrences, (
        f"Bare 'chat_history' still present in STEP 1.8 block:\n" + "\n".join(bad_occurrences)
    )


def test_blueprint_router_block_uses_getattr_request_messages():
    """The A3-Fix branch must use getattr(request, 'messages', None) instead of chat_history."""
    src = _src()
    step18_start = src.find("STEP 1.8: BLUEPRINT ROUTER")
    assert step18_start != -1
    block = src[step18_start:step18_start + 2000]
    assert 'getattr(request, "messages", None)' in block or "getattr(request, 'messages', None)" in block, (
        "Blueprint router A3 block must use getattr(request, 'messages', None)"
    )


def test_process_stream_with_events_has_no_chat_history_param():
    """process_stream_with_events must NOT have chat_history as a parameter (confirm root cause context)."""
    src = _src()
    # Find function signature
    fn_start = src.find("async def process_stream_with_events(")
    assert fn_start != -1, "process_stream_with_events not found"
    sig_end = src.find("):", fn_start)
    signature = src[fn_start:sig_end + 2]
    assert "chat_history" not in signature, (
        "chat_history should NOT be a direct parameter of process_stream_with_events"
    )


def test_no_other_bare_chat_history_in_process_stream_with_events():
    """No other bare chat_history references should exist inside process_stream_with_events body."""
    src = _src()
    fn_start = src.find("async def process_stream_with_events(")
    assert fn_start != -1
    # Find end of function (next top-level async def / def)
    fn_body_start = src.find(":", fn_start) + 1
    # Find next async def at same indentation level (0)
    next_fn = re.search(r'\n(?:async )?def \w+', src[fn_body_start:])
    fn_end = fn_body_start + next_fn.start() if next_fn else len(src)
    body = src[fn_body_start:fn_end]

    bare_refs = []
    for i, line in enumerate(body.splitlines(), 1):
        stripped = line.strip()
        if stripped.startswith("#"):
            continue
        # Standalone `chat_history` var: not `needs_chat_history`, not `chat_history=request.messages`,
        # not a string literal containing "needs_chat_history", not inside getattr()
        if re.search(r'(?<!needs_)\bchat_history\b', stripped):
            # Allowed: assignment `chat_history=request.messages`, string key, getattr call
            if ("chat_history=request.messages" in stripped
                    or '"needs_chat_history"' in stripped
                    or "'needs_chat_history'" in stripped
                    or "getattr(request" in stripped):
                continue
            bare_refs.append((i, stripped))

    assert not bare_refs, (
        "Unexpected bare 'chat_history' references in process_stream_with_events body:\n"
        + "\n".join(f"  L{ln}: {txt}" for ln, txt in bare_refs)
    )
