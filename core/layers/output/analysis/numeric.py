"""
core.layers.output.analysis.numeric
=====================================
Extraktion numerischer und lexikalischer Token aus Text.

Wird vom Grounding-Postcheck verwendet um zu prüfen ob die LLM-Antwort
neue Zahlen enthält die nicht in der Evidence belegt sind.
"""
import re
from typing import List


def extract_numeric_tokens(text: str) -> List[str]:
    """
    Extrahiert potentiell faktische Zahlen-Token aus Text.
    Filtert reine Listmarker (z.B. '1.') raus und behält
    Werte mit Einheiten (GB, MHz, °C…) oder mit ≥2 Stellen.
    """
    if not text:
        return []
    pattern = re.compile(
        r"\b\d+(?:[.,]\d+)?\s*(?:%|gb|gib|mb|mhz|ghz|tb|°c|c|b)\b|\b\d{2,}(?:[.,]\d+)?\b",
        re.IGNORECASE,
    )
    out = []
    seen = set()
    for match in pattern.finditer(text):
        token = match.group(0).strip().lower().replace(" ", "")
        if token and token not in seen:
            seen.add(token)
            out.append(token)
    return out


def extract_word_tokens(text: str, min_len: int) -> List[str]:
    """
    Extrahiert Wort-Token für den qualitativen Novelty-Vergleich.
    Filtert reine Zahlen und Token unter min_len Zeichen.
    """
    if not text:
        return []
    pattern = re.compile(r"[a-zA-Z0-9äöüÄÖÜß_-]+")
    out: List[str] = []
    for raw in pattern.findall(str(text)):
        token = str(raw).strip().lower()
        if len(token) < min_len:
            continue
        if token.isdigit():
            continue
        out.append(token)
    return out
