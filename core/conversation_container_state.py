"""
ConversationContainerState — typisiertes Objekt + Store für Orchestrator-Conversation-Wahrheit.

Entanden aus:
  docs/obsidian/2026-03-31-container-session-state-konsolidierung.md

Konsolidiert:
  - core/orchestrator.py: _conversation_container_state (raw Dict), _conversation_container_lock,
    _get_recent_container_state(), _remember_container_state(), _update_container_state_from_tool_result()

Was NICHT konsolidiert wird:
  - Docker-Runtime-Wahrheit (engine.py._active) — sinnvoll getrennt
  - Commander-Runtime-Wahrheit (engine_runtime_state.py) — sinnvoll getrennt
  - container_state_utils.py Merge/Select-Logik — bleibt unverändert, Store delegiert dorthin
"""

from __future__ import annotations

import json
import logging
import os
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


def _candidate_state_files() -> List[Path]:
    raw_candidates = []
    env_file = os.getenv("CONVERSATION_CONTAINER_STATE_FILE") or os.getenv("JARVIS_CONVERSATION_CONTAINER_STATE_FILE")
    if env_file:
        raw_candidates.append(env_file)
    raw_candidates.extend(
        [
            "/app/data/conversation_container_state.json",
            "/tmp/trion_conversation_container_state.json",
        ]
    )

    out: List[Path] = []
    seen = set()
    for raw in raw_candidates:
        path = Path(str(raw)).expanduser()
        key = str(path)
        if key in seen:
            continue
        seen.add(key)
        out.append(path)
    return out


# ---------------------------------------------------------------------------
# Datentyp
# ---------------------------------------------------------------------------


@dataclass
class ConversationContainerState:
    """Typisierter Conversation-Container-State für eine einzelne Conversation-ID."""

    last_active_container_id: str = ""
    home_container_id: str = ""
    known_containers: List[Dict[str, str]] = field(default_factory=list)
    updated_at: float = 0.0
    history_len: int = 0

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "ConversationContainerState":
        return cls(
            last_active_container_id=str(d.get("last_active_container_id", "") or ""),
            home_container_id=str(d.get("home_container_id", "") or ""),
            known_containers=list(d.get("known_containers") or []),
            updated_at=float(d.get("updated_at", 0.0) or 0.0),
            history_len=int(d.get("history_len", 0) or 0),
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "last_active_container_id": self.last_active_container_id,
            "home_container_id": self.home_container_id,
            "known_containers": self.known_containers,
            "updated_at": self.updated_at,
            "history_len": self.history_len,
        }


# ---------------------------------------------------------------------------
# Store
# ---------------------------------------------------------------------------


