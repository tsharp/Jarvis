from pathlib import Path


def _read(path: str) -> str:
    root = Path(__file__).resolve().parents[2]
    return (root / path).read_text(encoding="utf-8")


def test_secrets_app_get_api_base_avoids_self_recursion():
    src = _read("adapters/Jarvis/js/apps/secrets.js")
    assert 'window.getApiBase !== getApiBase' in src


def test_workspace_get_api_base_avoids_self_recursion():
    src = _read("adapters/Jarvis/static/js/workspace.js")
    assert 'window.getApiBase !== getApiBase' in src


def test_index_uses_versioned_secrets_script():
    src = _read("adapters/Jarvis/index.html")
    assert 'src="./js/apps/secrets.js?v=' in src


def test_index_uses_versioned_workspace_script():
    src = _read("adapters/Jarvis/index.html")
    assert 'src="./static/js/workspace.js?v=4"' in src
