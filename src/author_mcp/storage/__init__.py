"""Storage package for Author-MCP."""

from author_mcp.storage.base import StorageBackend
from author_mcp.storage.local import LocalStorageBackend

__all__ = ["StorageBackend", "LocalStorageBackend"]
