"""
Unit-Tests: ConversationContainerState + ConversationContainerStateStore

Prüft:
  - ConversationContainerState.from_dict() / to_dict() round-trip
  - Store.remember() — merge mit prev state
  - Store.get_recent() — TTL-Ablauf, history-delta
  - Store.update_from_tool_result() — Delegation an container_state_utils
"""

from __future__ import annotations

import threading
import time
import json
from typing import Any, Dict
from unittest.mock import MagicMock, patch

import pytest

from core.conversation_container_state import (
    ConversationContainerState,
    ConversationContainerStateStore,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_KNOWN = [{"container_id": "ctr-1", "blueprint_id": "bp-1", "status": "running", "name": "test"}]


def _make_store(
    ttl_s: int = 3600,
    ttl_turns: int = 10,
    home_bp: str = "trion-home",
    *,
    persist_path: str | None = None,
) -> ConversationContainerStateStore:
    return ConversationContainerStateStore(
        lock_factory=threading.Lock,
        ttl_s_fn=lambda: ttl_s,
        ttl_turns_fn=lambda: ttl_turns,
        home_blueprint_fn=lambda: home_bp,
        persist_path=persist_path,
    )


# ---------------------------------------------------------------------------
# ConversationContainerState
# ---------------------------------------------------------------------------

class TestConversationContainerStateDataclass:

    def test_defaults(self):
        s = ConversationContainerState()
        assert s.last_active_container_id == ""
        assert s.home_container_id == ""
        assert s.known_containers == []
        assert s.updated_at == 0.0
        assert s.history_len == 0

    def test_from_dict_full(self):
        d = {
            "last_active_container_id": "ctr-1",
            "home_container_id": "ctr-home",
            "known_containers": _KNOWN,
            "updated_at": 1234567890.5,
            "history_len": 7,
        }
        s = ConversationContainerState.from_dict(d)
        assert s.last_active_container_id == "ctr-1"
        assert s.home_container_id == "ctr-home"
        assert s.known_containers == _KNOWN
        assert s.updated_at == 1234567890.5
        assert s.history_len == 7

    def test_from_dict_empty(self):
        s = ConversationContainerState.from_dict({})
        assert s.last_active_container_id == ""
        assert s.known_containers == []
        assert s.history_len == 0

    def test_from_dict_none_values(self):
        s = ConversationContainerState.from_dict({
            "last_active_container_id": None,
            "home_container_id": None,
            "known_containers": None,
            "updated_at": None,
            "history_len": None,
        })
        assert s.last_active_container_id == ""
        assert s.home_container_id == ""
        assert s.known_containers == []
        assert s.updated_at == 0.0
        assert s.history_len == 0

    def test_to_dict_round_trip(self):
        s = ConversationContainerState(
            last_active_container_id="ctr-42",
            home_container_id="ctr-home",
            known_containers=_KNOWN,
            updated_at=9999.0,
            history_len=3,
        )
        d = s.to_dict()
        s2 = ConversationContainerState.from_dict(d)
        assert s2.last_active_container_id == "ctr-42"
        assert s2.home_container_id == "ctr-home"
        assert s2.known_containers == _KNOWN
        assert s2.updated_at == 9999.0
        assert s2.history_len == 3

    def test_to_dict_has_all_keys(self):
        s = ConversationContainerState()
        d = s.to_dict()
        assert set(d.keys()) == {"last_active_container_id", "home_container_id",
                                  "known_containers", "updated_at", "history_len"}


# ---------------------------------------------------------------------------
# ConversationContainerStateStore.remember
# ---------------------------------------------------------------------------

class TestStoreRemember:

    def test_remember_basic(self):
        store = _make_store()
        store.remember("conv-1", last_active_container_id="ctr-1", history_len=2)
        result = store.get_recent("conv-1")
        assert result is not None
        assert result["last_active_container_id"] == "ctr-1"
        assert result["history_len"] == 2

    def test_remember_merges_with_prev(self):
        store = _make_store()
        store.remember("conv-1", last_active_container_id="ctr-1", home_container_id="ctr-home")
        # Zweiter Aufruf ohne last_active → prev behalten
        store.remember("conv-1", home_container_id="ctr-home-2")
        result = store.get_recent("conv-1")
        assert result["last_active_container_id"] == "ctr-1"
        assert result["home_container_id"] == "ctr-home-2"

    def test_remember_known_containers_replaces_on_explicit_list(self):
        store = _make_store()
        store.remember("conv-1", known_containers=_KNOWN)
        new_known = [{"container_id": "ctr-2", "blueprint_id": "bp-2", "status": "stopped", "name": "x"}]
        store.remember("conv-1", known_containers=new_known)
        result = store.get_recent("conv-1")
        assert result["known_containers"] == new_known

    def test_remember_known_containers_keeps_prev_when_none(self):
        store = _make_store()
        store.remember("conv-1", known_containers=_KNOWN)
        store.remember("conv-1", last_active_container_id="ctr-2", known_containers=None)
        result = store.get_recent("conv-1")
        assert result["known_containers"] == _KNOWN

    def test_remember_empty_conv_id_ignored(self):
        store = _make_store()
        store.remember("", last_active_container_id="ctr-1")
        assert store.get_recent("") is None

    def test_remember_caps_known_containers_at_64(self):
        store = _make_store()
        big_list = [{"container_id": f"ctr-{i}", "blueprint_id": "", "status": "", "name": ""} for i in range(100)]
        store.remember("conv-1", known_containers=big_list)
        result = store.get_recent("conv-1")
        assert len(result["known_containers"]) == 64

    def test_remember_persists_state_to_disk(self, tmp_path):
        persist_path = tmp_path / "conversation_state.json"
        store = _make_store(persist_path=str(persist_path))
        store.remember("conv-1", last_active_container_id="ctr-1", history_len=2)

        payload = json.loads(persist_path.read_text(encoding="utf-8"))
        assert payload["conv-1"]["last_active_container_id"] == "ctr-1"
        assert payload["conv-1"]["history_len"] == 2


# ---------------------------------------------------------------------------
# ConversationContainerStateStore.get_recent
# ---------------------------------------------------------------------------

class TestStoreGetRecent:

    def test_returns_none_for_unknown_conv(self):
        store = _make_store()
        assert store.get_recent("nonexistent") is None

    def test_returns_none_for_empty_conv_id(self):
        store = _make_store()
        assert store.get_recent("") is None

    def test_expires_after_ttl(self):
        store = _make_store(ttl_s=1)
        store.remember("conv-1", last_active_container_id="ctr-1")
        time.sleep(1.1)
        assert store.get_recent("conv-1") is None

    def test_returns_valid_state_within_ttl(self):
        store = _make_store(ttl_s=3600)
        store.remember("conv-1", last_active_container_id="ctr-1")
        result = store.get_recent("conv-1")
        assert result is not None
        assert result["last_active_container_id"] == "ctr-1"

    def test_expires_on_history_delta_exceeded(self):
        store = _make_store(ttl_turns=5)
        store.remember("conv-1", last_active_container_id="ctr-1", history_len=5)
        # history_len=5, state_history_len=5, delta=16 > max_delta=max(2, 5*2)=10
        assert store.get_recent("conv-1", history_len=21) is None

    def test_keeps_state_within_history_delta(self):
        store = _make_store(ttl_turns=5)
        store.remember("conv-1", last_active_container_id="ctr-1", history_len=5)
        # delta = 8, max_delta = max(2, 10) = 10 → still valid
        result = store.get_recent("conv-1", history_len=13)
        assert result is not None

    def test_history_delta_skipped_when_history_len_zero(self):
        store = _make_store(ttl_turns=5)
        store.remember("conv-1", last_active_container_id="ctr-1", history_len=5)
        # history_len=0 → delta-check skipped
        result = store.get_recent("conv-1", history_len=0)
        assert result is not None

    def test_evicts_expired_entry_from_store(self):
        store = _make_store(ttl_s=1)
        store.remember("conv-1", last_active_container_id="ctr-1")
        time.sleep(1.1)
        store.get_recent("conv-1")  # triggers eviction
        # State should be gone now
        with store._lock:
            assert "conv-1" not in store._state

    def test_evicts_expired_entry_from_persisted_file(self, tmp_path):
        persist_path = tmp_path / "conversation_state.json"
        store = _make_store(ttl_s=1, persist_path=str(persist_path))
        store.remember("conv-1", last_active_container_id="ctr-1")
        time.sleep(1.1)
        assert store.get_recent("conv-1") is None
        payload = json.loads(persist_path.read_text(encoding="utf-8"))
        assert "conv-1" not in payload

    def test_loads_persisted_state_on_init(self, tmp_path):
        persist_path = tmp_path / "conversation_state.json"
        persist_path.write_text(
            json.dumps(
                {
                    "conv-1": {
                        "last_active_container_id": "ctr-1",
                        "home_container_id": "home-1",
                        "known_containers": _KNOWN,
                        "updated_at": time.time(),
                        "history_len": 4,
                    }
                }
            ),
            encoding="utf-8",
        )
        store = _make_store(persist_path=str(persist_path))
        result = store.get_recent("conv-1")
        assert result is not None
        assert result["last_active_container_id"] == "ctr-1"
        assert result["home_container_id"] == "home-1"

    def test_skips_expired_persisted_state_on_init(self, tmp_path):
        persist_path = tmp_path / "conversation_state.json"
        persist_path.write_text(
            json.dumps(
                {
                    "conv-1": {
                        "last_active_container_id": "ctr-1",
                        "home_container_id": "",
                        "known_containers": [],
                        "updated_at": time.time() - 100,
                        "history_len": 1,
                    }
                }
            ),
            encoding="utf-8",
        )
        store = _make_store(ttl_s=1, persist_path=str(persist_path))
        assert store.get_recent("conv-1") is None


# ---------------------------------------------------------------------------
# ConversationContainerStateStore.update_from_tool_result
# ---------------------------------------------------------------------------

class TestStoreUpdateFromToolResult:

    def test_update_delegates_to_merge(self):
        store = _make_store()
        mock_merged = {
            "last_active_container_id": "ctr-99",
            "home_container_id": "",
            "known_containers": [],
        }
        with patch("core.container_state_utils.merge_container_state_from_tool_result",
                   return_value=mock_merged) as mock_merge:
            store.update_from_tool_result(
                "conv-1",
                tool_name="request_container",
                tool_args={"blueprint_id": "bp-test"},
                result={"container_id": "ctr-99", "status": "running"},
                history_len=3,
            )
            mock_merge.assert_called_once()
            call_kwargs = mock_merge.call_args
            assert call_kwargs[1]["tool_name"] == "request_container"
            assert call_kwargs[1]["expected_home_blueprint_id"] == "trion-home"

        result = store.get_recent("conv-1")
        assert result is not None
        assert result["last_active_container_id"] == "ctr-99"

    def test_update_empty_conv_id_ignored(self):
        store = _make_store()
        # Should not raise
        store.update_from_tool_result("", "container_list", {}, {})
        assert store.get_recent("") is None

    def test_update_passes_history_len_to_get_recent(self):
        store = _make_store(ttl_turns=5)
        # Put expired-by-delta state in
        store.remember("conv-1", last_active_container_id="old-ctr", history_len=1)
        mock_merged = {
            "last_active_container_id": "new-ctr",
            "home_container_id": "",
            "known_containers": [],
        }
        with patch("core.container_state_utils.merge_container_state_from_tool_result",
                   return_value=mock_merged):
            # history_len=50 >> state_history_len=1 → TTL-delta eviction → start fresh
            store.update_from_tool_result("conv-1", "container_list", {}, {}, history_len=50)

        result = store.get_recent("conv-1")
        assert result["last_active_container_id"] == "new-ctr"
