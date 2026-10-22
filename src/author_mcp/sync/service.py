"""Knowledgebase synchronization service for Author-MCP.

Brought over from Hath0r Enterprise Knowledgebase architecture.
Synchronizes all active indices and documents into .hath0r/knowledgebase single source of truth.
"""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
import structlog

from author_mcp.config import settings
from author_mcp.storage.base import StorageBackend

logger = structlog.get_logger(__name__)


class KnowledgeSyncService:
    """Service to export and synchronize author documents to Hath0r knowledgebase."""

    def __init__(self, storage: StorageBackend) -> None:
        self.storage = storage

    def sync_to_hathor_knowledgebase(self, target_dir: Path | None = None) -> dict[str, Any]:
        """Export all indexed documents into standard Hath0r knowledge markdown files."""
        base_kb = target_dir or settings.HATHOR_KNOWLEDGEBASE_DIR
        dest_base = base_kb / "documents" / "books"
        dest_base.mkdir(parents=True, exist_ok=True)

        stats = self.storage.get_stats()
        synced_count = 0
        indices_synced = []

        for idx_info in self.storage.list_indices():
            idx_name = idx_info.name
            idx_dest = dest_base / idx_name
            idx_dest.mkdir(parents=True, exist_ok=True)

            # Iterate over docs in storage
            if hasattr(self.storage, "documents") and idx_name in self.storage.documents:
                for doc_id, doc in self.storage.documents[idx_name].items():
                    try:
                        safe_name = re.sub(r"[^\w\-.]", "_", doc_id)
                        if not safe_name.endswith(".md"):
                            safe_name = f"{safe_name}.md"

                        dest_file = idx_dest / safe_name
                        payload = (
                            f"---\n"
                            f"id: \"{doc.id}\"\n"
                            f"title: \"{doc.metadata.title or 'Untitled'}\"\n"
                            f"index: \"{doc.index_name}\"\n"
                            f"category: \"{doc.metadata.category}\"\n"
                            f"word_count: {doc.metadata.word_count}\n"
                            f"reading_time_minutes: {doc.metadata.reading_time_minutes}\n"
                            f"tags: {json.dumps(doc.metadata.tags)}\n"
                            f"synced_at: \"{datetime.now(timezone.utc).isoformat()}\"\n"
                            f"---\n\n"
                            f"# {doc.metadata.title or 'Untitled'}\n\n"
                            f"{doc.content}\n"
                        )
                        dest_file.write_text(payload, encoding="utf-8")
                        synced_count += 1
                    except Exception as e:
                        logger.error("sync_doc_failed", doc_id=doc_id, error=str(e))

            indices_synced.append(idx_name)

        return {
            "status": "success",
            "documents_synced": synced_count,
            "indices_synced": indices_synced,
            "target_directory": str(dest_base),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
