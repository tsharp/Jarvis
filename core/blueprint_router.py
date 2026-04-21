"""
BlueprintSemanticRouter — Embedding-basierter Blueprint-Resolver.

Der Router bleibt deterministisch und LLM-frei, liefert aber primär Kandidaten-
Evidence für den ControlLayer. Die finale Auswahl bleibt damit bei Control.

Routing-Klassen:

  score >= MATCH_THRESHOLD_STRICT (0.80)  → use_blueprint
  score >= MATCH_THRESHOLD_SUGGEST (0.68) → suggest_blueprint
  score <  MATCH_THRESHOLD_SUGGEST        → no_blueprint

Wichtig:
  `route()` bleibt für bestehende Aufrufer kompatibel, enthält aber jetzt immer
  die gerankte Kandidatenliste als advisory Evidence.
"""

from typing import List, Optional
from utils.logger import log_info, log_warn
from core.graph_hygiene import apply_graph_hygiene, GraphCandidate

# ═══════════════════════════════════════════════════════
# SCHWELLWERTE
# ═══════════════════════════════════════════════════════

MATCH_THRESHOLD_STRICT  = 0.80  # Auto-route: hohe Konfidenz, kein weiterer Recheck nötig
MATCH_THRESHOLD_SUGGEST = 0.68  # Recheck-Zone: Discovery vertiefen, noch nicht starten
PARTIAL_THRESHOLD       = 0.52  # Unter diesem Wert: kein Blueprint erkennbar

MAX_QUERY_LEN = 200


class BlueprintRouterDecision:
    """Ergebnis einer Blueprint-Router-Entscheidung."""

    __slots__ = ("decision", "blueprint_id", "score", "reason", "candidates")

    def __init__(
        self,
        decision: str,                      # "use_blueprint" | "suggest_blueprint" | "no_blueprint"
        blueprint_id: Optional[str] = None,
        score: float = 0.0,
        reason: str = "",
        candidates: Optional[List[dict]] = None,  # [{"id": ..., "score": ...}] für suggest
    ):
        self.decision = decision
        self.blueprint_id = blueprint_id
        self.score = score
        self.reason = reason
        self.candidates = candidates or []

    def __repr__(self):
        return (
            f"BlueprintRouterDecision(decision={self.decision!r}, "
            f"blueprint={self.blueprint_id!r}, score={self.score:.3f})"
        )


