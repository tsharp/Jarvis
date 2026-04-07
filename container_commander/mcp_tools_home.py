"""
TRION home helpers for Container Commander MCP tools.
"""

from __future__ import annotations

import base64
import os
from typing import Any, Callable, Dict, Optional


def home_runtime_config() -> Dict[str, str]:
    try:
        from utils.trion_home_identity import load_home_identity

        identity = load_home_identity(create_if_missing=True)
    except Exception:
        identity = {}
    blueprint_id = str(identity.get("container_id") or "trion-home").strip() or "trion-home"
    container_path = (
        str(os.environ.get("TRION_HOME_CONTAINER_PATH", "")).strip()
        or str(identity.get("container_home_path") or "").strip()
        or "/home/trion"
    )
    volume_name = str(os.environ.get("TRION_HOME_VOLUME", "trion_home_data")).strip() or "trion_home_data"
    return {
        "blueprint_id": blueprint_id,
        "volume_name": volume_name,
        "container_path": container_path,
    }


def ensure_trion_home(
    *,
    current_container_id: Optional[str],
    set_container_id: Callable[[str], None],
    blueprint_id: str,
    volume_name: str,
    home_path: str,
    logger: Any,
) -> str:
    """Ensure TRION home container is running. Returns container_id."""
    from .engine import exec_in_container, list_containers, start_container, start_stopped_container
    from .blueprint_store import create_blueprint, get_blueprint
    from .models import Blueprint, ContainerStatus, MountDef, NetworkMode, ResourceLimits

    known = list_containers()
    for container in known:
        if container.blueprint_id == blueprint_id:
            if container.status == ContainerStatus.RUNNING:
                set_container_id(container.container_id)
                return container.container_id
            if container.status == ContainerStatus.STOPPED and start_stopped_container(container.container_id):
                set_container_id(container.container_id)
                exec_in_container(
                    container.container_id,
                    f"mkdir -p {home_path}/notes {home_path}/projects {home_path}/scripts {home_path}/.config",
                    timeout=10,
                )
                return container.container_id
            set_container_id(container.container_id)
            break

    blueprint = get_blueprint(blueprint_id)
    if not blueprint:
        logger.info("[TRION Home] Creating trion-home blueprint...")
        blueprint = Blueprint(
            id=blueprint_id,
            name="TRION Home Workspace",
            description="TRIONs persistenter Arbeitsbereich für Notizen, Projekte und Experimente",
            image="python:3.12-slim",
            resources=ResourceLimits(memory_limit="512m", cpu_limit="0.5", timeout_seconds=0),
            mounts=[MountDef(host=volume_name, container=home_path, type="volume")],
            network=NetworkMode.INTERNAL,
            tags=["system", "persistent", "home"],
            icon="🏠",
        )
        create_blueprint(blueprint)

    instance = start_container(
        blueprint_id=blueprint_id,
        resume_volume=volume_name,
    )
    set_container_id(instance.container_id)

    exec_in_container(
        instance.container_id,
        f"mkdir -p {home_path}/notes {home_path}/projects {home_path}/scripts {home_path}/.config",
        timeout=10,
    )

    return instance.container_id


def tool_home_start(
    args: dict,
    *,
    ensure_trion_home: Callable[[], str],
    inspect_container: Callable[[str], Dict[str, Any]],
    home_path: str,
    blueprint_id: str,
) -> dict:
    """Start or reuse the TRION home container and return a compact runtime payload."""
    _ = dict(args or {})
    container_id = ensure_trion_home()
    result = {
        "status": "running",
        "container_id": container_id,
        "blueprint_id": str(blueprint_id or "").strip(),
        "home_path": home_path,
    }

    try:
        details = inspect_container(container_id)
    except Exception as exc:
        result["warning"] = f"inspect_failed:{exc}"
        return result

    if not isinstance(details, dict):
        return result

    for key in (
        "name",
        "status",
        "running",
        "image",
        "ports",
        "connection",
        "ip_address",
        "mounts",
        "resource_limits",
    ):
        if key in details and details.get(key) is not None:
            result[key] = details.get(key)
    return result


def tool_home_write(
    args: dict,
    *,
    ensure_trion_home: Callable[[], str],
    exec_in_container: Callable[..., tuple[int, str]],
    home_path: str,
) -> dict:
    if "path" not in args:
        return {"error": "Missing required parameter 'path'. Example: 'notes/todo.md'"}
    if "content" not in args:
        return {"error": "Missing required parameter 'content'. Provide the text to write."}

    container_id = ensure_trion_home()
    path = args["path"].lstrip("/")
    content = args["content"]

    encoded = base64.b64encode(content.encode("utf-8")).decode("ascii")

    full_path = f"{home_path}/{path}"
    if "/" in path:
        parent_dir = f"{home_path}/{'/'.join(path.split('/')[:-1])}"
    else:
        parent_dir = home_path

    exit_code, output = exec_in_container(
        container_id,
        f"sh -c \"mkdir -p '{parent_dir}' && echo '{encoded}' | base64 -d > '{full_path}'\"",
        timeout=10,
    )

    if exit_code != 0:
        return {"error": f"Write failed: {output}"}

    return {
        "written": True,
        "path": path,
        "size": len(content),
        "container_id": container_id,
    }


def tool_home_read(
    args: dict,
    *,
    ensure_trion_home: Callable[[], str],
    exec_in_container: Callable[..., tuple[int, str]],
    home_path: str,
) -> dict:
    if "path" not in args:
        return {"error": "Missing required parameter 'path'. Example: 'notes/todo.md'"}

    container_id = ensure_trion_home()
    path = args["path"].lstrip("/")
    full_path = f"{home_path}/{path}"

    exit_code, output = exec_in_container(
        container_id,
        f"sh -c \"cat '{full_path}'\"",
        timeout=10,
    )

    if exit_code != 0:
        return {"error": f"Read failed: {output}", "path": path}

    return {
        "content": output,
        "path": path,
        "container_id": container_id,
    }


def tool_home_list(
    args: dict,
    *,
    ensure_trion_home: Callable[[], str],
    exec_in_container: Callable[..., tuple[int, str]],
    home_path: str,
) -> dict:
    container_id = ensure_trion_home()
    path = args.get("path", ".").lstrip("/")
    full_path = f"{home_path}/{path}" if path and path != "." else home_path

    exit_code, output = exec_in_container(
        container_id,
        f"sh -c \"ls -la '{full_path}'\"",
        timeout=10,
    )

    if exit_code != 0:
        return {"error": f"List failed: {output}", "path": path}

    return {
        "listing": output,
        "path": path,
        "container_id": container_id,
    }
