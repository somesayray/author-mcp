"""Unit tests for MetadataExtractor."""

from pathlib import Path
from author_mcp.indexing.metadata import MetadataExtractor


def test_metadata_extraction():
    content = (
        "---\n"
        "title: Custom Chapter Title\n"
        "series: Cyber Chronicles\n"
        "---\n\n"
        "# Chapter 4: The Core Protocol\n\n"
        "The mainframe booted cleanly."
    )
    extractor = MetadataExtractor()
    meta = extractor.extract_from_content(content)

    assert meta.title == "Custom Chapter Title"
    assert meta.chapter_number == 4
    assert meta.word_count > 0
    assert "manuscript" in meta.tags or "general" in meta.tags
