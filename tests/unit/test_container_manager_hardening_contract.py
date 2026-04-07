import shlex
import subprocess
import threading
import time
from pathlib import Path

import container_commander.approval as approval
from container_commander.models import NetworkMode


def _read(path: str) -> str:
    root = Path(__file__).resolve().parents[2]
    return (root / path).read_text(encoding="utf-8")


def test_engine_exec_timeout_contract_present():
    src = _read("container_commander/engine.py")
    assert "EXEC_TIMEOUT_EXIT_CODE = 124" in src
    assert "def _build_timed_exec_command" in src
    assert "def _extract_timeout_marker" in src
    assert "timed_command = _build_timed_exec_command(command, timeout)" in src


# ---------------------------------------------------------------------------
# Behavioral tests for _build_timed_exec_command (zombie-prevention fix)
# ---------------------------------------------------------------------------

# Inline copy of the function so tests have no docker dependency.
_EXEC_TIMEOUT_EXIT_CODE = 124
_EXEC_TIMEOUT_MARKER = "__TRION_EXEC_TIMEOUT__"


def _build_timed_exec_command_under_test(command: str, timeout: int) -> str:
    """Mirror of container_commander.engine._build_timed_exec_command."""
    timeout_s = max(1, int(timeout or 30))
    cmd_escaped = shlex.quote(str(command or ""))
    marker = _EXEC_TIMEOUT_MARKER
    script = (
        f"cmd={cmd_escaped}; "
        "flag=/tmp/.trion_exec_timeout_$$; "
        'sh -lc "$cmd" & cmd_pid=$!; '
        '(SP=; trap \'kill "$SP" 2>/dev/null; exit\' TERM; '
        f'sleep {timeout_s} & SP=$!; wait "$SP"; '
        'echo 1 > "$flag"; kill -TERM "$cmd_pid" 2>/dev/null; '
        'SP=; sleep 1 & SP=$!; wait "$SP"; '
        'kill -KILL "$cmd_pid" 2>/dev/null) & killer_pid=$!; '
        'wait "$cmd_pid"; rc=$?; '
        'if [ -f "$flag" ]; then rm -f "$flag"; '
        'kill "$killer_pid" 2>/dev/null || true; wait "$killer_pid" 2>/dev/null || true; '
        f'echo "{marker}" >&2; exit {_EXEC_TIMEOUT_EXIT_CODE}; fi; '
        'kill "$killer_pid" 2>/dev/null || true; wait "$killer_pid" 2>/dev/null || true; '
        'exit "$rc"'
    )
    return f"sh -lc {shlex.quote(script)}"


def _count_sleep_zombies() -> int:
    result = subprocess.run(
        ["ps", "-eo", "stat,comm"],
        capture_output=True, text=True
    )
    return sum(
        1 for line in result.stdout.splitlines()
        if line.startswith("Z") and "sleep" in line
    )


def test_build_timed_exec_normal_path_output():
    """Command output and exit code are correct on the happy path."""
    cmd = _build_timed_exec_command_under_test("echo trion_ok", 5)
    r = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    assert r.returncode == 0
    assert "trion_ok" in r.stdout


def test_build_timed_exec_timeout_path_marker(tmp_path):
    """Timeout path emits the marker on stderr and returns exit code 124.

    We redirect stderr to a file instead of a pipe to avoid communicate()
    blocking: when 'sh -lc cmd' does not exec its child, the orphaned sleep
    process inherits the pipe write-end and keeps it open until it dies.
    A file redirect sidesteps this — subprocess.run uses wait() and returns
    as soon as the main script process exits.
    """
    stderr_file = tmp_path / "stderr.txt"
    cmd = _build_timed_exec_command_under_test("sleep 60", 1)
    with open(stderr_file, "w") as fe:
        r = subprocess.run(
            cmd, shell=True, stdout=subprocess.DEVNULL, stderr=fe, timeout=10
        )
    assert r.returncode == _EXEC_TIMEOUT_EXIT_CODE
    assert _EXEC_TIMEOUT_MARKER in stderr_file.read_text()


def test_build_timed_exec_normal_path_no_new_zombies():
    """Normal path must not leave behind zombie sleep processes."""
    before = _count_sleep_zombies()
    cmd = _build_timed_exec_command_under_test("echo hello", 5)
    subprocess.run(cmd, shell=True, capture_output=True)
    time.sleep(0.3)  # give kernel time to reap
    after = _count_sleep_zombies()
    assert after <= before, (
        f"New zombie sleep processes created: before={before}, after={after}"
    )


