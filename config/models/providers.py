"""
config.models.providers
=======================
Provider-Auflösung — auf welchem Backend läuft welche Rolle.

Unterstützte Provider: ollama | ollama_cloud | openai | anthropic

Thinking- und Control-Provider fallen auf den Output-Provider zurück,
wenn kein expliziter Override gesetzt ist. Das erlaubt eine
Ein-Zeilen-Konfiguration ("alles auf ollama") als sinnvollen Default.
"""
import os

from config.infra.adapter import settings


_VALID_PROVIDERS = {"ollama", "ollama_cloud", "openai", "anthropic"}


def _normalize_provider(raw: str, default: str = "ollama") -> str:
    provider = str(raw or "").strip().lower()
    if not provider:
        return default
    return provider if provider in _VALID_PROVIDERS else default


def get_output_provider() -> str:
    raw = settings.get("OUTPUT_PROVIDER", None)
    if str(raw or "").strip() == "":
        raw = os.getenv("OUTPUT_PROVIDER", "ollama")
    return _normalize_provider(raw, default="ollama")


def get_thinking_provider() -> str:
    raw = settings.get("THINKING_PROVIDER", None)
    if str(raw or "").strip() == "":
        raw = os.getenv("THINKING_PROVIDER", "")
    return _normalize_provider(raw, default=get_output_provider())


def get_control_provider() -> str:
    raw = settings.get("CONTROL_PROVIDER", None)
    if str(raw or "").strip() == "":
        raw = os.getenv("CONTROL_PROVIDER", "")
    return _normalize_provider(raw, default=get_output_provider())
