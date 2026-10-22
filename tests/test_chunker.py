"""Unit tests for DocumentChunker."""

from author_mcp.indexing.chunker import DocumentChunker


def test_chunker_markdown():
    text = (
        "# Chapter 1: The Gathering\n\n"
        "Paragraph one discussing the gathering of the characters.\n\n"
        "## Section 1.1: The Vault\n\n"
        "Paragraph two detailing the underground vault."
    )
    chunker = DocumentChunker(chunk_size=100, chunk_overlap=20, strategy="markdown")
    chunks = chunker.chunk_text(text)
    assert len(chunks) >= 1
    assert all(hasattr(c, "text") for c in chunks)
    assert all(len(c.text) > 0 for c in chunks)


def test_chunker_smart():
    text = "First sentence here. Second sentence follows. Third sentence concludes."
    chunker = DocumentChunker(chunk_size=40, chunk_overlap=10, strategy="smart")
    chunks = chunker.chunk_text(text)
    assert len(chunks) >= 1
