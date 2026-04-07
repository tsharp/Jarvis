import threading
import sys
from unittest.mock import MagicMock, patch

from container_commander import approval
from container_commander.models import NetworkMode


def test_request_approval_event_includes_runtime_risk_payload(monkeypatch):
    captured = []
    monkeypatch.setattr(approval, "_emit_ws_activity", lambda event, **data: captured.append((event, data)))
    monkeypatch.setattr(approval, "APPROVAL_STORE_PATH", "/tmp/trion_approval_ws_payloads.json")

    with approval._lock:
        old_pending = dict(approval._pending)
        old_history = list(approval._history)
        old_callbacks = dict(approval._callbacks)

    try:
        with approval._lock:
            approval._pending.clear()
            approval._history.clear()
            approval._callbacks.clear()

        with patch.dict(sys.modules, {
            "container_commander.blueprint_store": MagicMock(log_action=lambda *args, **kwargs: None),
        }):
            item = approval.request_approval(
                blueprint_id="gaming-station",
                reason="Container requests dangerous capability: SYS_ADMIN",
                network_mode=NetworkMode.INTERNAL,
                risk_flags=["cap_add:SYS_ADMIN"],
                risk_reasons=["Container requests dangerous capability: SYS_ADMIN"],
                requested_cap_add=["SYS_ADMIN"],
                requested_security_opt=["seccomp=unconfined"],
                requested_cap_drop=["NET_RAW"],
                read_only_rootfs=True,
            )

        assert item.id
        assert captured and captured[0][0] == "approval_requested"
        payload = captured[0][1]
        assert payload["approval_reason"] == "Container requests dangerous capability: SYS_ADMIN"
        assert payload["risk_flags"] == ["cap_add:SYS_ADMIN"]
        assert payload["requested_cap_add"] == ["SYS_ADMIN"]
        assert payload["requested_security_opt"] == ["seccomp=unconfined"]
        assert payload["requested_cap_drop"] == ["NET_RAW"]
        assert payload["read_only_rootfs"] is True
    finally:
        with approval._lock:
            approval._pending.clear()
            approval._pending.update(old_pending)
            approval._history.clear()
            approval._history.extend(old_history)
            approval._callbacks.clear()
            approval._callbacks.update(old_callbacks)


def test_reject_event_keeps_runtime_risk_payload(monkeypatch):
    captured = []
    monkeypatch.setattr(approval, "_emit_ws_activity", lambda event, **data: captured.append((event, data)))
    monkeypatch.setattr(approval, "APPROVAL_STORE_PATH", "/tmp/trion_approval_ws_payloads_reject.json")

    with approval._lock:
        old_pending = dict(approval._pending)
        old_history = list(approval._history)
        old_callbacks = dict(approval._callbacks)

    try:
        with approval._lock:
            approval._pending.clear()
            approval._history.clear()
            approval._callbacks.clear()

        item = approval.PendingApproval(
            blueprint_id="gaming-station",
            reason="Container requests dangerous capability: SYS_ADMIN",
            network_mode=NetworkMode.INTERNAL,
            risk_flags=["cap_add:SYS_ADMIN"],
            risk_reasons=["Container requests dangerous capability: SYS_ADMIN"],
            requested_cap_add=["SYS_ADMIN"],
            requested_security_opt=["seccomp=unconfined"],
            requested_cap_drop=["NET_RAW"],
            read_only_rootfs=True,
            mount_overrides=[{"host": "/data/games", "container": "/games", "asset_id": "games-lib"}],
        )
        with approval._lock:
            approval._pending[item.id] = item
            approval._callbacks[item.id] = threading.Event()

        with patch.dict(sys.modules, {
            "container_commander.blueprint_store": MagicMock(log_action=lambda *args, **kwargs: None),
        }):
            ok = approval.reject(item.id, rejected_by="user", reason="not now")

        assert ok is True
        assert captured and captured[-1][0] == "approval_resolved"
        payload = captured[-1][1]
        assert payload["approval_reason"] == "Container requests dangerous capability: SYS_ADMIN"
        assert payload["risk_flags"] == ["cap_add:SYS_ADMIN"]
        assert payload["requested_cap_add"] == ["SYS_ADMIN"]
        assert payload["requested_security_opt"] == ["seccomp=unconfined"]
        assert payload["requested_cap_drop"] == ["NET_RAW"]
        assert payload["read_only_rootfs"] is True
        assert payload["mount_overrides"][0]["asset_id"] == "games-lib"
        assert payload["reason"] == "not now"
    finally:
        with approval._lock:
            approval._pending.clear()
            approval._pending.update(old_pending)
            approval._history.clear()
            approval._history.extend(old_history)
            approval._callbacks.clear()
            approval._callbacks.update(old_callbacks)
