"""
core.layers.output.generation
===============================
Generation-Engine für den Output-Layer — 3 Module:

  async_stream  → generate_stream (AsyncGenerator) + generate (str)
  sync_stream   → generate_stream_sync (sync Generator, nur Ollama)
  tool_check    → chat_check_tools (NON-STREAMING Tool-Call-Prüfung)
"""
from core.layers.output.generation.async_stream import (  # noqa: F401
    generate_stream,
    generate,
)
from core.layers.output.generation.sync_stream import (  # noqa: F401
    generate_stream_sync,
)
from core.layers.output.generation.tool_check import (  # noqa: F401
    chat_check_tools,
)

__all__ = [
    "generate_stream",
    "generate",
    "generate_stream_sync",
    "chat_check_tools",
]
