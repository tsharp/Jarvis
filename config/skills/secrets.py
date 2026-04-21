"""
config.skills.secrets
======================
Secret-Policy (C8) — Schutz sensibler Credentials in Skills.

Steuert wie streng das System mit Secrets in Skill-Definitionen umgeht
und wie der interne Secret-Resolve-Endpunkt abgesichert ist.

Enforcement-Stufen:
  warn   → warnen wenn Secrets unsicher verwendet werden (default)
  strict → Skill-Erstellung ablehnen wenn Secrets nicht korrekt referenziert

TTL-Caches verhindern wiederholte Burst-Anfragen an den Resolve-Endpunkt
wenn ein Key nicht existiert oder der Endpunkt 404 zurückgibt.
"""
import os

from config.infra.adapter import settings


def get_skill_secret_enforcement() -> str:
    """
    C8 Secret-Policy-Strenge:
      warn   → warnen, aber nicht blockieren (default)
      strict → blockieren wenn Secrets nicht korrekt referenziert
    """
    val = settings.get(
        "SKILL_SECRET_ENFORCEMENT",
        os.getenv("SKILL_SECRET_ENFORCEMENT", "warn"),
    ).lower()
    return val if val in ("warn", "strict") else "warn"


def get_secret_resolve_token() -> str:
    """Interner Token für /api/secrets/resolve/{name}."""
    return settings.get(
        "INTERNAL_SECRET_RESOLVE_TOKEN",
        os.getenv("INTERNAL_SECRET_RESOLVE_TOKEN", ""),
    )


def get_secret_rate_limit() -> int:
    """Rate-Limit Max-Anfragen/Minute für den internen Resolve-Endpunkt. Default: 100."""
    try:
        return int(settings.get(
            "SECRET_RATE_LIMIT",
            os.getenv("SECRET_RATE_LIMIT", "100"),
        ))
    except Exception:
        return 100


def get_secret_resolve_miss_ttl_s() -> int:
    """
    Provider-Level-Cooldown für fehlende Cloud-API-Keys (Sekunden).
    Verhindert wiederholte Burst-Anfragen wenn kein Key existiert. Default: 45.
    """
    try:
        return int(settings.get(
            "SECRET_RESOLVE_MISS_TTL_S",
            os.getenv("SECRET_RESOLVE_MISS_TTL_S", "45"),
        ))
    except Exception:
        return 45


def get_secret_resolve_not_found_ttl_s() -> int:
    """
    Candidate-Level-Cooldown nach 404 vom Resolve-Endpunkt (Sekunden). Default: 180.
    """
    try:
        return int(settings.get(
            "SECRET_RESOLVE_NOT_FOUND_TTL_S",
            os.getenv("SECRET_RESOLVE_NOT_FOUND_TTL_S", "180"),
        ))
    except Exception:
        return 180
