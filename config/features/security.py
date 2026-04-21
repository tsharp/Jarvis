"""
config.features.security
=========================
Container-Image Signature-Verify — VERGÄNGLICH.

Steuert die Signatur-Prüfung von Container-Images bevor sie gestartet werden.
Die Migration läuft von off → opt_in → strict.

  off     → keine Prüfung (default, rückwärtskompatibel)
  opt_in  → prüfen wenn Signatur vorhanden; bei ungültiger ablehnen, bei fehlender erlauben
  strict  → Signatur Pflicht; bei fehlender oder ungültiger ablehnen

Sobald strict zum Standard wird, wandert diese Policy in den Container-Commander
und diese Datei wird gelöscht.
"""
import os

from config.infra.adapter import settings


def get_signature_verify_mode() -> str:
    """
    Container-Image Signatur-Verifikations-Mode:
      off     → keine Verifikation (default)
      opt_in  → optional, bei ungültiger Signatur ablehnen
      strict  → Signatur Pflicht
    """
    return settings.get(
        "SIGNATURE_VERIFY_MODE",
        os.getenv("SIGNATURE_VERIFY_MODE", "off"),
    ).lower()


# Backward-compat — beim Import eingefroren, Getter bevorzugen
SIGNATURE_VERIFY_MODE = get_signature_verify_mode()
