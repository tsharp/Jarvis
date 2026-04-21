"""Container-specific text extraction helpers.

Ziel:
- Request-Felder aus User-Text extrahieren
- Identitaets-Signale getrennt von Ressourcen-/Python-Feldern halten
- keine Snapshot- oder Artifact-Merges hier
"""

from __future__ import annotations

import re
import unicodedata
from typing import Any, Dict


def _normalize(value: Any) -> str:
    text = unicodedata.normalize("NFKD", str(value or ""))
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    return " ".join(text.lower().split())


def _extract_ports(text: str) -> list[str]:
    out: list[str] = []
    if not text:
        return out
    for match in re.finditer(r"(?:port(?:s|e)?|ports?)\s*[:=]?\s*([0-9,\s/]+)", text, flags=re.IGNORECASE):
        raw = str(match.group(1) or "")
        for item in re.findall(r"\b\d{2,5}\b", raw):
            if item not in out:
                out.append(item)
    return out


def extract_container_request_fields(text: Any) -> Dict[str, Any]:
    raw = str(text or "")
    normalized = _normalize(raw)
    params: Dict[str, Any] = {}

    cpu_match = re.search(r"\b(\d{1,2})\s*(?:vcpu|cpu|cpus|kerne|cores?)\b", normalized)
    if cpu_match:
        params["cpu_cores"] = int(cpu_match.group(1))

    ram_match = re.search(r"\b(\d{1,3})\s*(gb|gib|mb)\s*(?:ram|speicher|memory)?\b", normalized)
    if ram_match:
        params["ram"] = f"{ram_match.group(1)} {ram_match.group(2).upper()}"

    runtime = ""
    if "cpu-only" in normalized or "cpu only" in normalized:
        runtime = "cpu-only"
    elif "nvidia" in normalized:
        runtime = "nvidia"
    elif "amd" in normalized:
        runtime = "amd"
    if runtime:
        params["runtime"] = runtime

    gpu = ""
    for marker in ("rtx", "gtx", "nvidia", "amd", "intel arc", "gpu"):
        if marker in normalized:
            gpu = marker.upper() if marker not in {"nvidia", "amd", "gpu"} else marker
            break
    if gpu:
        params["gpu"] = gpu

    ports = _extract_ports(raw)
    if ports:
        params["ports"] = ports

    duration_match = re.search(r"\b(\d{1,3})\s*(stunden|stunde|hours?|tage|tag|days?)\b", normalized)
    if duration_match:
        params["duration"] = f"{duration_match.group(1)} {duration_match.group(2)}"

    return params


def _extract_python_version(text: str) -> str:
    patterns = (
        r"\bpython(?:\s+version)?\s*(3(?:\.\d{1,2}){0,2})\b",
        r"\bpy(?:thon)?\s*(3(?:\.\d{1,2}){0,2})\b",
    )
    for pattern in patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            return str(match.group(1) or "").strip()
    return ""


def _extract_dependency_spec(raw: str, normalized: str) -> str:
    if "requirements.txt" in normalized:
        return "requirements.txt"
    pip_match = re.search(r"\bpip install\s+([a-z0-9_.<>=,\-\s]+)", normalized)
    if pip_match:
        packages = " ".join(str(pip_match.group(1) or "").split())
        if packages:
            return packages
    if any(token in normalized for token in ("abhaengigkeiten", "dependencies", "dependencies:", "pakete", "packages")):
        return "specified"
    return ""


def _extract_build_or_runtime(normalized: str) -> str:
    if any(token in normalized for token in ("build-container", "build container", "builder-container", "builder container")):
        return "build"
    if any(token in normalized for token in ("runtime-container", "runtime container", "laufzeit-container", "laufzeit container")):
        return "runtime"
    return ""


def _extract_persistent_workdir(normalized: str) -> bool:
    markers = (
        "persistenten arbeitsverzeichnis",
        "persistent workdir",
        "persistent workspace",
        "persistentes arbeitsverzeichnis",
        "persistent volume",
        "gemountetes arbeitsverzeichnis",
        "mount",
        "volume",
    )
    return any(marker in normalized for marker in markers)


def extract_python_container_fields(text: Any) -> Dict[str, Any]:
    raw = str(text or "")
    normalized = _normalize(raw)
    fields: Dict[str, Any] = {}

    python_version = _extract_python_version(raw)
    if python_version:
        fields["python_version"] = python_version

    dependency_spec = _extract_dependency_spec(raw, normalized)
    if dependency_spec:
        fields["dependency_spec"] = dependency_spec

    build_or_runtime = _extract_build_or_runtime(normalized)
    if build_or_runtime:
        fields["build_or_runtime"] = build_or_runtime

    if _extract_persistent_workdir(normalized):
        fields["persistent_workdir"] = True

    return fields


def extract_container_identity_fields(text: Any) -> Dict[str, Any]:
    raw = str(text or "")
    normalized = _normalize(raw)
    out: Dict[str, Any] = {}

    container_id_match = re.search(
        r"\bcontainer[_\s-]?id\s*[:=]?\s*([a-z0-9][a-z0-9_.-]{2,63})\b",
        normalized,
        flags=re.IGNORECASE,
    )
    if container_id_match:
        candidate = str(container_id_match.group(1) or "").strip()
        if candidate and candidate not in {"container", "id"}:
            out["container_id"] = candidate

    name_patterns = (
        r"\bcontainer[_\s-]?name\s*[:=]?\s*([a-z0-9][a-z0-9_.-]{2,63})\b",
        r"\bcontainer\s+namens\s+([a-z0-9][a-z0-9_.-]{2,63})\b",
    )
    for pattern in name_patterns:
        name_match = re.search(pattern, normalized, flags=re.IGNORECASE)
        if not name_match:
            continue
        candidate = str(name_match.group(1) or "").strip()
        if candidate and candidate not in {"container", "name"}:
            out["container_name"] = candidate
            break

    if "trion-home" in normalized and "container_name" not in out:
        out["container_name"] = "trion-home"
    return out


__all__ = [
    "extract_container_identity_fields",
    "extract_container_request_fields",
    "extract_python_container_fields",
]
