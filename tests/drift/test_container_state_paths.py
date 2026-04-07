"""
Drift-Guard: Container-/Session-State-Wahrheit

Entstanden aus:
  docs/obsidian/2026-03-29-trion-codeatlas-und-konsolidierungsanalyse.md (Abschnitt D)
  docs/obsidian/2026-03-31-container-session-state-konsolidierung.md (Phase 4)

Diese Tests sichern die Architektur-Invarianten die durch Phase 1-3 eingeführt wurden:

  INVARIANTE 1 — Kein Raw-Dict mehr im Orchestrator:
    _conversation_container_state und _conversation_container_lock dürfen
    nicht mehr direkt in orchestrator.py oder orchestrator_flow_utils.py vorkommen.
    Sie leben ausschließlich in ConversationContainerStateStore.

  INVARIANTE 2 — Store-Initialisierung in flow_utils:
    orchestrator_flow_utils.py muss _container_state_store via
    ConversationContainerStateStore initialisieren.

  INVARIANTE 3 — Orchestrator-Wrapper existieren:
    orchestrator.py muss die drei dünnen Wrapper-Methoden haben die an
    _container_state_store delegieren.

  INVARIANTE 4 — Dataclass-Pflichtfelder:
    ConversationContainerState muss alle 5 Pflichtfelder haben.
    ConversationContainerStateStore muss alle 3 Store-Methoden haben.

  INVARIANTE 5 — Kein Drift in anderen Modulen:
    Kein anderes Core-Modul außer orchestrator.py darf _conversation_container_state
    als direktes Attribut oder Dict verwalten.

Warum static analysis und nicht Mock-Tests?
  Diese Invarianten sichern die Architektur gegen zukünftigen Drift, z.B.:
  - jemand fügt _conversation_container_state = {} direkt im Orchestrator wieder ein
  - jemand umgeht den Store und schreibt direkt in ein Dict
  Mock-Tests in test_conversation_container_state.py prüfen das Verhalten;
  diese Tests prüfen ob die Struktur des Codes die Invarianten respektiert.
"""

from __future__ import annotations

import re
from pathlib import Path

# ---------------------------------------------------------------------------
# Hilfsfunktionen
# ---------------------------------------------------------------------------

_ROOT = Path(__file__).resolve().parents[2]


def _read(rel: str) -> str:
    return (_ROOT / rel).read_text(encoding="utf-8")


def _count_pattern(src: str, pattern: str) -> int:
    return len(re.findall(pattern, src))


# ---------------------------------------------------------------------------
# INVARIANTE 1 — Kein Raw-Dict mehr im Orchestrator
# ---------------------------------------------------------------------------


class TestNoRawDictInOrchestrator:
    """
    _conversation_container_state und _conversation_container_lock dürfen
    nicht mehr als direkte Attribute auf dem Orchestrator oder in flow_utils vorkommen.
    """

    def test_orchestrator_has_no_raw_container_state_dict(self):
        """orchestrator.py darf _conversation_container_state nicht als Dict-Attribut haben."""
        src = _read("core/orchestrator.py")
        # Erlaubt: Methodenaufrufe auf dem Store, aber kein direktes _conversation_container_state = {}
        hits = re.findall(r'_conversation_container_state\s*=\s*\{', src)
        assert not hits, (
            f"orchestrator.py enthält _conversation_container_state = {{...}} ({len(hits)}×). "
            f"Der State lebt jetzt ausschließlich in ConversationContainerStateStore."
        )

    def test_orchestrator_has_no_raw_container_lock(self):
        """orchestrator.py darf _conversation_container_lock nicht direkt anlegen."""
        src = _read("core/orchestrator.py")
        hits = re.findall(r'_conversation_container_lock\s*=', src)
        assert not hits, (
            f"orchestrator.py setzt _conversation_container_lock direkt ({len(hits)}×). "
            f"Das Lock lebt jetzt ausschließlich im ConversationContainerStateStore."
        )

    def test_flow_utils_has_no_raw_container_state_dict(self):
        """orchestrator_flow_utils.py darf _conversation_container_state nicht mehr als Dict init haben."""
        src = _read("core/orchestrator_flow_utils.py")
        hits = re.findall(r'_conversation_container_state\s*=\s*\{', src)
        assert not hits, (
            f"orchestrator_flow_utils.py enthält _conversation_container_state = {{...}} ({len(hits)}×). "
            f"Initialisierung läuft jetzt über ConversationContainerStateStore."
        )

    def test_flow_utils_has_no_raw_container_lock(self):
        """orchestrator_flow_utils.py darf _conversation_container_lock nicht direkt anlegen."""
        src = _read("core/orchestrator_flow_utils.py")
        hits = re.findall(r'_conversation_container_lock\s*=', src)
        assert not hits, (
            f"orchestrator_flow_utils.py setzt _conversation_container_lock direkt ({len(hits)}×). "
            f"Das Lock lebt jetzt ausschließlich im ConversationContainerStateStore."
        )


