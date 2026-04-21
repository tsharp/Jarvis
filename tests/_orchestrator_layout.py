from __future__ import annotations

import os
from pathlib import Path


def get_repo_root() -> Path:
    env_root = str(os.getenv("JARVIS_PROJECT_ROOT") or "").strip()
    if env_root:
        root = Path(env_root).expanduser().resolve()
        if (root / "config" / "__init__.py").exists() and (root / "core").is_dir():
            return root
    return Path(__file__).resolve().parents[1]


def find_orchestrator_source_path() -> Path | None:
    root = get_repo_root()
    candidates = (
        root / "core" / "orchestrator.py",
        root / "core" / "orchestrator" / "pipeline.py",
        root / "core" / "orchestrator" / "__init__.py",
    )
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return None


def read_orchestrator_source() -> str:
    source_path = find_orchestrator_source_path()
    if source_path is None:
        raise FileNotFoundError("Could not locate PipelineOrchestrator source file")
    return source_path.read_text(encoding="utf-8")


def read_first_existing_repo_text(*relative_paths: str) -> str:
    root = get_repo_root()
    for relative_path in relative_paths:
        candidate = root / relative_path
        if candidate.exists():
            return candidate.read_text(encoding="utf-8")
    raise FileNotFoundError(
        f"Could not locate any repo source file from candidates: {relative_paths}"
    )
