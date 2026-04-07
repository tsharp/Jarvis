# core/bridge.py
"""
Core-Bridge: Thin delegation layer to PipelineOrchestrator.

All pipeline logic lives in orchestrator.py.
Bridge exists for backward compatibility (get_bridge() singleton pattern).
"""

from typing import Optional, Dict, Tuple, AsyncGenerator

from .models import CoreChatRequest, CoreChatResponse
from .orchestrator import PipelineOrchestrator
from .layers.thinking import ThinkingLayer  # patch target
from .layers.control import ControlLayer   # patch target
from .layers.output import OutputLayer     # patch target
from config import ENABLE_CONTROL_LAYER, SKIP_CONTROL_ON_LOW_RISK  # patch targets

from config import OLLAMA_BASE
from mcp.hub import get_hub
from utils.logger import log_info


class CoreBridge:
    """
    Thin wrapper around PipelineOrchestrator.
    Maintains backward-compatible get_bridge() singleton API.
    """

    def __init__(self):
        self.orchestrator = PipelineOrchestrator()

        # Expose orchestrator's layers for backward compatibility
        self.thinking = self.orchestrator.thinking
        self.control = self.orchestrator.control
        self.output = self.orchestrator.output
        self.registry = self.orchestrator.registry
        self.ollama_base = OLLAMA_BASE

        # Legacy compatibility hook for tests and older callers that expect
        # CoreBridge to wire a fresh ControlLayer instance with MCPHub.
        try:
            legacy_control = ControlLayer()
            legacy_control.set_mcp_hub(get_hub())
        except Exception:
            pass

        log_info("[CoreBridge] Initialized with PipelineOrchestrator")

    async def process(self, request: CoreChatRequest) -> CoreChatResponse:
        """
        Backward-compatible non-streaming flow.
        Always delegates to the full orchestrator pipeline so sync and stream
        share identical routing, control, tool execution, and grounding logic.
        """
        return await self.orchestrator.process(request)

    async def process_stream(
        self,
        request: CoreChatRequest
    ) -> AsyncGenerator[Tuple[str, bool, Dict], None]:
        """Delegates to PipelineOrchestrator streaming."""
        async for chunk in self.orchestrator.process_stream_with_events(request):
            yield chunk


# ═══════════════════════════════════════════════════════════
# SINGLETON
# ═══════════════════════════════════════════════════════════

_bridge_instance: Optional[CoreBridge] = None

def get_bridge() -> CoreBridge:
    global _bridge_instance
    if _bridge_instance is None:
        _bridge_instance = CoreBridge()
    return _bridge_instance