# ---------------------------------------------------------------------------
# INVARIANTE 2 — Store-Initialisierung in flow_utils
# ---------------------------------------------------------------------------


class TestStoreInitialisierung:
    """
    orchestrator_flow_utils.py muss _container_state_store über
    ConversationContainerStateStore initialisieren.
    """

    def test_flow_utils_imports_store(self):
        """orchestrator_flow_utils.py muss ConversationContainerStateStore importieren."""
        src = _read("core/orchestrator_flow_utils.py")
        assert "ConversationContainerStateStore" in src, (
            "orchestrator_flow_utils.py importiert ConversationContainerStateStore nicht. "
            "Erwartet: from core.conversation_container_state import ConversationContainerStateStore"
        )

    def test_flow_utils_creates_container_state_store(self):
        """orchestrator_flow_utils.py muss _container_state_store anlegen."""
        src = _read("core/orchestrator_flow_utils.py")
        assert re.search(r'_container_state_store\s*=\s*ConversationContainerStateStore\s*\(', src), (
            "orchestrator_flow_utils.py initialisiert _container_state_store nicht via "
            "ConversationContainerStateStore(). Erwartet: orch._container_state_store = ConversationContainerStateStore(...)"
        )


# ---------------------------------------------------------------------------
# INVARIANTE 3 — Orchestrator-Wrapper existieren
# ---------------------------------------------------------------------------


class TestOrchestratorWrapper:
    """
    orchestrator.py muss die drei dünnen Wrapper-Methoden haben,
    die an self._container_state_store delegieren.
    """

    def test_orchestrator_has_get_recent_wrapper(self):
        """_get_recent_container_state muss an _container_state_store.get_recent delegieren."""
        src = _read("core/orchestrator.py")
        match = re.search(
            r'def _get_recent_container_state\b.*?(?=\n    def |\Z)', src, re.DOTALL
        )
        assert match, "orchestrator.py: _get_recent_container_state Methode nicht gefunden"
        body = match.group(0)
        assert "_container_state_store" in body, (
            "orchestrator._get_recent_container_state delegiert nicht an _container_state_store. "
            "Erwartet: return self._container_state_store.get_recent(...)"
        )

    def test_orchestrator_has_remember_wrapper(self):
        """_remember_container_state muss an _container_state_store.remember delegieren."""
        src = _read("core/orchestrator.py")
        match = re.search(
            r'def _remember_container_state\b.*?(?=\n    def |\Z)', src, re.DOTALL
        )
        assert match, "orchestrator.py: _remember_container_state Methode nicht gefunden"
        body = match.group(0)
        assert "_container_state_store" in body, (
            "orchestrator._remember_container_state delegiert nicht an _container_state_store. "
            "Erwartet: self._container_state_store.remember(...)"
        )

    def test_orchestrator_has_update_from_tool_result_wrapper(self):
        """_update_container_state_from_tool_result muss an _container_state_store.update_from_tool_result delegieren."""
        src = _read("core/orchestrator.py")
        match = re.search(
            r'def _update_container_state_from_tool_result\b.*?(?=\n    def |\Z)', src, re.DOTALL
        )
        assert match, "orchestrator.py: _update_container_state_from_tool_result Methode nicht gefunden"
        body = match.group(0)
        assert "_container_state_store" in body, (
            "orchestrator._update_container_state_from_tool_result delegiert nicht an _container_state_store. "
            "Erwartet: self._container_state_store.update_from_tool_result(...)"
        )


# ---------------------------------------------------------------------------
# INVARIANTE 4 — Dataclass-Pflichtfelder und Store-Methoden
# ---------------------------------------------------------------------------


