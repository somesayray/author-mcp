"""Unit tests for IndexingPipeline."""

from pathlib import Path
from author_mcp.indexing.pipeline import IndexingPipeline
from author_mcp.storage.local import LocalStorageBackend


def test_pipeline_directory_indexing(tmp_path: Path):
    storage = LocalStorageBackend(base_dir=tmp_path / "storage")
    docs_dir = tmp_path / "manuscripts"
    docs_dir.mkdir(parents=True)

    f1 = docs_dir / "chapter_01.md"
    f1.write_text("# Chapter 1: The Frontier\n\nOut on the digital frontier, code was currency.")

    pipeline = IndexingPipeline(storage=storage)
    res = pipeline.index_directory(docs_dir)

    assert res["status"] == "success"
    assert res["files_indexed"] >= 1

    hits = storage.search("digital frontier")
    assert len(hits) >= 1
    assert "Chapter 1: The Frontier" in hits[0].document.metadata.title
