from pathlib import Path


def _read(path: str) -> str:
    root = Path(__file__).resolve().parents[2]
    return (root / path).read_text(encoding="utf-8")


def test_engine_preserves_gaming_station_on_stop_by_default():
    src = _read("container_commander/engine.py")
    assert 'PRESERVE_ON_STOP_BLUEPRINT_IDS = {"gaming-station"}' in src
    assert 'return str(blueprint_id or "").strip().lower() not in PRESERVE_ON_STOP_BLUEPRINT_IDS' in src
    assert 'blueprint_id = container.labels.get("trion.blueprint", "unknown")' in src
    assert 'should_remove = _should_remove_container_on_stop(blueprint_id, remove)' in src
    assert "if should_remove:" in src
    assert "container.remove(force=True)" in src
    assert 'else f"Container stopped and preserved: {container_id[:12]}"' in src


def test_api_exposes_start_endpoint_for_preserved_containers():
    src = _read("adapters/admin-api/commander_api/containers.py")
    assert '@router.post("/containers/{container_id}/start")' in src
    assert "start_stopped_container" in src
    assert 'return {"started": True, "container_id": container_id}' in src
