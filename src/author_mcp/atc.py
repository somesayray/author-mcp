"""Air Traffic Control (ATC) Subsystem for the Author Suite."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path
from typing import Any

import structlog

from author_mcp.config import settings

logger = structlog.get_logger(__name__)


class AuthorATC:
    """Air Traffic Control (ATC) controller and tower for Author suite.

    Manages suite topology, service discovery, container observation,
    and agent task traffic between Books and MCP components.
    """

    def __init__(self, author_root: Path | None = None) -> None:
        self.author_root = author_root or settings.BOOKS_DIR.parent
        self.mcp_dir = self.author_root / "mcp"
        self.books_dir = settings.BOOKS_DIR

    def get_inventory(self) -> dict[str, Any]:
        """Return suite inventory of member repositories and their roles."""
        return {
            "suite": settings.SUITE_NAME,
            "atc_role": settings.ATC_ROLE,
            "root_path": str(self.author_root),
            "members": [
                {
                    "name": "mcp",
                    "repo": "author-mcp",
                    "role": "Root MCP Server & Suite ATC Control Tower",
                    "path": str(self.mcp_dir),
                    "exists": self.mcp_dir.exists(),
                    "has_hathor": (self.mcp_dir / ".hath0r").exists(),
                    "ports": {"http": settings.PORT},
                },
                {
                    "name": "Books",
                    "repo": "Books",
                    "role": "Text Documents & Manuscript Repository (No Site)",
                    "path": str(self.books_dir),
                    "exists": self.books_dir.exists(),
                    "has_hathor": (self.books_dir / ".hath0r").exists(),
                    "site_enabled": False,
                },
            ],
            "containers": [
                {
                    "name": "Author-MCP",
                    "service": "author-mcp",
                    "role": "Root Model Context Protocol server",
                },
                {
                    "name": "Author-Sessions",
                    "service": "author-sessions",
                    "role": "Shared session and task memory",
                },
            ],
            "network": "author-net",
        }

    def get_git_info(self, repo_dir: Path) -> dict[str, Any]:
        """Extract quick git information for a member repo."""
        if not repo_dir.exists() or not (repo_dir / ".git").exists():
            return {"status": "not_git_repo"}
        try:
            branch = subprocess.check_output(
                ["git", "-C", str(repo_dir), "rev-parse", "--abbrev-ref", "HEAD"],
                text=True,
                stderr=subprocess.DEVNULL,
            ).strip()
            commit = subprocess.check_output(
                ["git", "-C", str(repo_dir), "rev-parse", "--short", "HEAD"],
                text=True,
                stderr=subprocess.DEVNULL,
            ).strip()
            return {"branch": branch, "commit": commit}
        except Exception:
            return {"status": "git_query_failed"}

    def get_docker_status(self) -> list[dict[str, Any]]:
        """Query Docker daemon status for author suite containers."""
        try:
            res = subprocess.check_output(
                ["docker", "ps", "--filter", "name=Author-", "--format", "{{.Names}}\t{{.Status}}\t{{.Ports}}"],
                text=True,
                stderr=subprocess.DEVNULL,
            ).strip()
            containers = []
            if res:
                for line in res.split("\n"):
                    parts = line.split("\t")
                    containers.append({
                        "name": parts[0] if len(parts) > 0 else "unknown",
                        "status": parts[1] if len(parts) > 1 else "unknown",
                        "ports": parts[2] if len(parts) > 2 else "",
                    })
            return containers
        except Exception:
            return []

    def get_atc_status(self) -> dict[str, Any]:
        """Aggregate full ATC control tower status."""
        inv = self.get_inventory()
        mcp_git = self.get_git_info(self.mcp_dir)
        books_git = self.get_git_info(self.books_dir)
        containers = self.get_docker_status()

        return {
            "status": "operational",
            "suite": settings.SUITE_NAME,
            "atc_role": settings.ATC_ROLE,
            "control_tower": {
                "server": "Author-MCP",
                "network": "author-net",
                "root_mcp": True,
            },
            "members": {
                "mcp": {
                    "git": mcp_git,
                    "hathor_aligned": (self.mcp_dir / ".hath0r").exists(),
                    "agents_md": (self.mcp_dir / "AGENTS.md").exists(),
                },
                "books": {
                    "git": books_git,
                    "hathor_aligned": (self.books_dir / ".hath0r").exists(),
                    "agents_md": (self.books_dir / "AGENTS.md").exists(),
                    "site_free": not (self.books_dir / "site").exists(),
                },
            },
            "running_containers": containers,
        }
