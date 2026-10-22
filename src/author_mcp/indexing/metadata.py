"""Metadata extraction for Author text documents and manuscripts.

Brought over from Hath0r Enterprise Knowledgebase architecture.
Analyzes text content, frontmatter, document taxonomy, word counts, and chapter hierarchy.
"""

from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path
from typing import Any
import yaml

from author_mcp.core.models import DocumentMetadata


class MetadataExtractor:
    """Extracts rich metadata, taxonomy, and metrics from text documents."""

    MARKDOWN_TITLE_PATTERN = re.compile(r"^#\s+(.+)$", re.MULTILINE)
    YAML_FRONTMATTER_PATTERN = re.compile(r"^---[ \t]*\n(.*?)\n---[ \t]*\n", re.DOTALL)
    CHAPTER_PATTERN = re.compile(r"\bchapter\s+(\d+|one|two|three|four|five|six|seven|eight|nine|ten|[ivxlcdm]+)\b", re.IGNORECASE)
    SCENE_PATTERN = re.compile(r"\bscene\s+(\d+)\b", re.IGNORECASE)

    CATEGORY_KEYWORDS = {
        "manuscript": ["prologue", "epilogue", "chapter", "act ", "scene ", "draft", "manuscript"],
        "characters": ["character", "dossier", "persona", "protagonist", "antagonist", "biography"],
        "lore": ["lore", "worldbuilding", "history", "faction", "magic", "technology", "timeline"],
        "outlines": ["outline", "synopsis", "beat sheet", "treatment", "story arc", "pitch"],
        "notes": ["note", "memo", "research", "idea", "journal", "todo"],
    }

    def extract_from_content(self, content: str, file_path: Path | None = None) -> DocumentMetadata:
        """Extract structured DocumentMetadata from file content."""
        title = None
        extra: dict[str, Any] = {}
        cleaned_content = content

        # Check for YAML frontmatter
        fm_match = self.YAML_FRONTMATTER_PATTERN.match(content)
        if fm_match:
            raw_fm = fm_match.group(1)
            try:
                fm_data = yaml.safe_load(raw_fm)
                if isinstance(fm_data, dict):
                    extra.update(fm_data)
                    title = fm_data.get("title")
            except Exception:
                pass
            cleaned_content = content[fm_match.end():]

        # Extract title from markdown H1 if not in frontmatter
        if not title:
            h1_match = self.MARKDOWN_TITLE_PATTERN.search(cleaned_content)
            if h1_match:
                title = h1_match.group(1).strip()
            elif file_path:
                title = file_path.stem.replace("_", " ").replace("-", " ").title()
            else:
                title = "Untitled Document"

        # Calculate word count & estimated reading time
        words = re.findall(r"\b\w+\b", cleaned_content)
        word_count = len(words)
        reading_time_minutes = round(word_count / 200.0, 1)

        # Detect category
        category = self._detect_category(cleaned_content, file_path)

        # Detect chapter number if present
        chap_num = self._detect_chapter_number(cleaned_content, title)

        # Extract tags
        tags = self._extract_tags(cleaned_content, file_path, category)

        meta = DocumentMetadata(
            title=title,
            category=category,
            chapter_number=chap_num,
            word_count=word_count,
            reading_time_minutes=reading_time_minutes,
            tags=tags,
            extra=extra,
        )

        if file_path and file_path.exists():
            stat = file_path.stat()
            meta.path = str(file_path.resolve())
            meta.created_at = datetime.fromtimestamp(stat.st_ctime)
            meta.updated_at = datetime.fromtimestamp(stat.st_mtime)

        return meta

    def _detect_category(self, content: str, file_path: Path | None) -> str:
        if file_path:
            path_str = str(file_path).lower()
            for cat in ["manuscript", "characters", "lore", "outlines", "notes"]:
                if cat in path_str:
                    return cat

        lower_content = content[:2000].lower()
        for cat, keywords in self.CATEGORY_KEYWORDS.items():
            if any(kw in lower_content for kw in keywords):
                return cat
        return "general"

    def _detect_chapter_number(self, content: str, title: str) -> int | None:
        target = f"{title}\n{content[:500]}".lower()
        match = self.CHAPTER_PATTERN.search(target)
        if match:
            val = match.group(1)
            word_to_num = {
                "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
                "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10
            }
            if val in word_to_num:
                return word_to_num[val]
            if val.isdigit():
                return int(val)
        return None

    def _extract_tags(self, content: str, file_path: Path | None, category: str) -> list[str]:
        tags = {category}
        if file_path:
            for part in file_path.parts[:-1]:
                if not part.startswith("."):
                    tags.add(part.lower().replace(" ", "_"))

        lower = content[:1500].lower()
        if "prologue" in lower:
            tags.add("prologue")
        if "epilogue" in lower:
            tags.add("epilogue")
        if "scifi" in lower or "cyber" in lower or "quantum" in lower:
            tags.add("sci-fi")
        if "fantasy" in lower or "magic" in lower:
            tags.add("fantasy")

        return sorted(tags)
