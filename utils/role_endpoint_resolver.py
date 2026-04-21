# compat shim — moved to utils/routing/role_endpoint.py
from utils.routing.role_endpoint import *  # noqa: F401,F403
from utils.routing.role_endpoint import (  # noqa: F401
    _CACHE,
    _CACHE_LOCK,
    _CACHE_TTL_SECONDS,
    _DISCOVERY_CACHE,
    _DISCOVERY_CACHE_LOCK,
    _DISCOVERY_TTL_SECONDS,
    _DISCOVERY_TIMEOUT_S,
    _candidate_default_endpoints,
    _docker_default_gateway_endpoint,
    _is_truthy,
    _normalize_endpoint,
    _probe_ollama_tags,
    _build_snapshot,
    _get_snapshot,
    _instances_from_snapshot,
    _recover_endpoint_from_instances,
)
