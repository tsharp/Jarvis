from datetime import datetime
from unittest.mock import MagicMock

from core.orchestrator_workspace_event_runtime_utils import (
    build_container_event_content,
    save_container_event,
    save_workspace_entry,
)


def test_build_container_event_content_emits_start_event():
    out = build_container_event_content(
        "home_start",
        {
            "status": "running",
            "container_id": "ctr-home",
            "blueprint_id": "trion-home",
            "name": "TRION Home Workspace",
        },
        "starte bitte den TRION Home Workspace",
        {},
        session_id="conv-home",
        utcnow_fn=lambda: datetime(2026, 4, 8, 12, 0, 0),
        resolve_exec_blueprint_id_fn=lambda _cid, _args: "ignored",
    )

    assert out is not None
    assert out["event_type"] == "container_started"
    assert out["event_data"]["container_id"] == "ctr-home"
    assert out["event_data"]["blueprint_id"] == "trion-home"
    assert out["event_data"]["session_id"] == "conv-home"


def test_build_container_event_content_resolves_exec_blueprint_id():
    out = build_container_event_content(
        "exec_in_container",
        {
            "container_id": "ctr-1",
            "exit_code": 0,
            "output": "ok",
        },
        "run command",
        {"container_id": "ctr-1", "command": "ls -la"},
        session_id="conv-exec",
        utcnow_fn=lambda: datetime(2026, 4, 8, 12, 1, 0),
        resolve_exec_blueprint_id_fn=lambda cid, args: f"bp::{cid}::{args['command']}",
    )

    assert out is not None
    assert out["event_type"] == "container_exec"
    assert out["event_data"]["blueprint_id"] == "bp::ctr-1::ls -la"
    assert out["event_data"]["exit_code"] == 0


def test_save_workspace_entry_delegates_to_emitter():
    emitter = MagicMock()
    emitter.persist.return_value.sse_dict = {"type": "workspace_update", "entry_id": 1}

    out = save_workspace_entry(
        "conv-1",
        "content",
        entry_type="task",
        source_layer="control",
        get_workspace_emitter_fn=lambda: emitter,
    )

    assert out == {"type": "workspace_update", "entry_id": 1}
    emitter.persist.assert_called_once_with(
        conversation_id="conv-1",
        content="content",
        entry_type="task",
        source_layer="control",
    )


def test_save_container_event_delegates_to_emitter():
    emitter = MagicMock()
    emitter.persist_container.return_value.sse_dict = {"type": "workspace_update", "entry_id": 2}
    evt = {"event_type": "container_started", "event_data": {"container_id": "ctr-1"}}

    out = save_container_event(
        "conv-2",
        evt,
        get_workspace_emitter_fn=lambda: emitter,
    )

    assert out == {"type": "workspace_update", "entry_id": 2}
    emitter.persist_container.assert_called_once_with(
        conversation_id="conv-2",
        container_evt=evt,
    )
