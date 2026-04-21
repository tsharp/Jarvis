"""
System-Addons — MCP Tool Definitionen
═══════════════════════════════════════
Registriert die 4 Artifact-Registry-Tools via @mcp.tool:
  artifact_save, artifact_list, artifact_get, artifact_update

Ruft db_bridge.py auf — keine direkte DB-Logik hier.
"""

import logging
from typing import Optional

from .db_bridge import (
    artifact_save as db_save,
    artifact_get as db_get,
    artifact_list as db_list,
    artifact_update as db_update,
)
from .models import (
    ArtifactRecord,
    ArtifactSaveResult,
    ArtifactListResult,
    ArtifactGetResult,
    ArtifactUpdateResult,
)

log = logging.getLogger(__name__)

VALID_TYPES = {"skill", "cron", "config", "secret_ref", "other"}
VALID_STATUSES = {"active", "deprecated", "removed", "unverified"}


def register_tools(mcp):

    @mcp.tool
    def artifact_save(
        type: str,
        name: str,
        purpose: str = "",
        related_secrets: str = "",
        depends_on: str = "",
        meta: str = "",
    ) -> dict:
        """
        Artefakt anlegen oder aktualisieren (Upsert per type+name).

        TRION ruft dies auf nachdem create_skill oder cron_create erfolgreich war.

        Args:
            type: Artefakt-Typ (skill | cron | config | secret_ref | other)
            name: Eindeutiger Name des Artefakts
            purpose: Kurzbeschreibung was es tut
            related_secrets: Komma-getrennte Secret-Namen die es braucht
            depends_on: Komma-getrennte Namen anderer Artefakte
            meta: Optionaler JSON-String mit weiteren Metadaten
        """
        t = str(type or "").strip().lower()
        n = str(name or "").strip()
        if not t:
            return ArtifactSaveResult(ok=False, error="type darf nicht leer sein").model_dump()
        if not n:
            return ArtifactSaveResult(ok=False, error="name darf nicht leer sein").model_dump()
        try:
            aid = db_save(
                type=t,
                name=n,
                purpose=str(purpose or "").strip() or None,
                related_secrets=str(related_secrets or "").strip() or None,
                depends_on=str(depends_on or "").strip() or None,
                meta=str(meta or "").strip() or None,
            )
            return ArtifactSaveResult(ok=True, artifact_id=aid).model_dump()
        except Exception as e:
            log.error(f"[artifact_save] {e}")
            return ArtifactSaveResult(ok=False, error=str(e)).model_dump()

    @mcp.tool
    def artifact_list(
        type: str = "",
        status: str = "",
        limit: int = 100,
    ) -> dict:
        """
        Alle bekannten Artefakte auflisten (gefiltert nach type/status).

        Standardmäßig werden alle aktiven und deprecated Artefakte zurückgegeben
        (status='removed' wird ausgeblendet).

        Args:
            type: Optional filter nach Typ (skill | cron | ...)
            status: Optional filter nach Status (active | deprecated | removed | unverified)
            limit: Max. Anzahl Ergebnisse (default: 100)
        """
        try:
            rows = db_list(
                type=str(type or "").strip() or None,
                status=str(status or "").strip() or None,
                limit=max(1, int(limit)),
            )
            artifacts = [ArtifactRecord(**r) for r in rows]
            return ArtifactListResult(ok=True, artifacts=artifacts, count=len(artifacts)).model_dump()
        except Exception as e:
            log.error(f"[artifact_list] {e}")
            return ArtifactListResult(ok=False, error=str(e)).model_dump()

    @mcp.tool
    def artifact_get(name: str) -> dict:
        """
        Details zu einem Artefakt per Name abrufen.

        Args:
            name: Name des Artefakts (exakte Übereinstimmung)
        """
        n = str(name or "").strip()
        if not n:
            return ArtifactGetResult(ok=False, error="name darf nicht leer sein").model_dump()
        try:
            row = db_get(name=n)
            if row is None:
                return ArtifactGetResult(ok=False, error=f"Artefakt '{n}' nicht gefunden").model_dump()
            return ArtifactGetResult(ok=True, artifact=ArtifactRecord(**row)).model_dump()
        except Exception as e:
            log.error(f"[artifact_get] {e}")
            return ArtifactGetResult(ok=False, error=str(e)).model_dump()

    @mcp.tool
    def artifact_update(
        name: str,
        status: str = "",
        meta: str = "",
    ) -> dict:
        """
        Status oder Meta eines Artefakts ändern.

        Typische Aufrufe:
          artifact_update(name="my-skill", status="removed")   # nach Skill-Löschung
          artifact_update(name="my-skill", status="deprecated") # veraltet markieren

        Args:
            name: Name des Artefakts
            status: Neuer Status (active | deprecated | removed | unverified)
            meta: Neuer Meta-JSON-String (ersetzt bestehenden Wert)
        """
        n = str(name or "").strip()
        if not n:
            return ArtifactUpdateResult(ok=False, error="name darf nicht leer sein").model_dump()
        new_status = str(status or "").strip() or None
        new_meta = str(meta or "").strip() or None
        if new_status is None and new_meta is None:
            return ArtifactUpdateResult(ok=False, error="Mindestens status oder meta muss angegeben werden").model_dump()
        try:
            updated = db_update(name=n, status=new_status, meta=new_meta)
            return ArtifactUpdateResult(ok=True, updated=updated).model_dump()
        except Exception as e:
            log.error(f"[artifact_update] {e}")
            return ArtifactUpdateResult(ok=False, error=str(e)).model_dump()
