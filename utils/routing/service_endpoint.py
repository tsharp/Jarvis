from __future__ import annotations

import os
from pathlib import Path
from typing import Iterable, List, Optional


def normalize_endpoint(endpoint: str) -> str:
    return str(endpoint or "").strip().rstrip("/")


def is_truthy(value: str) -> bool:
    return str(value or "").strip().lower() in {"1", "true", "yes", "on"}


def is_running_in_container() -> bool:
    if Path("/.dockerenv").exists():
        return True
    try:
        content = Path("/proc/1/cgroup").read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return False
    lowered = content.lower()
    return any(marker in lowered for marker in ("docker", "containerd", "kubepods", "podman"))


def docker_default_gateway_endpoint(port: int, *, scheme: str = "http") -> Optional[str]:
    try:
        with open("/proc/net/route", "r", encoding="utf-8") as fh:
            next(fh, None)
            for line in fh:
                cols = line.strip().split()
                if len(cols) < 4:
                    continue
                destination = cols[1]
                gateway_hex = cols[2]
                flags_hex = cols[3]
                if destination != "00000000":
                    continue
                try:
                    flags = int(flags_hex, 16)
                except Exception:
                    continue
                if not (flags & 0x2):
                    continue
                try:
                    raw = bytes.fromhex(gateway_hex)
                except Exception:
                    continue
                if len(raw) != 4:
                    continue
                ip = ".".join(str(b) for b in raw[::-1])
                if ip and ip != "0.0.0.0":
                    return f"{scheme}://{ip}:{int(port)}"
    except Exception:
        return None
    return None


def unique_endpoints(values: Iterable[str]) -> List[str]:
    out: List[str] = []
    seen = set()
    for raw in values:
        endpoint = normalize_endpoint(str(raw or ""))
        if not endpoint or endpoint in seen:
            continue
        seen.add(endpoint)
        out.append(endpoint)
    return out


def is_generic_host_ip(value: str) -> bool:
    return str(value or "").strip() in {"", "0.0.0.0", "::"}


def resolve_public_endpoint_host(
    *,
    configured_public_host: str = "",
    host_ip: str = "",
) -> str:
    configured = str(configured_public_host or "").strip()
    if configured:
        return configured
    candidate = str(host_ip or "").strip()
    return "" if is_generic_host_ip(candidate) else candidate


def default_service_endpoint(
    service_name: str,
    port: int,
    *,
    scheme: str = "http",
    local_host: str = "127.0.0.1",
) -> str:
    host = str(service_name or "").strip() if is_running_in_container() else str(local_host or "127.0.0.1").strip()
    return f"{scheme}://{host}:{int(port)}"


def candidate_service_endpoints(
    *,
    configured: str = "",
    port: int,
    scheme: str = "http",
    service_name: str = "",
    prefer_container_service: Optional[bool] = None,
    extra: Iterable[str] | None = None,
    include_gateway: bool = True,
    include_host_docker: bool = True,
    include_loopback: bool = True,
    include_localhost: bool = True,
) -> List[str]:
    candidates: List[str] = []
    normalized_configured = normalize_endpoint(configured)
    if normalized_configured:
        candidates.append(normalized_configured)

    use_service = bool(str(service_name or "").strip())
    if prefer_container_service is None:
        use_service = use_service and is_running_in_container()
    else:
        use_service = use_service and bool(prefer_container_service)
    if use_service:
        candidates.append(f"{scheme}://{str(service_name).strip()}:{int(port)}")

    for raw in list(extra or []):
        candidates.append(str(raw or ""))

    if include_gateway:
        gateway = docker_default_gateway_endpoint(port, scheme=scheme)
        if gateway:
            candidates.append(gateway)
    if include_host_docker:
        candidates.append(f"{scheme}://host.docker.internal:{int(port)}")
    if include_loopback:
        candidates.append(f"{scheme}://127.0.0.1:{int(port)}")
    if include_localhost:
        candidates.append(f"{scheme}://localhost:{int(port)}")
    return unique_endpoints(candidates)