class BlueprintSemanticRouter:
    """
    Embedding-basierter Blueprint-Router mit zwei Schwellwerten.

    Workflow (Phase 5):
    1. Baue Query aus user_text + intent
    2. Suche in _blueprints graph via cosine similarity (kein extra LLM)
    3. Hygiene-Pipeline (core/graph_hygiene.apply_graph_hygiene):
         parse → trust_level-Filter → dedupe(latest) → sqlite-crosscheck (fail-closed)
    4. Entscheide basierend auf bestem Score:
       - >= STRICT   → use_blueprint    (auto-route)
       - >= SUGGEST  → suggest_blueprint (Discovery/Recheck mit Top-Kandidaten)
       - sonst       → no_blueprint     (kein Freestyle-Fallback!)
    """

    def route(
        self,
        user_text: str,
        intent: str = "",
        top_k: int = 5,
    ) -> BlueprintRouterDecision:
        """
        Haupt-Routing-Methode.

        Args:
            user_text: Originale User-Anfrage
            intent:    Intent aus ThinkingLayer-Plan
            top_k:     Wie viele Treffer abrufen (mehr = bessere Suggest-Liste)

        Returns:
            BlueprintRouterDecision
        """
        try:
            from mcp.client import blueprint_semantic_search

            query = self._build_query(user_text, intent)
            results = blueprint_semantic_search(
                query=query,
                limit=top_k,
                min_similarity=0.0,
            )

            if not results:
                log_info("[BlueprintRouter] Kein Blueprint im Graph gefunden")
                return BlueprintRouterDecision(
                    decision="no_blueprint",
                    reason="Kein Blueprint im Graph",
                    candidates=[],
                )

            # Trust-Level-Filter: nur "verified" Blueprints zulassen.
            # Als extra_filter an apply_graph_hygiene() übergeben — läuft VOR dem Dedupe.
            def _trust_filter(c: GraphCandidate) -> bool:
                if c.meta.get("trust_level") != "verified":
                    log_info(
                        f"[BlueprintRouter] Blueprint übersprungen — "
                        f"trust_level={c.meta.get('trust_level')!r}"
                    )
                    return False
                if not c.blueprint_id:
                    log_info("[BlueprintRouter] Blueprint übersprungen — keine blueprint_id")
                    return False
                return True

            # Hygiene-Pipeline (Phase 5): fail-closed (kein Fail-Open bei SQLite-Fehler)
            candidates, log_meta = apply_graph_hygiene(
                results,
                fail_closed=True,
                crosscheck_mode="strict",
                extra_filter=_trust_filter,
            )
            log_info(
                f"[BlueprintRouter] Hygiene: "
                f"raw={log_meta['graph_candidates_raw']} "
                f"→ trust_filtered={log_meta['graph_candidates_after_extra']} "
                f"→ deduped={log_meta['graph_candidates_deduped']} "
                f"→ final={log_meta['graph_candidates_after_sqlite_filter']} "
                f"(mode={log_meta['graph_crosscheck_mode']})"
            )

            if not candidates:
                return BlueprintRouterDecision(
                    decision="no_blueprint",
                    reason="Keine verifizierten, aktiven Blueprints nach Hygiene-Filter",
                    candidates=[],
                )

            # Bester Treffer entscheidet (candidates sind score-sorted descending)
            best = candidates[0]
            best_score = best.score
            best_id = best.blueprint_id
            ranked = [
                {
                    "id": c.blueprint_id,
                    "score": c.score,
                }
                for c in candidates[: max(1, int(top_k or 5))]
                if c.blueprint_id
            ]

            log_info(
                f"[BlueprintRouter] Bester Kandidat: '{best_id}' score={best_score:.3f} "
                f"(strict={MATCH_THRESHOLD_STRICT}, suggest={MATCH_THRESHOLD_SUGGEST})"
            )

            # Exact-name bypass: alle Kandidaten prüfen ob Blueprint-ID explizit genannt,
            # nicht nur den best-scoring — z.B. wenn user-blueprint-1773182488 semantisch
            # vor gaming-station liegt, aber der User explizit "gaming-station" schreibt.
            _combined_lower = f"{user_text} {intent}".lower()
            for _cand in candidates:
                _cid = _cand.blueprint_id or ""
                if _cid and _cid.lower() in _combined_lower and _cand.score >= MATCH_THRESHOLD_SUGGEST:
                    log_info(
                        f"[BlueprintRouter] EXACT-NAME BYPASS → '{_cid}' "
                        f"(explizit genannt, score={_cand.score:.3f})"
                    )
                    return BlueprintRouterDecision(
                        decision="use_blueprint",
                        blueprint_id=_cid,
                        score=_cand.score,
                        reason=f"Explizit genannt + Semantic-Match ({_cand.score:.2f}) → auto-route '{_cid}'",
                        candidates=ranked,
                    )

            if best_score >= MATCH_THRESHOLD_STRICT:
                log_info(f"[BlueprintRouter] AUTO-ROUTE → '{best_id}' (score={best_score:.3f} >= {MATCH_THRESHOLD_STRICT})")
                return BlueprintRouterDecision(
                    decision="use_blueprint",
                    blueprint_id=best_id,
                    score=best_score,
                    reason=f"Hohe Konfidenz ({best_score:.2f}) → auto-route '{best_id}'",
                    candidates=ranked,
                )

            elif best_score >= MATCH_THRESHOLD_SUGGEST:
                log_info(
                    f"[BlueprintRouter] SUGGEST → score={best_score:.3f} in "
                    f"[{MATCH_THRESHOLD_SUGGEST}, {MATCH_THRESHOLD_STRICT}) "
                    f"— Kandidaten: {[c['id'] for c in ranked[:2]]}"
                )
                return BlueprintRouterDecision(
                    decision="suggest_blueprint",
                    blueprint_id=best_id,
                    score=best_score,
                    reason=f"Nicht sicher genug für auto-route ({best_score:.2f}) — erst Discovery/Recheck nötig",
                    candidates=ranked,
                )

            elif best_score >= PARTIAL_THRESHOLD:
                log_info(f"[BlueprintRouter] Partieller Treffer ({best_score:.2f}) — unter Suggest-Threshold")
                return BlueprintRouterDecision(
                    decision="no_blueprint",
                    score=best_score,
                    reason=f"Partieller Treffer ({best_score:.2f}) — unter Suggest-Threshold {MATCH_THRESHOLD_SUGGEST}",
                    candidates=ranked,
                )

            else:
                return BlueprintRouterDecision(
                    decision="no_blueprint",
                    score=best_score,
                    reason=f"Kein passender Blueprint (bester Score: {best_score:.2f})",
                    candidates=ranked,
                )

        except Exception as e:
            log_warn(f"[BlueprintRouter] Fehler bei Routing: {e} — no_blueprint")
            return BlueprintRouterDecision(
                decision="no_blueprint",
                reason=f"Router-Fehler: {e}",
                candidates=[],
            )

    def _build_query(self, user_text: str, intent: str) -> str:
        """Baut eine kompakte Query für die Embedding-Suche."""
        parts = []
        if intent and intent != "unknown":
            parts.append(intent.strip())
        if user_text:
            parts.append(user_text.strip())
        query = " ".join(parts)
        return query[:MAX_QUERY_LEN]


# Singleton
_router: Optional[BlueprintSemanticRouter] = None


def get_blueprint_router() -> BlueprintSemanticRouter:
    global _router
    if _router is None:
        _router = BlueprintSemanticRouter()
    return _router
