# compat shim — moved to utils/text/chunker.py
from utils.text.chunker import *  # noqa: F401,F403
from utils.text.chunker import (  # noqa: F401
    Chunker,
    TextChunk,
    ChunkType,
    BoundaryDetector,
    DocumentStructure,
)
