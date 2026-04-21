from utils.embedding.resolver import (  # noqa: F401
    RoutingDecision,
    resolve_embedding_target,
    DEFAULT_EXECUTION_MODE,
    DEFAULT_FALLBACK_POLICY,
    DEFAULT_ENDPOINT_MODE,
    VALID_EXECUTION_MODES,
    VALID_FALLBACK_POLICIES,
    VALID_ENDPOINT_MODES,
)
from utils.embedding.health import check_embedding_availability, clear_health_cache  # noqa: F401
from utils.embedding.metrics import (  # noqa: F401
    increment_fallback,
    increment_error,
    record_latency,
    get_metrics,
    reset_metrics,
)
