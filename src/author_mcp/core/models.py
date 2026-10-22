"""Core data models for Author-MCP Knowledge & Index Engine."""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from typing import Any
from pydantic import BaseModel, ConfigDict, Field


class DocumentMetadata(BaseModel):
    """Metadata associated with an Author document or manuscript."""

    path: str | None = None
    relative_path: str | None = None
    title: str | None = None
    source_type: str = "text"
    category: str = "general"  # manuscript, chapter, character, lore, outline, note, research
    series: str | None = None
    book: str | None = None
    chapter_number: int | None = None
    word_count: int = 0
    reading_time_minutes: float = 0.0
    tags: list[str] = Field(default_factory=list)
    author: str = "Ray Bayly"
    created_at: datetime | None = None
    updated_at: datetime | None = None
    extra: dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(extra="allow")


class Document(BaseModel):
    """A document or chunk to be indexed and searched in the Author library."""

    id: str
    content: str
    metadata: DocumentMetadata = Field(default_factory=DocumentMetadata)
    index_name: str = "books"
    chunk_index: int = 0
    total_chunks: int = 1

    @property
    def preview(self) -> str:
        cleaned = " ".join(self.content.split())
        return cleaned[:240] + "..." if len(cleaned) > 240 else cleaned

    @property
    def content_hash(self) -> str:
        return hashlib.sha256(self.content.encode("utf-8")).hexdigest()[:16]


class Chunk(BaseModel):
    """A chunk of text produced by DocumentChunker."""

    text: str
    index: int
    start_char: int
    end_char: int
    metadata: dict[str, Any] = Field(default_factory=dict)

    @property
    def hash(self) -> str:
        return hashlib.md5(self.text.encode("utf-8")).hexdigest()[:12]


class SearchResult(BaseModel):
    """A ranked search result with relevance score and highlight snippets."""

    document: Document
    score: float = Field(ge=0.0)
    bm25_score: float | None = None
    highlights: list[str] = Field(default_factory=list)


class SearchQuery(BaseModel):
    """Search request specification."""

    query: str
    index_name: str | None = None
    source: str | None = None
    category: str | None = None
    limit: int = Field(default=10, ge=1, le=100)
    min_score: float = 0.0
    filters: dict[str, Any] = Field(default_factory=dict)


class IndexInfo(BaseModel):
    """Information and statistics about an active index."""

    name: str
    description: str = ""
    document_count: int = 0
    chunk_count: int = 0
    total_bytes: int = 0
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class IndexStats(BaseModel):
    """Aggregate statistics across all indexes."""

    total_documents: int = 0
    total_chunks: int = 0
    indices: dict[str, IndexInfo] = Field(default_factory=dict)
    storage_bytes: int = 0
    sources_summary: dict[str, int] = Field(default_factory=dict)
