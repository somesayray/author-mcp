"""Unit tests for LocalStorageBackend."""

from pathlib import Path
from author_mcp.core.models import Document, DocumentMetadata
from author_mcp.storage.local import LocalStorageBackend


def test_storage_create_and_search(tmp_path: Path):
    storage = LocalStorageBackend(base_dir=tmp_path / "storage")
    doc = Document(
        id="book1:chap1",
        content="The neural grid began humming with high voltage energy.",
        metadata=DocumentMetadata(title="Neural Grid Initiation", category="manuscript"),
        index_name="books",
    )
    storage.add_document(doc)

    retrieved = storage.get_document("book1:chap1")
    assert retrieved is not None
    assert retrieved.id == "book1:chap1"

    results = storage.search("neural grid")
    assert len(results) >= 1
    assert results[0].document.id == "book1:chap1"
    assert results[0].score > 0
