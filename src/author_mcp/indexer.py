"""Knowledgebase Indexer and Search Engine for Author-MCP.

Powered by the Hath0r Enterprise Knowledgebase & Index Architecture:
- LocalStorageBackend (multi-index partitioned storage)
- DocumentChunker (smart, markdown, sentence chunking)
- MetadataExtractor (YAML frontmatter, category, word count, reading time)
- BM25Index (Okapi BM25 with title boost and snippet extraction)
- KnowledgeSyncService (sync to .hath0r/knowledgebase)
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any
import structlog

from author_mcp.config import settings
from author_mcp.core.models import Document, IndexInfo, IndexStats, SearchResult

DocumentRecord = Document
from author_mcp.indexing.chunker import DocumentChunker
from author_mcp.indexing.metadata import MetadataExtractor
from author_mcp.indexing.pipeline import IndexingPipeline
from author_mcp.storage.local import LocalStorageBackend
from author_mcp.sync.service import KnowledgeSyncService

logger = structlog.get_logger(__name__)


class KnowledgeIndexer:
    """Enterprise Knowledge Indexer for Author and Books text documents."""

    def __init__(
        self,
        storage_dir: Path | None = None,
        books_dir: Path | None = None,
        auto_load: bool = True,
    ) -> None:
        self.storage_dir = storage_dir or settings.STORAGE_DIR
        self.books_dir = books_dir or settings.BOOKS_DIR
        self.storage = LocalStorageBackend(base_dir=self.storage_dir)
        self.chunker = DocumentChunker(chunk_size=1500, chunk_overlap=200, strategy="markdown")
        self.metadata_extractor = MetadataExtractor()
        self.pipeline = IndexingPipeline(
            storage=self.storage,
            chunker=self.chunker,
            metadata_extractor=self.metadata_extractor,
        )
        self.sync_service = KnowledgeSyncService(storage=self.storage)

        import sys
        is_test = "pytest" in sys.modules or os.getenv("ENVIRONMENT") == "test" or settings.ENVIRONMENT == "test"
        if auto_load and not is_test:
            # If storage is empty, scan books directory
            stats = self.storage.get_stats()
            if stats.total_documents == 0 and self.books_dir.exists():
                try:
                    self.scan_and_index()
                except Exception as e:
                    logger.warning("auto_indexing_failed", error=str(e))

    @property
    def documents(self) -> dict[str, Document]:
        """Flattened dictionary of all documents across indices for backward compatibility."""
        flat = {}
        for idx_name, docs in self.storage.documents.items():
            for doc_id, doc in docs.items():
                flat[doc_id] = doc
        return flat

    @property
    def index_file(self) -> Path:
        return self.storage.base_dir

    def scan_and_index(self, force: bool = False, scan_onedrive: bool = False) -> dict[str, Any]:
        """Scan Books repository and optional OneDrive books context folders and update index."""
        sources_to_scan = []
        if self.books_dir.exists():
            sources_to_scan.append(("books_repo", self.books_dir))
        if scan_onedrive and self.books_dir == settings.BOOKS_DIR:
            if settings.ONEDRIVE_BOOKS_PATH.exists():
                sources_to_scan.append(("onedrive_books", settings.ONEDRIVE_BOOKS_PATH))
            if settings.ONEDRIVE_AUTHOR_PATH.exists():
                sources_to_scan.append(("onedrive_author", settings.ONEDRIVE_AUTHOR_PATH))

        total_files = 0
        total_chunks = 0

        for source_name, dir_path in sources_to_scan:
            try:
                res = self.pipeline.index_directory(dir_path=dir_path, force=force)
                total_files += res.get("files_indexed", 0)
                total_chunks += res.get("chunks_created", 0)
            except Exception as e:
                logger.error("scan_dir_failed", source=source_name, error=str(e))

        stats = self.storage.get_stats()

        if settings.HATHOR_SYNC_ENABLED:
            try:
                self.sync_to_hathor_knowledgebase()
            except Exception as e:
                logger.error("auto_sync_failed", error=str(e))

        return {
            "status": "success",
            "indexed_count": total_files,
            "chunks_created": total_chunks,
            "total_documents": stats.total_documents,
            "total_chunks": stats.total_chunks,
            "sources_scanned": [s[0] for s in sources_to_scan],
            "indices": list(stats.indices.keys()),
        }

    def search(
        self,
        query: str,
        index_name: str | None = None,
        source: str | None = None,
        category: str | None = None,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        """Search documents across indices using Okapi BM25 ranking."""
        hits = self.storage.search(
            query=query,
            index_name=index_name,
            category=category,
            limit=limit,
        )
        results = []
        for h in hits:
            doc = h.document
            if source and doc.metadata.source_type != source and doc.index_name != source:
                continue

            results.append({
                "id": doc.id,
                "score": h.score,
                "index": doc.index_name,
                "source": doc.metadata.source_type or doc.index_name,
                "title": doc.metadata.title or "Untitled",
                "relative_path": doc.metadata.relative_path or doc.id,
                "category": doc.metadata.category,
                "word_count": doc.metadata.word_count,
                "reading_time_minutes": doc.metadata.reading_time_minutes,
                "preview": doc.preview,
                "highlights": h.highlights,
                "tags": doc.metadata.tags,
                "path": doc.metadata.path,
                "chunk_index": doc.chunk_index,
                "total_chunks": doc.total_chunks,
            })
        return results

    def get_document(self, doc_id: str, index_name: str | None = None) -> dict[str, Any] | None:
        """Fetch complete document content and metadata."""
        doc = self.storage.get_document(doc_id, index_name=index_name)
        if not doc:
            return None
        return {
            "id": doc.id,
            "content": doc.content,
            "title": doc.metadata.title,
            "index": doc.index_name,
            "category": doc.metadata.category,
            "word_count": doc.metadata.word_count,
            "reading_time_minutes": doc.metadata.reading_time_minutes,
            "tags": doc.metadata.tags,
            "path": doc.metadata.path,
            "relative_path": doc.metadata.relative_path,
            "chunk_index": doc.chunk_index,
            "total_chunks": doc.total_chunks,
        }

    def list_documents(self, index_name: str | None = None, category: str | None = None) -> list[dict[str, Any]]:
        """List summary of indexed documents."""
        docs = []
        indices = [index_name] if index_name else list(self.storage.indices.keys())
        for idx in indices:
            for d in self.storage.documents.get(idx, {}).values():
                if category and d.metadata.category != category:
                    continue
                docs.append({
                    "id": d.id,
                    "index": d.index_name,
                    "title": d.metadata.title,
                    "category": d.metadata.category,
                    "relative_path": d.metadata.relative_path or d.id,
                    "word_count": d.metadata.word_count,
                    "preview": d.preview,
                    "tags": d.metadata.tags,
                })
        return sorted(docs, key=lambda x: (x["index"], x["title"] or ""))

    def get_sources_summary(self) -> dict[str, Any]:
        """Summary of active indices and document counts."""
        stats = self.storage.get_stats()
        return {
            "total_documents": stats.total_documents,
            "total_chunks": stats.total_chunks,
            "storage_bytes": stats.storage_bytes,
            "indices": {name: info.document_count for name, info in stats.indices.items()},
            "sources": stats.sources_summary,
        }

    def sync_to_hathor_knowledgebase(self, target_dir: Path | None = None) -> dict[str, Any]:
        """Synchronize indexed documents into .hath0r/knowledgebase single source of truth."""
        return self.sync_service.sync_to_hathor_knowledgebase(target_dir=target_dir)
