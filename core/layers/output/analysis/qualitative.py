"""
core.layers.output.analysis.qualitative
=========================================
Qualitative Grounding-Bewertung und Text-Normalisierung.

Bewertet ob eine LLM-Antwort neue/unbelegte Informationen enthält
(Novelty-Ratio) und stellt Hilfsfunktionen für Textvergleiche bereit.
"""
import re
from typing import Any, Dict, List, Optional


def normalize_semantic_text(text: str) -> str:
    """Lowercase + Umlaut-Ersetzen für konsistente Mustervergleiche."""
    raw = str(text or "").lower()
    return (
        raw.replace("ä", "ae")
        .replace("ö", "oe")
        .replace("ü", "ue")
        .replace("ß", "ss")
    )


def summarize_structured_output(output_text: str, max_lines: int = 4) -> str:
    """
    Kürzt strukturierten Output auf max N relevante Zeilen.
    Priorisiert Hardware-relevante Zeilen (GPU, VRAM, CPU, RAM…)
    damit diese nicht beim Kürzen verloren gehen.
    """
    if not output_text:
        return ""
    lines = []
    for raw in str(output_text).splitlines():
        line = str(raw or "").strip()
        if not line:
            continue
        if re.fullmatch(r"-{3,}", line):
            continue
        lines.append(line)
    if not lines:
        return ""

    priority_patterns = [
        r"\bgpu\b",
        r"\bvram\b",
        r"\bcpu\b",
        r"\bram\b",
        r"\bspeicher\b",
        r"\bdisk\b",
    ]
    selected: List[str] = []
    for pattern in priority_patterns:
        for line in lines:
            if line in selected:
                continue
            if re.search(pattern, line, re.IGNORECASE):
                selected.append(line)

    for line in lines:
        if line not in selected:
            selected.append(line)

    return "; ".join(selected[:max_lines])


def to_int(value: Any) -> Optional[int]:
    """Safe-Cast zu int. Gibt None zurück bei Fehler."""
    try:
        return int(value)
    except Exception:
        return None


def evaluate_qualitative_grounding(
    *,
    answer: str,
    evidence_blob: str,
    guard_cfg: Dict[str, Any],
    extract_word_tokens_fn,
) -> Dict[str, Any]:
    """
    Bewertet ob die LLM-Antwort qualitativ neue/unbelegte Aussagen enthält.

    Berechnet den Anteil der Antwort-Token die NICHT in der Evidence vorkommen
    (Novelty-Ratio). Gibt violated=True wenn der Schwellwert überschritten wird.

    Args:
        answer: Die generierte LLM-Antwort.
        evidence_blob: Alle bekannten Fakten als Fließtext.
        guard_cfg: Konfiguration aus grounding policy (max_overall_novelty_ratio etc.)
        extract_word_tokens_fn: Callable — inject um circular imports zu vermeiden.
    """
    cfg = guard_cfg if isinstance(guard_cfg, dict) else {}
    min_len = max(2, int(cfg.get("min_token_length", 5) or 5))
    max_overall_ratio = float(cfg.get("max_overall_novelty_ratio", 0.72) or 0.72)
    max_sentence_ratio = float(cfg.get("max_sentence_novelty_ratio", 0.82) or 0.82)
    min_sentence_tokens = max(1, int(cfg.get("min_sentence_tokens", 4) or 4))
    min_sentence_violations = max(
        0, int(cfg.get("min_assertive_sentence_violations", 1) or 0)
    )
    assertive_cues = [
        str(cue).strip().lower()
        for cue in cfg.get("assertive_cues", [])
        if str(cue).strip()
    ]
    ignored = {
        str(tok).strip().lower()
        for tok in cfg.get("ignored_tokens", [])
        if str(tok).strip()
    }

    evidence_tokens = {
        tok
        for tok in extract_word_tokens_fn(evidence_blob, min_len=min_len)
        if tok not in ignored
    }
    answer_tokens = [
        tok
        for tok in extract_word_tokens_fn(answer, min_len=min_len)
        if tok not in ignored
    ]
    answer_unique = sorted(set(answer_tokens))
    if not answer_unique:
        return {"violated": False, "overall_novelty_ratio": 0.0, "sentence_violations": 0}

    novelty = [tok for tok in answer_unique if tok not in evidence_tokens]
    overall_ratio = len(novelty) / max(1, len(answer_unique))

    sentence_violations = 0
    for sentence in re.split(r"[.!?;\n]+", answer):
        sentence_text = sentence.strip()
        if not sentence_text:
            continue
        sentence_lower = sentence_text.lower()
        if assertive_cues and not any(
            re.search(rf"\b{re.escape(cue)}\b", sentence_lower) for cue in assertive_cues
        ):
            continue
        sentence_tokens = [
            tok
            for tok in extract_word_tokens_fn(sentence_text, min_len=min_len)
            if tok not in ignored
        ]
        sentence_unique = sorted(set(sentence_tokens))
        if len(sentence_unique) < min_sentence_tokens:
            continue
        sentence_novelty = [tok for tok in sentence_unique if tok not in evidence_tokens]
        sentence_ratio = len(sentence_novelty) / max(1, len(sentence_unique))
        if sentence_ratio > max_sentence_ratio:
            sentence_violations += 1

    violated = bool(
        overall_ratio > max_overall_ratio
        and sentence_violations >= min_sentence_violations
    )
    return {
        "violated": violated,
        "overall_novelty_ratio": round(overall_ratio, 4),
        "sentence_violations": sentence_violations,
        "novel_tokens_sample": novelty[:8],
    }
