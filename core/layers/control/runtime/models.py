"""Model resolution helpers for ControlLayer runtime paths."""


def resolve_control_model(
    model_override: str | None,
    response_mode: str = "interactive",
    *,
    get_control_model_fn,
    get_control_model_deep_fn,
) -> str:
    """Resolve the effective control model for the current response mode."""
    if model_override:
        return str(model_override)
    mode = str(response_mode or "").strip().lower()
    if mode == "deep":
        return str(get_control_model_deep_fn())
    return str(get_control_model_fn())


def resolve_sequential_model(*, get_thinking_model_fn) -> str:
    """Resolve the model used for sequential reasoning side paths."""
    return str(get_thinking_model_fn())