class TestDataclassUndStorePflichtfelder:
    """
    ConversationContainerState muss alle 5 Pflichtfelder haben.
    ConversationContainerStateStore muss alle 3 Store-Methoden haben.
    """

    def test_dataclass_has_all_required_fields(self):
        """ConversationContainerState muss alle 5 Felder definieren."""
        src = _read("core/conversation_container_state.py")
        required_fields = [
            "last_active_container_id",
            "home_container_id",
            "known_containers",
            "updated_at",
            "history_len",
        ]
        for field in required_fields:
            assert field in src, (
                f"ConversationContainerState fehlt Pflichtfeld: {field}"
            )

    def test_dataclass_has_from_dict(self):
        """ConversationContainerState muss from_dict haben."""
        src = _read("core/conversation_container_state.py")
        assert re.search(r'def from_dict\s*\(', src), (
            "ConversationContainerState fehlt from_dict() Methode"
        )

    def test_dataclass_has_to_dict(self):
        """ConversationContainerState muss to_dict haben."""
        src = _read("core/conversation_container_state.py")
        assert re.search(r'def to_dict\s*\(', src), (
            "ConversationContainerState fehlt to_dict() Methode"
        )

    def test_store_has_remember(self):
        """ConversationContainerStateStore muss remember() haben."""
        src = _read("core/conversation_container_state.py")
        assert re.search(r'def remember\s*\(', src), (
            "ConversationContainerStateStore fehlt remember() Methode"
        )

    def test_store_has_get_recent(self):
        """ConversationContainerStateStore muss get_recent() haben."""
        src = _read("core/conversation_container_state.py")
        assert re.search(r'def get_recent\s*\(', src), (
            "ConversationContainerStateStore fehlt get_recent() Methode"
        )

    def test_store_has_update_from_tool_result(self):
        """ConversationContainerStateStore muss update_from_tool_result() haben."""
        src = _read("core/conversation_container_state.py")
        assert re.search(r'def update_from_tool_result\s*\(', src), (
            "ConversationContainerStateStore fehlt update_from_tool_result() Methode"
        )

    def test_store_module_exists(self):
        """core/conversation_container_state.py muss existieren."""
        p = _ROOT / "core" / "conversation_container_state.py"
        assert p.exists(), (
            "core/conversation_container_state.py existiert nicht. "
            "Wurde der Store gelöscht oder umbenannt?"
        )


# ---------------------------------------------------------------------------
# INVARIANTE 5 — Kein Drift in anderen Modulen
# ---------------------------------------------------------------------------


class TestKeinDriftInAnderenModulen:
    """
    Kein anderes Core-Modul darf _conversation_container_state als Raw-Dict verwalten.
    Der Store ist die einzige Stelle.
    """

    _RAW_DICT_PATTERN = r'_conversation_container_state\s*=\s*\{'

    def test_no_other_core_module_manages_raw_container_state(self):
        """
        Kein Core-Modul außer conversation_container_state.py darf
        _conversation_container_state = {...} direkt anlegen.
        """
        violations = []
        for p in (_ROOT / "core").glob("*.py"):
            if p.name == "conversation_container_state.py":
                continue
            try:
                src = p.read_text(encoding="utf-8")
                if re.search(self._RAW_DICT_PATTERN, src):
                    violations.append(p.relative_to(_ROOT))
            except Exception:
                pass
        assert not violations, (
            f"Core-Module verwalten _conversation_container_state als Raw-Dict (Drift!):\n"
            + "\n".join(f"  - {p}" for p in violations)
            + "\nNur ConversationContainerStateStore darf diesen State verwalten."
        )

    def test_no_adapter_module_manages_raw_container_state(self):
        """
        Adapter-Module dürfen _conversation_container_state nicht direkt anlegen.
        Sie müssen über die Orchestrator-Wrapper oder den Store gehen.
        """
        violations = []
        for p in (_ROOT / "adapters").rglob("*.py"):
            try:
                src = p.read_text(encoding="utf-8")
                if re.search(self._RAW_DICT_PATTERN, src):
                    violations.append(p.relative_to(_ROOT))
            except Exception:
                pass
        assert not violations, (
            f"Adapter-Module verwalten _conversation_container_state als Raw-Dict (Drift!):\n"
            + "\n".join(f"  - {p}" for p in violations)
            + "\nNur ConversationContainerStateStore darf diesen State verwalten."
        )
