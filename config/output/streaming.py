"""
config.output.streaming
========================
Output-Timeouts & Stream-Verhalten.

Steuert wie die fertige Antwort zum Client transportiert wird:
- Wie lange darf der OutputLayer maximal brauchen?
- Wie wird ein laufender Stream auf Grounding-Fehler geprüft?

Stream-Postcheck-Modi:
  tail_repair → Stream sofort senden, Korrektur nur bei Bedarf anhängen (default)
  buffered    → Vollständige Ausgabe puffern vor dem Senden (legacy)
  off         → Postcheck deaktivieren
"""
import os

from config.infra.adapter import settings


def get_output_timeout_interactive_s() -> int:
    """HTTP-Timeout für den OutputLayer im Interactive-Mode (Sekunden)."""
    val = int(settings.get(
        "OUTPUT_TIMEOUT_INTERACTIVE_S",
        os.getenv("OUTPUT_TIMEOUT_INTERACTIVE_S", "30"),
    ))
    return max(5, min(300, val))


def get_output_timeout_deep_s() -> int:
    """HTTP-Timeout für den OutputLayer im Deep-Mode (Sekunden)."""
    val = int(settings.get(
        "OUTPUT_TIMEOUT_DEEP_S",
        os.getenv("OUTPUT_TIMEOUT_DEEP_S", "120"),
    ))
    return max(5, min(600, val))


def get_output_stream_postcheck_mode() -> str:
    """
    Stream-Grounding-Postcheck-Verhalten:
      - tail_repair: sofort streamen, Korrektur nur bei Bedarf anhängen (default)
      - buffered:    vollständige Ausgabe puffern (legacy)
      - off:         Postcheck für Streaming-Pfad deaktivieren
    """
    val = str(settings.get(
        "OUTPUT_STREAM_POSTCHECK_MODE",
        os.getenv("OUTPUT_STREAM_POSTCHECK_MODE", "tail_repair"),
    )).strip().lower()
    return val if val in {"tail_repair", "buffered", "off"} else "tail_repair"
