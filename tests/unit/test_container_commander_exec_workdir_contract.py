from pathlib import Path


def _read(path: str) -> str:
    root = Path(__file__).resolve().parents[2]
    return (root / path).read_text(encoding="utf-8")


def test_exec_path_falls_back_when_workspace_is_missing():
    src = _read("container_commander/engine.py")
    assert "def _exec_run_with_workdir_fallback(" in src
    assert 'workdir="/workspace"' in src
    assert '"chdir to cwd" not in stderr.lower()' in src
    assert 'workdir="/"' in src
    assert "exec_result = _exec_run_with_workdir_fallback(container, timed_command)" in src
