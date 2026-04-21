"""
config.context.chunking
========================
Long-Context Chunking-Konfiguration.

Wenn ein User-Input die Token-Schwelle überschreitet, zerlegt der
WorkspaceManager den Text in Chunks, verarbeitet sie getrennt durch
das LLM und aggregiert die Ergebnisse zu einer Meta-Summary.

CHUNKING_THRESHOLD  : Ab dieser geschätzten Token-Anzahl wird gechunkt.
CHUNK_MAX_TOKENS    : Maximale Tokens pro Chunk.
CHUNK_OVERLAP_TOKENS: Überlappung zwischen Chunks für Kontext-Erhalt.
ENABLE_CHUNKING     : Master-Toggle — false deaktiviert Chunking komplett.
"""
import os

CHUNKING_THRESHOLD = int(os.getenv("CHUNKING_THRESHOLD", "6000"))
CHUNK_MAX_TOKENS = int(os.getenv("CHUNK_MAX_TOKENS", "4000"))
CHUNK_OVERLAP_TOKENS = int(os.getenv("CHUNK_OVERLAP_TOKENS", "200"))
ENABLE_CHUNKING = os.getenv("ENABLE_CHUNKING", "true").lower() == "true"
