from pathlib import Path


def _read(path: str) -> str:
    root = Path(__file__).resolve().parents[2]
    return (root / path).read_text(encoding="utf-8")


def test_ws_stream_separates_log_and_shell_output_channels():
    src = _read("container_commander/ws_stream.py")
    assert '"stream": "logs"' in src
    assert '"stream": "shell"' in src


def test_ws_stream_tracks_exec_sessions_per_ws_and_container():
    src = _read("container_commander/ws_stream.py")
    assert "SessionKey = Tuple[int, str]" in src
    assert "_exec_sessions: Dict[SessionKey, ExecSession] = {}" in src
    assert "_ws_exec_index: Dict[WebSocket, Set[SessionKey]] = {}" in src
    assert "def _session_key(ws: WebSocket, container_id: str) -> SessionKey:" in src


def test_ws_stream_resize_targets_exec_session_not_container_resize():
    src = _read("container_commander/ws_stream.py")
    assert "client.api.exec_resize(session.exec_id, height=rows, width=cols)" in src


def test_ws_stream_exposes_unified_activity_emitter():
    src = _read("container_commander/ws_stream.py")
    assert "def emit_activity(event: str, level: str = \"info\", message: str = \"\", **data):" in src
    assert "broadcast_event_sync(event, payload_without_event)" in src


def test_ws_stream_broadcast_event_no_unbound_local_on_dead_cleanup():
    """
    Regression guard for UnboundLocalError in broadcast_event.

    `_connections -= dead` is an augmented assignment which causes Python to
    compile `_connections` as a local variable, making the earlier
    `for ws in _connections` read an uninitialised local → UnboundLocalError.
    The fix is `_connections.difference_update(dead)` (in-place, no rebind).
    """
    src = _read("container_commander/ws_stream.py")
    # Must NOT contain the rebinding form
    assert "_connections -= dead" not in src
    # Must use the in-place mutation form
    assert "_connections.difference_update(dead)" in src


def test_ws_stream_broadcast_event_dead_set_and_cleanup_pattern():
    """
    Contract: broadcast_event must collect dead connections and remove them
    via difference_update — never via augmented assignment.
    """
    src = _read("container_commander/ws_stream.py")
    # Must track dead connections
    assert "dead = set()" in src
    assert "dead.add(ws)" in src
    # Must clean up using in-place mutation (no rebind → no UnboundLocalError)
    assert "_connections.difference_update(dead)" in src


def test_ws_stream_registers_exec_session_before_starting_read_task():
    src = _read("container_commander/ws_stream.py")
    register_idx = src.index("_exec_sessions[key] = session")
    create_task_idx = src.index("session.read_task = asyncio.create_task(_read_pty_output(ws, container_id, key))")
    assert register_idx < create_task_idx


def test_ws_stream_reads_follow_logs_off_event_loop():
    src = _read("container_commander/ws_stream.py")
    assert "chunk = await loop.run_in_executor(None, lambda: _next_log_chunk(log_stream))" in src
    assert "def _next_log_chunk(log_stream: Any) -> Optional[bytes]:" in src
