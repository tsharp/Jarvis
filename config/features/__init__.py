"""
config.features
===============
Feature-Flags & laufende Migrationen — VERGÄNGLICH.

Einträge hier sind temporär. Sobald eine Migration abgeschlossen ist,
wandern die stabilen Werte in ihr Heimat-Modul und der Eintrag wird gelöscht.

Module:
  typedstate → TypedState V1 Schema-Aktivierung, CSV-Source, Skills-Rendering
  security   → Container-Image Signature-Verify (off → opt_in → strict)

Re-Exports für bequemen Zugriff via `from config.features import ...`:
"""
from config.features.typedstate import (
    get_typedstate_mode,
    get_typedstate_enable_small_only,
    get_typedstate_csv_path,
    get_typedstate_csv_enable,
    get_typedstate_csv_jit_only,
    get_typedstate_skills_mode,
    TYPEDSTATE_MODE,
    TYPEDSTATE_ENABLE_SMALL_ONLY,
)

from config.features.security import (
    get_signature_verify_mode,
    SIGNATURE_VERIFY_MODE,
)

__all__ = [
    # typedstate
    "get_typedstate_mode", "get_typedstate_enable_small_only",
    "get_typedstate_csv_path", "get_typedstate_csv_enable",
    "get_typedstate_csv_jit_only", "get_typedstate_skills_mode",
    "TYPEDSTATE_MODE", "TYPEDSTATE_ENABLE_SMALL_ONLY",
    # security
    "get_signature_verify_mode", "SIGNATURE_VERIFY_MODE",
]
