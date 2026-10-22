"""Runbook and operational procedure management for Author-MCP.

Brought over from Hath0r Enterprise Knowledgebase architecture.
Provides procedural runbooks for manuscript ingestion, lore consistency checks,
and knowledge synchronization.
"""

from __future__ import annotations

from typing import Any
from pydantic import BaseModel, Field


class Runbook(BaseModel):
    name: str
    title: str
    description: str
    safety_level: str = "safe"
    steps: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)


DEFAULT_AUTHOR_RUNBOOKS = [
    Runbook(
        name="ingest-manuscript",
        title="Ingest New Manuscript or Chapter",
        description="Standard operating procedure for adding a new book chapter or story draft.",
        steps=[
            "Place markdown file under Books/manuscripts/ with '# Chapter N: Title' header.",
            "Run 'author-mcp index' to execute the indexing pipeline.",
            "Execute 'author-mcp search <keywords>' to verify BM25 indexing.",
            "Run 'author-mcp sync-knowledge' to export single source of truth.",
        ],
        tags=["manuscript", "ingestion", "author"],
    ),
    Runbook(
        name="lore-consistency-check",
        title="Lore & Worldbuilding Consistency Verification",
        description="Cross-reference character and setting lore against draft chapters.",
        steps=[
            "Query 'lore' index via search_author_knowledge for target faction or magic rules.",
            "Query 'characters' index for character relationships and voice profiles.",
            "Verify manuscript chapter adheres to canonical facts without contradictions.",
        ],
        tags=["lore", "editorial", "qa"],
    ),
    Runbook(
        name="atc-suite-health",
        title="Air Traffic Control Suite Health Audit",
        description="Verify container orchestration and member repo compliance.",
        steps=[
            "Run 'author-mcp atc' to verify suite topology and container state.",
            "Check that Books repository has NO website/site directory.",
            "Verify Redis session cache and healthcheck endpoints respond 200 OK.",
        ],
        tags=["atc", "operations", "health"],
    ),
]


class RunbookService:
    """Manages Author operational runbooks."""

    def __init__(self) -> None:
        self.runbooks: dict[str, Runbook] = {r.name: r for r in DEFAULT_AUTHOR_RUNBOOKS}

    def list_runbooks(self) -> list[Runbook]:
        return list(self.runbooks.values())

    def get_runbook(self, name: str) -> Runbook | None:
        return self.runbooks.get(name)

    def search_runbooks(self, query: str) -> list[Runbook]:
        q = query.lower()
        results = []
        for r in self.runbooks.values():
            if q in r.name.lower() or q in r.title.lower() or q in r.description.lower() or any(q in t.lower() for t in r.tags):
                results.append(r)
        return results
