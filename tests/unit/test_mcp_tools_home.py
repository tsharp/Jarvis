import sys
from types import ModuleType
from unittest.mock import MagicMock


def test_ensure_trion_home_restarts_stopped_home_container(monkeypatch):
    from container_commander.mcp_tools_home import ensure_trion_home
    from container_commander.models import ContainerInstance, ContainerStatus

    restarted = []
    exec_calls = []
    captured = {}

    def _set_container_id(container_id: str) -> None:
        captured["container_id"] = container_id

    def _fake_exec_in_container(container_id: str, command: str, timeout: int = 30):
        exec_calls.append((container_id, command, timeout))
        return (0, "")

    fake_engine = ModuleType("container_commander.engine")
    fake_engine.list_containers = lambda: [
        ContainerInstance(
            container_id="ctr-stopped",
            blueprint_id="trion-home",
            name="trion-home",
            status=ContainerStatus.STOPPED,
        )
    ]
    fake_engine.start_stopped_container = lambda container_id: restarted.append(container_id) or True
    fake_engine.exec_in_container = _fake_exec_in_container
    fake_engine.start_container = lambda *args, **kwargs: (_ for _ in ()).throw(
        AssertionError("must not create new container")
    )

    fake_blueprint_store = ModuleType("container_commander.blueprint_store")
    fake_blueprint_store.get_blueprint = lambda _blueprint_id: object()
    fake_blueprint_store.create_blueprint = lambda _bp: None

    monkeypatch.setitem(sys.modules, "container_commander.engine", fake_engine)
    monkeypatch.setitem(sys.modules, "container_commander.blueprint_store", fake_blueprint_store)

    out = ensure_trion_home(
        current_container_id=None,
        set_container_id=_set_container_id,
        blueprint_id="trion-home",
        volume_name="trion_home_data",
        home_path="/home/trion",
        logger=MagicMock(),
    )

    assert out == "ctr-stopped"
    assert restarted == ["ctr-stopped"]
    assert captured["container_id"] == "ctr-stopped"
    assert exec_calls == [
        (
            "ctr-stopped",
            "mkdir -p /home/trion/notes /home/trion/projects /home/trion/scripts /home/trion/.config",
            10,
        )
    ]
