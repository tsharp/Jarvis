"""Endpoint override helpers for ControlLayer runtime behavior."""


def resolve_control_endpoint_override(
    response_mode: str = "interactive",
    *,
    get_control_endpoint_override_fn,
    resolve_ollama_base_endpoint_fn,
) -> str:
    """Resolve and normalize a configured Control endpoint override."""
    override = str(get_control_endpoint_override_fn(response_mode=response_mode) or "").strip()
    if not override:
        return ""
    return str(resolve_ollama_base_endpoint_fn(default_endpoint=override))
