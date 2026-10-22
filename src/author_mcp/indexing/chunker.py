"""Document chunking implementation for Author text documents and manuscripts.

Brought over from Hath0r Enterprise Knowledgebase architecture.
Supports:
- markdown header-aware splitting (preserves book chapter/section hierarchy)
- smart paragraph & sentence splitting
- overlapping sliding window
"""

from __future__ import annotations

import re
import structlog
from author_mcp.core.models import Chunk

logger = structlog.get_logger(__name__)


class DocumentChunker:
    """Splits documents into overlapping chunks for indexing and LLM context."""

    PARAGRAPH_PATTERN = re.compile(r"\n\s*\n")
    SENTENCE_PATTERN = re.compile(r"(?<=[.!?])\s+(?=[A-Z0-9])")
    LINE_PATTERN = re.compile(r"\n")
    MARKDOWN_HEADER_PATTERN = re.compile(r"^(#{1,6}\s+.+)$", re.MULTILINE)

    def __init__(
        self,
        chunk_size: int = 1500,
        chunk_overlap: int = 200,
        min_chunk_size: int = 100,
        strategy: str = "smart",
    ) -> None:
        if chunk_overlap >= chunk_size:
            raise ValueError("chunk_overlap must be less than chunk_size")

        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.min_chunk_size = min_chunk_size
        self.strategy = strategy

    def chunk_text(self, text: str, initial_metadata: dict | None = None) -> list[Chunk]:
        """Split text into overlapping chunks using configured strategy."""
        if not text or len(text.strip()) == 0:
            return []

        if len(text) <= self.chunk_size:
            return [
                Chunk(
                    text=text.strip(),
                    index=0,
                    start_char=0,
                    end_char=len(text),
                    metadata=initial_metadata or {},
                )
            ]

        if self.strategy == "markdown":
            return self._chunk_markdown(text, initial_metadata)
        elif self.strategy == "sentence":
            return self._chunk_sentence(text, initial_metadata)
        elif self.strategy == "character":
            return self._chunk_character(text, initial_metadata)
        else:
            return self._chunk_smart(text, initial_metadata)

    def _chunk_smart(self, text: str, initial_meta: dict | None) -> list[Chunk]:
        """Smart chunking: tries paragraph, sentence, then word boundaries."""
        chunks: list[Chunk] = []
        start = 0
        index = 0

        while start < len(text):
            end = min(start + self.chunk_size, len(text))
            if end < len(text):
                end = self._find_break_point(text, start, end)

            chunk_text = text[start:end].strip()
            if chunk_text and len(chunk_text) >= self.min_chunk_size:
                chunks.append(
                    Chunk(
                        text=chunk_text,
                        index=index,
                        start_char=start,
                        end_char=end,
                        metadata=dict(initial_meta or {}),
                    )
                )
                index += 1

            if end >= len(text):
                break
            start = end - self.chunk_overlap
            if start >= end:
                start = end

        return chunks if chunks else [Chunk(text=text.strip(), index=0, start_char=0, end_char=len(text), metadata=initial_meta or {})]

    def _chunk_markdown(self, text: str, initial_meta: dict | None) -> list[Chunk]:
        """Markdown header-aware chunking for manuscripts, chapters, and lore bibles."""
        # Split on markdown headings
        sections = re.split(r"(?=(?:^|\n)#{1,6}\s+)", text)
        chunks: list[Chunk] = []
        current_text = ""
        current_header = ""
        index = 0
        start_char = 0

        for sec in sections:
            if not sec.strip():
                continue

            # Detect if section begins with a header
            header_match = re.match(r"^#{1,6}\s+(.+)$", sec.strip().split("\n")[0])
            if header_match:
                current_header = header_match.group(1).strip()

            if len(current_text) + len(sec) < self.chunk_size:
                current_text += sec
            else:
                if current_text.strip():
                    meta = dict(initial_meta or {})
                    if current_header:
                        meta["section_header"] = current_header
                    chunks.append(
                        Chunk(
                            text=current_text.strip(),
                            index=index,
                            start_char=start_char,
                            end_char=start_char + len(current_text),
                            metadata=meta,
                        )
                    )
                    index += 1
                    start_char += len(current_text)
                current_text = sec

        if current_text.strip():
            meta = dict(initial_meta or {})
            if current_header:
                meta["section_header"] = current_header
            chunks.append(
                Chunk(
                    text=current_text.strip(),
                    index=index,
                    start_char=start_char,
                    end_char=start_char + len(current_text),
                    metadata=meta,
                )
            )

        return chunks if chunks else self._chunk_smart(text, initial_meta)

    def _chunk_sentence(self, text: str, initial_meta: dict | None) -> list[Chunk]:
        sentences = re.split(r"(?<=[.!?])\s+", text)
        chunks: list[Chunk] = []
        current = ""
        index = 0
        start_char = 0

        for s in sentences:
            if not s.strip():
                continue
            if len(current) + len(s) < self.chunk_size:
                current = (current + " " + s).strip()
            else:
                if current.strip():
                    chunks.append(
                        Chunk(
                            text=current.strip(),
                            index=index,
                            start_char=start_char,
                            end_char=start_char + len(current),
                            metadata=dict(initial_meta or {}),
                        )
                    )
                    index += 1
                    start_char += len(current)
                current = s

        if current.strip():
            chunks.append(
                Chunk(
                    text=current.strip(),
                    index=index,
                    start_char=start_char,
                    end_char=start_char + len(current),
                    metadata=dict(initial_meta or {}),
                )
            )

        return chunks

    def _chunk_character(self, text: str, initial_meta: dict | None) -> list[Chunk]:
        chunks: list[Chunk] = []
        start = 0
        index = 0

        while start < len(text):
            end = min(start + self.chunk_size, len(text))
            chunk_text = text[start:end].strip()
            if chunk_text:
                chunks.append(
                    Chunk(
                        text=chunk_text,
                        index=index,
                        start_char=start,
                        end_char=end,
                        metadata=dict(initial_meta or {}),
                    )
                )
                index += 1
            if end >= len(text):
                break
            start = end - self.chunk_overlap

        return chunks

    def _find_break_point(self, text: str, start: int, end: int) -> int:
        search_region = text[max(start, end - 250):end]

        # Try paragraph break
        for match in self.PARAGRAPH_PATTERN.finditer(search_region):
            break_pos = max(start, end - 250) + match.end()
            if break_pos > start + self.min_chunk_size:
                return break_pos

        # Try sentence break
        for match in self.SENTENCE_PATTERN.finditer(search_region):
            break_pos = max(start, end - 250) + match.end()
            if break_pos > start + self.min_chunk_size:
                return break_pos

        # Try line break
        for match in self.LINE_PATTERN.finditer(search_region):
            break_pos = max(start, end - 250) + match.end()
            if break_pos > start + self.min_chunk_size:
                return break_pos

        # Try space break
        space_idx = text.rfind(" ", max(start, end - 50), end)
        if space_idx != -1 and space_idx > start + self.min_chunk_size:
            return space_idx + 1

        return end
