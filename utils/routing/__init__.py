# utils/routing/ — Routing utilities
#
# Safe to import at package level (no config dependency):
from utils.routing.service_endpoint import (  # noqa: F401
    normalize_endpoint,
    is_truthy,
    is_running_in_container,
    docker_default_gateway_endpoint,
    unique_endpoints,
    is_generic_host_ip,
    resolve_public_endpoint_host,
    default_service_endpoint,
    candidate_service_endpoints,
)
from utils.routing.model_runtime import resolve_runtime_chat_model  # noqa: F401

# NOT imported eagerly here — both have transitive dep on `config.OLLAMA_BASE`
# which would cause circular imports during config package initialization:
#   utils.routing.role_endpoint  → config.OLLAMA_BASE
#   utils.routing.ollama_manager → utils.settings → (no cycle, but role_endpoint does)
# Import these directly when needed:
#   from utils.routing.role_endpoint import resolve_role_endpoint
#   from utils.routing import ollama_manager
