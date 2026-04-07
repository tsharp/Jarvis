from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from container_commander.mount_utils import ensure_bind_mount_host_dirs


class _Mount:
    def __init__(self, host: str, container: str = "/data", type: str = "bind", mode: str = "rw"):
        self.host = host
        self.container = container
        self.type = type
        self.mode = mode


def test_ensure_bind_mount_host_dirs_uses_host_helper_before_local(monkeypatch, tmp_path):
    missing = tmp_path / "services" / "gaming-station" / "data"
    helper_calls = []
    local_calls = []

    monkeypatch.setattr(
        "container_commander.mount_utils._host_helper_mkdirs",
        lambda paths, mode="0750": helper_calls.append((list(paths), mode)) or {"ok": True, "paths": [str(missing)]},
    )
    monkeypatch.setattr(
        "container_commander.mount_utils.os.makedirs",
        lambda path, mode=0o750, exist_ok=True: local_calls.append((str(path), mode, exist_ok)),
    )

    ensure_bind_mount_host_dirs([_Mount(str(missing))])

    assert helper_calls == [([str(missing)], "0750")]
    assert local_calls == []


def test_ensure_bind_mount_host_dirs_falls_back_to_local_when_helper_fails(monkeypatch, tmp_path):
    missing = tmp_path / "services" / "gaming-station" / "config"
    helper_calls = []
    local_calls = []

    monkeypatch.setattr(
        "container_commander.mount_utils._host_helper_mkdirs",
        lambda paths, mode="0750": helper_calls.append((list(paths), mode)) or {"ok": False, "error": "boom"},
    )
    monkeypatch.setattr(
        "container_commander.mount_utils.os.makedirs",
        lambda path, mode=0o750, exist_ok=True: local_calls.append((str(path), mode, exist_ok)),
    )
    monkeypatch.setattr("container_commander.mount_utils.os.path.exists", lambda path: False)

    ensure_bind_mount_host_dirs([_Mount(str(missing))])

    assert helper_calls == [([str(missing)], "0750")]
    assert local_calls == [(str(missing), 0o750, True)]
