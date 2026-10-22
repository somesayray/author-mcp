"""Abstract storage interface for Author-MCP Knowledge Base."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any
from author_mcp.core.models import Document, IndexInfo, IndexStats, SearchResult


class StorageBackend(ABC):
    """Abstract interface for storing and querying documents across indices."""

    @abstractmethod
    def create_index(self, index_name: str, description: str = "") -> IndexInfo:
        pass

    @abstractmethod
    def delete_index(self, index_name: str) -> bool:
        pass

    @abstractmethod
    def list_indices(self) -> list[IndexInfo]:
        pass

    @abstractmethod
    def get_index_info(self, index_name: str) -> IndexInfo | None:
        pass

    @abstractmethod
    def add_document(self, document: Document) -> bool:
        pass

    @abstractmethod
    def get_document(self, doc_id: str, index_name: str | None = None) -> Document | None:
        pass

    @abstractmethod
    def remove_document(self, doc_id: str, index_name: str | None = None) -> bool:
        pass

    @abstractmethod
    def search(
        self,
        query: str,
        index_name: str | None = None,
        category: str | None = None,
        limit: int = 10,
    ) -> list[SearchResult]:
        pass

    @abstractmethod
    def get_stats(self) -> IndexStats:
        pass
