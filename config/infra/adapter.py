"""
config.infra.adapter
====================
Settings-Bootstrap — Grundlage für alle anderen Config-Module.

Stellt das `settings`-Objekt bereit, das aus `utils.settings` geladen wird.
Schlägt der Import fehl (z.B. in isolierten Tests), greift der Fallback auf
os.getenv zurück, sodass kein Modul abstürzt.
"""
import os


class _EnvOnlySettingsFallback:
    """Minimaler Settings-Adapter, wenn utils.settings nicht importierbar ist."""

    def get(self, key, default=None):
        return os.getenv(key, default)


try:
    from utils.settings import settings
except (ModuleNotFoundError, ImportError):
    settings = _EnvOnlySettingsFallback()
