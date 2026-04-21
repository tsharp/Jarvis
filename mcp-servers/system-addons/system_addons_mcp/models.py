"""
System-Addons — Pydantic Response-Schemas
══════════════════════════════════════════
ArtifactRecord, ArtifactSaveResult, ArtifactListResult, ArtifactUpdateResult
"""

from typing import Optional, List
from pydantic import BaseModel


class ArtifactRecord(BaseModel):
    id: str
    type: str
    name: str
    purpose: Optional[str] = None
    related_secrets: Optional[str] = None
    depends_on: Optional[str] = None
    created_at: str
    updated_at: Optional[str] = None
    status: str
    meta: Optional[str] = None


class ArtifactSaveResult(BaseModel):
    ok: bool
    artifact_id: Optional[str] = None
    error: Optional[str] = None


class ArtifactListResult(BaseModel):
    ok: bool
    artifacts: List[ArtifactRecord] = []
    count: int = 0
    error: Optional[str] = None


class ArtifactGetResult(BaseModel):
    ok: bool
    artifact: Optional[ArtifactRecord] = None
    error: Optional[str] = None


class ArtifactUpdateResult(BaseModel):
    ok: bool
    updated: bool = False
    error: Optional[str] = None
