from pathlib import Path


def _read(path: str) -> str:
    root = Path(__file__).resolve().parents[2]
    return (root / path).read_text(encoding="utf-8")


def test_trion_shell_uses_stable_language_resolver_with_mission_state():
    src = _read("adapters/admin-api/commander_api/containers.py")
    assert "def _resolve_shell_language(" in src
    assert "def _mission_state_prefers_german(" in src
    assert 'session.setdefault("mission_state", mission_state)' in src
    assert "language = _resolve_shell_language(" in src
    assert "mission_state=str(session.get(\"mission_state\") or \"\")" in src
