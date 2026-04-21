"""
Package facade for ControlLayer.

The actual implementation now lives in the sibling module `layer.py`, but the
public patch/import surface remains `core.layers.control.*`. To keep that
surface stable during the refactor, this package executes `layer.py` into the
current module namespace.
"""

from pathlib import Path


_LAYER_IMPL_PATH = Path(__file__).resolve().parent / "layer.py"

if not _LAYER_IMPL_PATH.exists():
    raise ImportError(f"Control layer implementation missing: {_LAYER_IMPL_PATH}")

_legacy_source = _LAYER_IMPL_PATH.read_text(encoding="utf-8")
_legacy_code = compile(_legacy_source, str(_LAYER_IMPL_PATH), "exec")
exec(_legacy_code, globals(), globals())
