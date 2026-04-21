"""Timeout and response-mode helpers for ControlLayer runtime behavior."""


def normalize_response_mode(response_mode: str) -> str:
    """Normalize arbitrary response-mode input into the supported runtime values."""
    return "deep" if str(response_mode or "").strip().lower() == "deep" else "interactive"


def resolve_verify_timeout_s(
    response_mode: str = "interactive",
    *,
    get_control_timeout_interactive_s_fn,
    get_control_timeout_deep_s_fn,
) -> float:
    """Resolve the control verification timeout for the effective response mode."""
    mode = normalize_response_mode(response_mode)
    if mode == "deep":
        timeout_s = float(get_control_timeout_deep_s_fn())
    else:
        timeout_s = float(get_control_timeout_interactive_s_fn())
    return max(5.0, min(600.0, timeout_s))
