"""Unit tests for KnowledgeIndexer and search engine."""

from pathlib import Path
from author_mcp.indexer import KnowledgeIndexer, DocumentRecord


def test_indexer_in_memory(tmp_path: Path):
    storage = tmp_path / "indices"
    books = tmp_path / "books"
    books.mkdir(parents=True)
    doc_file = books / "chapter1.md"
    doc_file.write_text("# Chapter 1: The Beginning\n\nIt was a dark and stormy night in the cyber realm.")

    indexer = KnowledgeIndexer(storage_dir=storage, books_dir=books, auto_load=False)
    res = indexer.scan_and_index()

    assert res["status"] == "success"
    assert res["total_documents"] >= 1

    search_res = indexer.search("cyber realm")
    assert len(search_res) >= 1
    assert "chapter1" in search_res[0]["id"].lower()
    assert search_res[0]["score"] > 0
