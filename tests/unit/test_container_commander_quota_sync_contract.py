from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def _read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8")


def test_engine_has_runtime_sync_helper_for_quota_paths():
    src = _read("container_commander/engine.py")
    assert "def _sync_runtime_state_from_docker(force: bool = False) -> None:" in src
    assert '_sync_runtime_state_from_docker()' in src


def test_get_quota_and_quota_checks_sync_before_using_in_memory_state():
    src = _read("container_commander/engine.py")
    assert "def get_quota() -> SessionQuota:\n    \"\"\"Get current quota usage.\"\"\"\n    _sync_runtime_state_from_docker()" in src
    assert "def _check_quota(resources: ResourceLimits):\n    \"\"\"Raise if starting a new container would exceed quota.\"\"\"\n    _sync_runtime_state_from_docker()" in src
    assert "def _reserve_quota(resources: ResourceLimits) -> Tuple[float, float]:\n    \"\"\"Reserve quota atomically to prevent concurrent oversubscription.\"\"\"\n    _sync_runtime_state_from_docker()" in src
