"""Core package for Author-MCP."""

from author_mcp.core.models import (
    Chunk,
    Document,
    DocumentMetadata,
    IndexInfo,
    IndexStats,
    SearchQuery,
    SearchResult,
)

__all__ = [
    "Chunk",
    "Document",
    "DocumentMetadata",
    "IndexInfo",
    "IndexStats",
    "SearchQuery",
    "SearchResult",
]
