"""
Fix #9: NameError: name 'chat_history' is not defined

Ursache: Im Blueprint-Router-Block in process_stream_with_events()
wird `chat_history` als bare Variable referenziert, obwohl sie kein Parameter
der Funktion ist. Getriggert wenn request_container in suggested_tools und
needs_chat_history=False (z.B. Gaming/Steam-Container Request).

Fix: `chat_history` → `getattr(request, "messages", None)`

Die Blueprint-Router-Logik wurde in run_pre_control_gates (pipeline_stages.py)
extrahiert, wo sie korrekt getattr(request, "messages", None) nutzt.
"""
import ast
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def _stream_src() -> str:
    return (ROOT / "core/orchestrator_stream_flow_utils.py").read_text(encoding="utf-8")


def _stages_src() -> str:
    return (ROOT / "core/orchestrator_pipeline_stages.py").read_text(encoding="utf-8")


def test_chat_history_bare_name_gone_from_blueprint_router_block():
    """run_pre_control_gates (pipeline_stages) must not use bare 'chat_history' variable."""
    src = _stages_src()
    # Isolate the Container Candidate Evidence block
    block_start = src.find("Container Candidate Evidence")
    assert block_start != -1, "Container Candidate Evidence block not found in pipeline_stages"
    # Take next ~80 lines as the block
    block = src[block_start:block_start + 2500]

    bad_occurrences = []
    for line in block.splitlines():
        stripped = line.strip()
        if stripped.startswith("#"):
            continue
        if re.search(r'(?<!needs_)\bchat_history\b', stripped):
            if "getattr(request" not in stripped and '"needs_chat_history"' not in stripped:
                bad_occurrences.append(stripped)

    assert not bad_occurrences, (
        f"Bare 'chat_history' still present in pipeline_stages blueprint block:\n"
        + "\n".join(bad_occurrences)
    )


def test_blueprint_router_block_uses_getattr_request_messages():
    """run_pre_control_gates must use getattr(request, 'messages', None) for chat history."""
    src = _stages_src()
    block_start = src.find("Container Candidate Evidence")
    assert block_start != -1
    block = src[block_start:block_start + 2500]
    assert 'getattr(request, "messages", None)' in block or "getattr(request, 'messages', None)" in block, (
        "run_pre_control_gates must use getattr(request, 'messages', None)"
    )


def test_process_stream_with_events_has_no_chat_history_param():
    """process_stream_with_events must NOT have chat_history as a parameter (confirm root cause context)."""
    src = _stream_src()
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
    src = _stream_src()
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