def test_build_timed_exec_timeout_path_no_new_zombies(tmp_path):
    """Timeout path must not leave behind zombie sleep processes.

    Uses file redirect for the same reason as test_build_timed_exec_timeout_path_marker.
    """
    before = _count_sleep_zombies()
    cmd = _build_timed_exec_command_under_test("sleep 60", 1)
    with open(tmp_path / "out.txt", "w") as f:
        subprocess.run(
            cmd, shell=True, stdout=f, stderr=f, timeout=10
        )
    time.sleep(0.5)
    after = _count_sleep_zombies()
    assert after <= before, (
        f"New zombie sleep processes created: before={before}, after={after}"
    )


def test_engine_exec_timeout_killer_trap_present():
    """Source must contain the SIGTERM trap that prevents orphaned sleep children."""
    src = _read("container_commander/engine.py")
    assert "trap" in src
    assert "kill \"$SP\"" in src or 'kill "$SP"' in src


def test_engine_quota_reservation_contract_present():
    src = _read("container_commander/engine.py")
    assert "_pending_starts" in src
    assert "def _reserve_quota" in src
    assert "def _release_quota_reservation" in src
    assert "def _commit_quota_reservation" in src
    assert "reserved_mem_mb, reserved_cpu = _reserve_quota(resources)" in src


def test_engine_unique_runtime_suffix_contract_present():
    src = _read("container_commander/engine.py")
    assert "def _unique_runtime_suffix" in src
    assert "unique_suffix = _unique_runtime_suffix()" in src
    assert "container_name = f\"{TRION_PREFIX}{blueprint_id}_{unique_suffix}\"" in src
    assert "volume_name = f\"trion_ws_{blueprint_id}_{unique_suffix}\"" in src


def test_approval_store_persistence_roundtrip(tmp_path, monkeypatch):
    store_path = tmp_path / "approval_store.json"
    monkeypatch.setattr(approval, "APPROVAL_STORE_PATH", str(store_path))

    with approval._lock:
        old_pending = dict(approval._pending)
        old_history = list(approval._history)
        old_callbacks = dict(approval._callbacks)

    item = approval.PendingApproval(
        blueprint_id="python-sandbox",
        reason="needs net",
        network_mode=NetworkMode.FULL,
        risk_flags=["network_full", "cap_add:SYS_ADMIN"],
        risk_reasons=[
            "Container requests internet access (network: full)",
            "Container requests dangerous capability: SYS_ADMIN",
        ],
        requested_cap_add=["SYS_ADMIN"],
        requested_security_opt=["seccomp=unconfined"],
        requested_cap_drop=["NET_RAW"],
        read_only_rootfs=True,
        extra_env={"A": "1"},
        session_id="sess-1",
        conversation_id="conv-1",
    )

    try:
        with approval._lock:
            approval._pending.clear()
            approval._history.clear()
            approval._callbacks.clear()
            approval._pending[item.id] = item
            approval._callbacks[item.id] = threading.Event()
            approval._save_store_unlocked()

            approval._pending.clear()
            approval._history.clear()
            approval._callbacks.clear()

        approval._load_store()

        with approval._lock:
            assert item.id in approval._pending
            restored = approval._pending[item.id]
            assert restored.blueprint_id == "python-sandbox"
            assert restored.session_id == "sess-1"
            assert restored.risk_flags == ["network_full", "cap_add:SYS_ADMIN"]
            assert restored.requested_security_opt == ["seccomp=unconfined"]
            assert restored.requested_cap_drop == ["NET_RAW"]
            assert restored.read_only_rootfs is True
            assert item.id in approval._callbacks
    finally:
        with approval._lock:
            approval._pending.clear()
            approval._pending.update(old_pending)
            approval._history.clear()
            approval._history.extend(old_history)
            approval._callbacks.clear()
            approval._callbacks.update(old_callbacks)


def test_bridge_approval_policy_consistent_between_modules(monkeypatch):
    monkeypatch.setattr(approval, "APPROVAL_REQUIRE_BRIDGE", True)

    reason = approval.check_needs_approval(NetworkMode.BRIDGE)
    assert reason is not None

    monkeypatch.setattr(approval, "APPROVAL_REQUIRE_BRIDGE", False)

    reason_off = approval.check_needs_approval(NetworkMode.BRIDGE)
    assert reason_off is None

    network_src = _read("container_commander/network.py")
    assert "APPROVAL_REQUIRE_BRIDGE" in network_src
    assert '"requires_approval": APPROVAL_REQUIRE_BRIDGE' in network_src
