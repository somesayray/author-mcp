"""Document indexing pipeline for Author-MCP Knowledge & Index Engine.

Brought over from Hath0r Enterprise Knowledgebase architecture.
Orchestrates: file reading -> metadata extraction -> chapter & header chunking -> index storage.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any
import structlog

from author_mcp.core.models import Document, DocumentMetadata
from author_mcp.core.observability import timed_operation
from author_mcp.indexing.chunker import DocumentChunker
from author_mcp.indexing.metadata import MetadataExtractor
from author_mcp.storage.base import StorageBackend

logger = structlog.get_logger(__name__)

SUPPORTED_EXTENSIONS = {
    ".md",
    ".txt",
    ".text",
    ".rst",
    ".json",
    ".yaml",
    ".yml",
    ".docx",
}


IGNORE_DIRS = {
    "__pycache__",
    "node_modules",
    "site",
    ".git",
    ".hath0r",
    ".pytest_cache",
    "Social Media",
    "marketing",
    "Videos",
    "videos",
    "images",
    "assets",
    "Fonts",
    "Tattoos",
    "profile-pics",
}


class IndexingPipeline:
    """Enterprise indexing pipeline for Author manuscripts and text documents."""

    def __init__(
        self,
        storage: StorageBackend,
        chunker: DocumentChunker | None = None,
        metadata_extractor: MetadataExtractor | None = None,
    ) -> None:
        self.storage = storage
        self.chunker = chunker or DocumentChunker(chunk_size=1500, chunk_overlap=200, strategy="markdown")
        self.metadata_extractor = metadata_extractor or MetadataExtractor()

    def index_text(
        self,
        content: str,
        doc_id: str,
        index_name: str | None = None,
        metadata: dict[str, Any] | None = None,
        chunk: bool = True,
    ) -> list[Document]:
        """Index raw text content into the storage engine."""
        doc_meta = self.metadata_extractor.extract_from_content(content)
        if metadata:
            for k, v in metadata.items():
                if hasattr(doc_meta, k):
                    setattr(doc_meta, k, v)
                else:
                    doc_meta.extra[k] = v

        target_index = index_name or self._resolve_target_index(doc_meta.category)

        docs_created: list[Document] = []
        if chunk and len(content) > self.chunker.chunk_size:
            chunks = self.chunker.chunk_text(content, initial_metadata={"doc_id": doc_id})
            total = len(chunks)
            for ch in chunks:
                chunk_meta = doc_meta.model_copy(deep=True)
                chunk_meta.extra["chunk_index"] = ch.index
                chunk_meta.extra["total_chunks"] = total
                if "section_header" in ch.metadata:
                    chunk_meta.extra["section_header"] = ch.metadata["section_header"]

                chunk_doc = Document(
                    id=f"{doc_id}#chunk_{ch.index}",
                    content=ch.text,
                    metadata=chunk_meta,
                    index_name=target_index,
                    chunk_index=ch.index,
                    total_chunks=total,
                )
                self.storage.add_document(chunk_doc)
                docs_created.append(chunk_doc)
        else:
            doc = Document(
                id=doc_id,
                content=content,
                metadata=doc_meta,
                index_name=target_index,
                chunk_index=0,
                total_chunks=1,
            )
            self.storage.add_document(doc)
            docs_created.append(doc)

        return docs_created

    def _extract_text(self, path: Path) -> str:
        """Extract text from file, including native .docx support."""
        ext = path.suffix.lower()
        if ext == ".docx":
            import zipfile
            import xml.etree.ElementTree as ET
            try:
                with zipfile.ZipFile(path) as z:
                    xml_content = z.read("word/document.xml")
                    tree = ET.fromstring(xml_content)
                    texts = [
                        node.text for node in tree.iter("{http://schemas.openxmlformats.org/wordprocessingml/2006/main}t")
                        if node.text
                    ]
                    return " ".join(texts)
            except Exception as e:
                logger.warning("docx_extract_failed", path=str(path), error=str(e))
                return ""
        try:
            return path.read_text(encoding="utf-8", errors="ignore")
        except Exception as e:
            logger.warning("file_read_failed", path=str(path), error=str(e))
            return ""

    def index_file(
        self,
        file_path: Path | str,
        base_dir: Path | None = None,
        index_name: str | None = None,
        force: bool = False,
    ) -> list[Document]:
        """Index a single file with full metadata and chunking."""
        path = Path(file_path).resolve()
        if not path.is_file() or path.suffix.lower() not in SUPPORTED_EXTENSIONS:
            return []

        rel_path = str(path.relative_to(base_dir)) if base_dir else path.name
        doc_id = rel_path

        try:
            content = self._extract_text(path)
            if not content.strip():
                return []

            meta = self.metadata_extractor.extract_from_content(content, file_path=path)
            meta.relative_path = rel_path
            meta.source_type = "file"

            target_index = index_name or self._resolve_target_index(meta.category)
            return self.index_text(
                content=content,
                doc_id=doc_id,
                index_name=target_index,
                metadata=meta.model_dump(),
                chunk=True,
            )
        except Exception as e:
            logger.error("index_file_failed", path=str(path), error=str(e))
            return []

    def index_directory(
        self,
        dir_path: Path | str,
        index_name: str | None = None,
        force: bool = False,
    ) -> dict[str, Any]:
        """Recursively scan and index an entire directory."""
        root = Path(dir_path).resolve()
        if not root.is_dir():
            return {"status": "error", "message": f"Directory not found: {dir_path}"}

        with timed_operation("pipeline_index_directory", dir=str(root)) as op_info:
            files_indexed = 0
            chunks_created = 0

            for cur_root, dirs, files in os.walk(root):
                # Filter out hidden and system/media dirs
                dirs[:] = [
                    d for d in dirs
                    if not d.startswith(".") and d not in IGNORE_DIRS
                ]
                for fname in files:
                    if fname.startswith("."):
                        continue
                    fpath = Path(cur_root) / fname
                    if fpath.suffix.lower() in SUPPORTED_EXTENSIONS:
                        docs = self.index_file(fpath, base_dir=root, index_name=index_name, force=force)
                        if docs:
                            files_indexed += 1
                            chunks_created += len(docs)

            return {
                "status": "success",
                "directory": str(root),
                "files_indexed": files_indexed,
                "chunks_created": chunks_created,
                "elapsed_ms": op_info.get("elapsed_ms", 0),
            }

    def _resolve_target_index(self, category: str) -> str:
        cat_map = {
            "manuscript": "books",
            "lore": "lore",
            "characters": "characters",
            "outlines": "outlines",
            "notes": "notes",
        }
        return cat_map.get(category.lower(), "books")
