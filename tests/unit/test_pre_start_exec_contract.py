from types import SimpleNamespace

from container_commander.engine_runtime_blueprint import run_pre_start_exec
from container_commander.models import Blueprint, MountDef, PreStartExec


def test_pre_start_exec_passes_shell_command_as_single_argument():
    calls = {}

    class _Containers:
        def run(self, **kwargs):
            calls["kwargs"] = kwargs
            return None

    client = SimpleNamespace(containers=_Containers())
    bp = Blueprint(
        id="filestash",
        name="Filestash",
        image="machines/filestash:latest",
        mounts=[MountDef(host="filestash_state", container="/app/data/state", type="volume", mode="rw")],
        pre_start_exec=PreStartExec(command="mkdir -p /app/data/state/config && echo ok"),
    )

    run_pre_start_exec(bp, "machines/filestash:latest", {}, get_client=lambda: client)

    kwargs = calls["kwargs"]
    assert kwargs["entrypoint"] == ["/bin/sh", "-lc"]
    assert kwargs["command"] == ["mkdir -p /app/data/state/config && echo ok"]