class ConversationContainerStateStore:
    """
    Verwaltet den Container-State aller laufenden Conversations.

    Übernimmt die drei privaten Methoden aus core/orchestrator.py:
      - _get_recent_container_state  → get_recent()
      - _remember_container_state    → remember()
      - _update_container_state_from_tool_result → update_from_tool_result()

    Der Store delegiert intern an container_state_utils für Merge/Select-Logik.
    """

    def __init__(
        self,
        lock_factory: Callable,
        ttl_s_fn: Callable[[], int],
        ttl_turns_fn: Callable[[], int],
        home_blueprint_fn: Callable[[], str],
        persist_path: Optional[str] = None,
    ) -> None:
        self._state: Dict[str, ConversationContainerState] = {}
        self._lock = lock_factory()
        self._ttl_s_fn = ttl_s_fn
        self._ttl_turns_fn = ttl_turns_fn
        self._home_blueprint_fn = home_blueprint_fn
        candidates = [Path(persist_path).expanduser()] if persist_path else _candidate_state_files()
        self._persist_candidates = candidates
        self._persist_path = candidates[0] if candidates else Path("/tmp/trion_conversation_container_state.json")
        self._load_persisted_state()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get_recent(
        self,
        conversation_id: str,
        history_len: int = 0,
    ) -> Optional[Dict[str, Any]]:
        """
        Gibt den zuletzt gespeicherten Container-State zurück, wenn er noch gültig ist.
        Gibt None zurück wenn der State abgelaufen ist (TTL oder History-Delta).
        Rückgabe als Dict für Rückwärtskompatibilität mit bestehendem Orchestrator-Code.
        """
        conv_id = str(conversation_id or "").strip()
        if not conv_id:
            return None

        ttl_s = int(self._ttl_s_fn())
        ttl_turns = int(self._ttl_turns_fn())

        with self._lock:
            state = self._state.get(conv_id)
            if not isinstance(state, ConversationContainerState):
                return None

            age_s = time.time() - state.updated_at
            if age_s > ttl_s:
                self._state.pop(conv_id, None)
                self._persist_state_unlocked()
                return None

            if history_len > 0 and state.history_len > 0 and history_len >= state.history_len:
                max_delta = max(2, ttl_turns * 2)
                if (history_len - state.history_len) > max_delta:
                    self._state.pop(conv_id, None)
                    self._persist_state_unlocked()
                    return None

            return state.to_dict()

    def remember(
        self,
        conversation_id: str,
        *,
        last_active_container_id: str = "",
        home_container_id: str = "",
        known_containers: Optional[List[Dict[str, str]]] = None,
        history_len: int = 0,
    ) -> None:
        """Speichert / merged den Container-State für eine Conversation."""
        conv_id = str(conversation_id or "").strip()
        if not conv_id:
            return

        with self._lock:
            prev = self._state.get(conv_id)
            prev_dict = prev.to_dict() if isinstance(prev, ConversationContainerState) else {}

            merged_last_active = str(last_active_container_id or prev_dict.get("last_active_container_id", "")).strip()
            merged_home = str(home_container_id or prev_dict.get("home_container_id", "")).strip()
            merged_known = (
                known_containers
                if isinstance(known_containers, list)
                else list(prev_dict.get("known_containers") or [])
            )

            self._state[conv_id] = ConversationContainerState(
                last_active_container_id=merged_last_active,
                home_container_id=merged_home,
                known_containers=merged_known[:64],
                updated_at=time.time(),
                history_len=int(history_len or 0),
            )
            self._persist_state_unlocked()

    def update_from_tool_result(
        self,
        conversation_id: str,
        tool_name: str,
        tool_args: Dict[str, Any],
        result: Any,
        *,
        history_len: int = 0,
    ) -> None:
        """Aktualisiert den Container-State basierend auf einem Tool-Ergebnis."""
        from core.container_state_utils import merge_container_state_from_tool_result

        conv_id = str(conversation_id or "").strip()
        if not conv_id:
            return

        state = self.get_recent(conv_id, history_len=history_len) or {}
        merged = merge_container_state_from_tool_result(
            state,
            tool_name=tool_name,
            tool_args=tool_args,
            result=result,
            expected_home_blueprint_id=self._home_blueprint_fn(),
        )
        self.remember(
            conv_id,
            last_active_container_id=str(merged.get("last_active_container_id", "")).strip(),
            home_container_id=str(merged.get("home_container_id", "")).strip(),
            known_containers=merged.get("known_containers", []),
            history_len=history_len,
        )

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def _load_persisted_state(self) -> None:
        for candidate in self._persist_candidates:
            if not candidate.exists():
                continue
            try:
                raw = json.loads(candidate.read_text(encoding="utf-8"))
            except Exception as exc:
                logger.warning("[ConversationContainerState] Failed to load %s: %s", candidate, exc)
                continue
            if not isinstance(raw, dict):
                continue
            restored: Dict[str, ConversationContainerState] = {}
            now = time.time()
            ttl_s = int(self._ttl_s_fn())
            for conv_id, payload in raw.items():
                key = str(conv_id or "").strip()
                if not key or not isinstance(payload, dict):
                    continue
                try:
                    state = ConversationContainerState.from_dict(payload)
                except Exception:
                    continue
                if (now - state.updated_at) > ttl_s:
                    continue
                restored[key] = state
            with self._lock:
                self._state = restored
            self._persist_path = candidate
            return

    def _persist_state_unlocked(self) -> None:
        payload = {
            conv_id: state.to_dict()
            for conv_id, state in self._state.items()
            if conv_id and isinstance(state, ConversationContainerState)
        }
        data = json.dumps(payload, ensure_ascii=True, indent=2)
        last_error: Optional[Exception] = None
        for candidate in self._persist_candidates:
            try:
                candidate.parent.mkdir(parents=True, exist_ok=True)
                candidate.write_text(data, encoding="utf-8")
                self._persist_path = candidate
                return
            except Exception as exc:
                last_error = exc
        if last_error is not None:
            logger.warning(
                "[ConversationContainerState] Failed to persist state to any candidate path: %s",
                last_error,
            )
