"""Local file-based and in-memory multi-index storage backend for Author-MCP.

Brought over from Hath0r Enterprise Knowledgebase architecture.
Provides structured index partitioning ({storage_dir}/{index_name}/documents/{doc_id}.json),
per-index BM25 search engines, and cross-index aggregation.
"""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
import structlog

from author_mcp.config import settings
from author_mcp.core.models import Document, DocumentMetadata, IndexInfo, IndexStats, SearchResult
from author_mcp.core.observability import timed_operation
from author_mcp.search.bm25 import BM25Index
from author_mcp.storage.base import StorageBackend

logger = structlog.get_logger(__name__)


class LocalStorageBackend(StorageBackend):
    """File-backed and in-memory storage engine supporting multiple indices."""

    def __init__(self, base_dir: Path | None = None) -> None:
        self.base_dir = base_dir or settings.STORAGE_DIR
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self.indices: dict[str, IndexInfo] = {}
        self.documents: dict[str, dict[str, Document]] = {}  # index_name -> {doc_id: Document}
        self.search_engines: dict[str, BM25Index] = {}  # index_name -> BM25Index

        # Default indices for Author project
        self._init_default_indices()
        self._load_from_disk()

    def _init_default_indices(self) -> None:
        defaults = [
            ("books", "Core manuscripts, chapters, and published books"),
            ("lore", "Worldbuilding, lore bibles, history, and faction codices"),
            ("characters", "Dramatis personae, character dossiers, and arcs"),
            ("outlines", "Story arcs, beat sheets, and synopses"),
            ("notes", "Author notes, research, and memos"),
        ]
        for name, desc in defaults:
            if name not in self.indices:
                self.create_index(name, desc)

    def _get_index_dir(self, index_name: str) -> Path:
        return self.base_dir / index_name

    def _get_docs_dir(self, index_name: str) -> Path:
        d = self._get_index_dir(index_name) / "documents"
        d.mkdir(parents=True, exist_ok=True)
        return d

    def create_index(self, index_name: str, description: str = "") -> IndexInfo:
        idx_dir = self._get_index_dir(index_name)
        idx_dir.mkdir(parents=True, exist_ok=True)
        self._get_docs_dir(index_name)

        info = IndexInfo(
            name=index_name,
            description=description,
            document_count=0,
            chunk_count=0,
            total_bytes=0,
            updated_at=datetime.now(timezone.utc),
        )
        self.indices[index_name] = info
        if index_name not in self.documents:
            self.documents[index_name] = {}
        if index_name not in self.search_engines:
            self.search_engines[index_name] = BM25Index()

        self._save_index_metadata(index_name)
        return info

    def delete_index(self, index_name: str) -> bool:
        if index_name not in self.indices:
            return False
        del self.indices[index_name]
        if index_name in self.documents:
            del self.documents[index_name]
        if index_name in self.search_engines:
            del self.search_engines[index_name]

        idx_dir = self._get_index_dir(index_name)
        if idx_dir.exists():
            import shutil
            shutil.rmtree(idx_dir, ignore_errors=True)
        return True

    def list_indices(self) -> list[IndexInfo]:
        return list(self.indices.values())

    def get_index_info(self, index_name: str) -> IndexInfo | None:
        return self.indices.get(index_name)

    def _save_index_metadata(self, index_name: str) -> None:
        info = self.indices.get(index_name)
        if not info:
            return
        meta_file = self._get_index_dir(index_name) / "metadata.json"
        data = {
            "name": info.name,
            "description": info.description,
            "document_count": info.document_count,
            "chunk_count": info.chunk_count,
            "total_bytes": info.total_bytes,
            "updated_at": info.updated_at.isoformat(),
        }
        meta_file.write_text(json.dumps(data, indent=2), encoding="utf-8")

    def _load_from_disk(self) -> None:
        """Load all indices and persisted JSON documents from disk."""
        if not self.base_dir.exists():
            return

        for child in self.base_dir.iterdir():
            if child.is_dir() and not child.name.startswith("."):
                idx_name = child.name
                meta_file = child / "metadata.json"
                desc = ""
                if meta_file.exists():
                    try:
                        m_data = json.loads(meta_file.read_text(encoding="utf-8"))
                        desc = m_data.get("description", "")
                    except Exception:
                        pass
                self.create_index(idx_name, desc)

                docs_dir = child / "documents"
                if docs_dir.exists():
                    for f in docs_dir.glob("*.json"):
                        try:
                            d_json = json.loads(f.read_text(encoding="utf-8"))
                            doc = Document(**d_json)
                            self.documents[idx_name][doc.id] = doc
                            self.search_engines[idx_name].add_document(
                                doc_id=doc.id,
                                content=doc.content,
                                title=doc.metadata.title or "",
                                rebuild=False,
                            )
                        except Exception as e:
                            logger.warning("failed_loading_doc", path=str(f), error=str(e))

                    self.search_engines[idx_name]._recalculate_stats()
                    self._update_index_metrics(idx_name)

    def _update_index_metrics(self, index_name: str) -> None:
        if index_name not in self.indices or index_name not in self.documents:
            return
        docs = self.documents[index_name]
        total_b = sum(len(d.content.encode("utf-8")) for d in docs.values())
        unique_parents = len({d.metadata.path or d.id for d in docs.values()})

        self.indices[index_name].document_count = unique_parents
        self.indices[index_name].chunk_count = len(docs)
        self.indices[index_name].total_bytes = total_b
        self.indices[index_name].updated_at = datetime.now(timezone.utc)
        self._save_index_metadata(index_name)

    def add_document(self, document: Document) -> bool:
        """Add or update a document in its target index and persist to disk."""
        idx_name = document.index_name or "books"
        if idx_name not in self.indices:
            self.create_index(idx_name)

        self.documents[idx_name][document.id] = document
        self.search_engines[idx_name].add_document(
            doc_id=document.id,
            content=document.content,
            title=document.metadata.title or "",
            rebuild=True,
        )

        # Persist JSON file
        safe_name = re.sub(r"[^\w\-.]", "_", document.id) + ".json"
        doc_path = self._get_docs_dir(idx_name) / safe_name
        doc_path.write_text(document.model_dump_json(indent=2), encoding="utf-8")

        self._update_index_metrics(idx_name)
        return True

    def get_document(self, doc_id: str, index_name: str | None = None) -> Document | None:
        """Retrieve document by ID across specified or all indices."""
        indices_to_check = [index_name] if index_name else list(self.indices.keys())
        for idx in indices_to_check:
            if idx in self.documents and doc_id in self.documents[idx]:
                return self.documents[idx][doc_id]

        # Secondary search by relative_path or title
        for idx in indices_to_check:
            for doc in self.documents.get(idx, {}).values():
                if doc.metadata.relative_path == doc_id or (doc.metadata.title and doc.metadata.title.lower() == doc_id.lower()):
                    return doc

        return None

    def remove_document(self, doc_id: str, index_name: str | None = None) -> bool:
        indices_to_check = [index_name] if index_name else list(self.indices.keys())
        removed = False
        for idx in indices_to_check:
            if idx in self.documents and doc_id in self.documents[idx]:
                del self.documents[idx][doc_id]
                self.search_engines[idx].remove_document(doc_id)
                safe_name = re.sub(r"[^\w\-.]", "_", doc_id) + ".json"
                doc_path = self._get_docs_dir(idx) / safe_name
                if doc_path.exists():
                    doc_path.unlink()
                self._update_index_metrics(idx)
                removed = True
        return removed

    def search(
        self,
        query: str,
        index_name: str | None = None,
        category: str | None = None,
        limit: int = 10,
    ) -> list[SearchResult]:
        """Search using BM25 across target index or entire suite."""
        with timed_operation("local_storage_search", query=query, index=index_name):
            indices_to_search = [index_name] if index_name else list(self.indices.keys())
            all_results: list[SearchResult] = []

            for idx in indices_to_search:
                engine = self.search_engines.get(idx)
                if not engine:
                    continue

                hits = engine.search(query, limit=limit)
                for did, score in hits:
                    doc = self.documents[idx].get(did)
                    if not doc:
                        continue
                    if category and doc.metadata.category != category:
                        continue

                    highlights = engine.extract_highlights(did, query)
                    all_results.append(
                        SearchResult(
                            document=doc,
                            score=round(score, 4),
                            bm25_score=round(score, 4),
                            highlights=highlights,
                        )
                    )

            # Sort globally by score descending
            all_results.sort(key=lambda r: r.score, reverse=True)
            return all_results[:limit]

    def get_stats(self) -> IndexStats:
        """Global aggregated statistics."""
        total_docs = sum(i.document_count for i in self.indices.values())
        total_chunks = sum(i.chunk_count for i in self.indices.values())
        total_bytes = sum(i.total_bytes for i in self.indices.values())

        sources: dict[str, int] = {}
        for idx_name, docs in self.documents.items():
            for d in docs.values():
                src = d.metadata.source_type or idx_name
                sources[src] = sources.get(src, 0) + 1

        return IndexStats(
            total_documents=total_docs,
            total_chunks=total_chunks,
            indices=self.indices,
            storage_bytes=total_bytes,
            sources_summary=sources,
        )
