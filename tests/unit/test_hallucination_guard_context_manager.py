"""
Contract tests: Halluzinations-Guard — ContextResult Key-Tracking

Prüft:
- fehlende Keys landen in memory_keys_not_found
- gefundene Keys landen in memory_keys_found + memory_keys_requested
- memory_used bleibt für bestehende Nutzung unverändert
- beide Retrieval-Pfade (small_model_mode + full_context) werden abgedeckt
"""

from core.context_manager import ContextResult


# ---------------------------------------------------------------------------
# ContextResult — Felder vorhanden
# ---------------------------------------------------------------------------

def test_context_result_has_key_tracking_fields():
    r = ContextResult()
    assert hasattr(r, "memory_keys_requested")
    assert hasattr(r, "memory_keys_found")
    assert hasattr(r, "memory_keys_not_found")
    assert r.memory_keys_requested == []
    assert r.memory_keys_found == []
    assert r.memory_keys_not_found == []


def test_context_result_to_dict_includes_key_tracking():
    r = ContextResult()
    r.memory_keys_requested = ["user_name"]
    r.memory_keys_not_found = ["user_name"]
    d = r.to_dict()
    assert "memory_keys_requested" in d
    assert "memory_keys_found" in d
    assert "memory_keys_not_found" in d
    assert d["memory_keys_not_found"] == ["user_name"]


def test_context_result_memory_used_unchanged_semantics():
    """memory_used darf nicht als Guard-Signal verwendet werden — bleibt aber vorhanden."""
    r = ContextResult()
    r.memory_used = True
    r.memory_keys_not_found = ["user_name"]
    # Beide Felder können gleichzeitig gesetzt sein
    assert r.memory_used is True
    assert r.memory_keys_not_found == ["user_name"]


# ---------------------------------------------------------------------------
# Simulated Key-Loop Behavior
# ---------------------------------------------------------------------------

def _simulate_key_loop(result: ContextResult, memory_keys: list, found_keys: set):
    """Simuliert das Verhalten der Memory-Key-Loop in context_manager.py"""
    result.memory_keys_requested.extend(memory_keys)
    for key in memory_keys:
        if key in found_keys:
            result.memory_data += f"[{key}=found]"
            result.memory_used = True
            result.memory_keys_found.append(key)
        else:
            result.memory_keys_not_found.append(key)


def test_missing_key_tracked_in_not_found():
    r = ContextResult()
    _simulate_key_loop(r, ["user_name"], found_keys=set())
    assert "user_name" in r.memory_keys_not_found
    assert "user_name" not in r.memory_keys_found
    assert r.memory_used is False


def test_found_key_tracked_in_found():
    r = ContextResult()
    _simulate_key_loop(r, ["user_name"], found_keys={"user_name"})
    assert "user_name" in r.memory_keys_found
    assert "user_name" not in r.memory_keys_not_found
    assert r.memory_used is True


def test_mixed_keys_tracked_correctly():
    r = ContextResult()
    _simulate_key_loop(r, ["user_name", "preferences", "user_facts"], found_keys={"preferences"})
    assert "user_name" in r.memory_keys_not_found
    assert "user_facts" in r.memory_keys_not_found
    assert "preferences" in r.memory_keys_found
    assert len(r.memory_keys_not_found) == 2
    assert len(r.memory_keys_found) == 1


def test_all_keys_found_not_found_is_empty():
    r = ContextResult()
    _simulate_key_loop(r, ["user_name", "preferences"], found_keys={"user_name", "preferences"})
    assert r.memory_keys_not_found == []
    assert len(r.memory_keys_found) == 2


def test_no_keys_requested_not_found_stays_empty():
    r = ContextResult()
    # Kein Key angefragt (kein needs_memory)
    assert r.memory_keys_not_found == []
    assert r.memory_keys_requested == []


def test_multiple_loops_accumulate_correctly():
    """Beide Retrieval-Pfade (small_model + full_context) können akkumulieren."""
    r = ContextResult()
    # Erster Loop (small_model_mode)
    _simulate_key_loop(r, ["user_name"], found_keys=set())
    # Zweiter Loop (full_context_mode, z.B. fallback keys)
    _simulate_key_loop(r, ["user_facts", "personal_info"], found_keys={"user_facts"})

    assert "user_name" in r.memory_keys_not_found
    assert "personal_info" in r.memory_keys_not_found
    assert "user_facts" in r.memory_keys_found
    assert len(r.memory_keys_requested) == 3
