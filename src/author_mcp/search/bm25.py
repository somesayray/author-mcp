"""BM25 ranking and inverted index implementation for Author-MCP.

Brought over from Hath0r Enterprise Knowledgebase architecture.
Implements Okapi BM25 ranking algorithm with field boosting and snippet extraction.
"""

from __future__ import annotations

import math
import re
from collections import Counter
import structlog

logger = structlog.get_logger(__name__)


class BM25Index:
    """Okapi BM25 Index with field weighting and incremental updates."""

    def __init__(self, k1: float = 1.5, b: float = 0.75) -> None:
        self.k1 = k1
        self.b = b
        self.documents: dict[str, str] = {}
        self.titles: dict[str, str] = {}
        self.doc_tokens: dict[str, list[str]] = {}
        self.doc_lengths: dict[str, int] = {}
        self.inverted_index: dict[str, set[str]] = {}
        self.term_freqs: dict[str, Counter[str]] = {}
        self.avg_doc_len: float = 0.0

    def tokenize(self, text: str) -> list[str]:
        """Simple and fast lowercase word tokenizer."""
        return re.findall(r"\b\w{2,}\b", text.lower())

    def add_document(self, doc_id: str, content: str, title: str = "", rebuild: bool = True) -> None:
        """Add or update a document in the BM25 index."""
        tokens = self.tokenize(content)
        self.documents[doc_id] = content
        self.titles[doc_id] = title
        self.doc_tokens[doc_id] = tokens
        self.doc_lengths[doc_id] = len(tokens)
        self.term_freqs[doc_id] = Counter(tokens)

        for token in set(tokens):
            if token not in self.inverted_index:
                self.inverted_index[token] = set()
            self.inverted_index[token].add(doc_id)

        if rebuild:
            self._recalculate_stats()

    def add_documents_bulk(self, docs: list[tuple[str, str, str]]) -> None:
        """Bulk add documents: list of (doc_id, content, title)."""
        for doc_id, content, title in docs:
            self.add_document(doc_id, content, title, rebuild=False)
        self._recalculate_stats()

    def remove_document(self, doc_id: str) -> bool:
        if doc_id not in self.documents:
            return False

        del self.documents[doc_id]
        if doc_id in self.titles:
            del self.titles[doc_id]
        if doc_id in self.doc_tokens:
            del self.doc_tokens[doc_id]
        if doc_id in self.doc_lengths:
            del self.doc_lengths[doc_id]
        if doc_id in self.term_freqs:
            del self.term_freqs[doc_id]

        for token_docs in self.inverted_index.values():
            token_docs.discard(doc_id)

        self._recalculate_stats()
        return True

    def clear(self) -> None:
        self.documents.clear()
        self.titles.clear()
        self.doc_tokens.clear()
        self.doc_lengths.clear()
        self.inverted_index.clear()
        self.term_freqs.clear()
        self.avg_doc_len = 0.0

    def _recalculate_stats(self) -> None:
        total_len = sum(self.doc_lengths.values())
        self.avg_doc_len = total_len / max(1, len(self.documents))

    def search(self, query: str, limit: int = 10) -> list[tuple[str, float]]:
        """Search query using Okapi BM25 formula with title match boost."""
        tokens = self.tokenize(query)
        if not tokens or not self.documents:
            return []

        n_total = len(self.documents)
        scores: dict[str, float] = {}

        for token in set(tokens):
            matching_docs = self.inverted_index.get(token, set())
            df = len(matching_docs)
            if df == 0:
                continue

            # Standard Okapi BM25 IDF
            idf = math.log(1.0 + (n_total - df + 0.5) / (df + 0.5))

            for did in matching_docs:
                tf = self.term_freqs[did][token]
                doc_len = self.doc_lengths[did]

                numerator = tf * (self.k1 + 1.0)
                denominator = tf + self.k1 * (1.0 - self.b + self.b * (doc_len / max(1e-6, self.avg_doc_len)))
                score = idf * (numerator / max(1e-6, denominator))

                # Exact title match boost
                title = self.titles.get(did, "").lower()
                if token in title:
                    score += 2.5

                scores[did] = scores.get(did, 0.0) + score

        ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        return ranked[:limit]

    def extract_highlights(self, doc_id: str, query: str, max_snippets: int = 2, snippet_len: int = 160) -> list[str]:
        """Extract matching sentence snippets around query keywords."""
        content = self.documents.get(doc_id, "")
        if not content:
            return []

        tokens = set(self.tokenize(query))
        sentences = re.split(r"(?<=[.!?])\s+", content)
        highlights = []

        for s in sentences:
            s_clean = s.strip()
            if not s_clean:
                continue
            s_tokens = set(self.tokenize(s_clean))
            if tokens.intersection(s_tokens):
                if len(s_clean) > snippet_len:
                    s_clean = s_clean[:snippet_len] + "..."
                highlights.append(s_clean)
                if len(highlights) >= max_snippets:
                    break

        return highlights
