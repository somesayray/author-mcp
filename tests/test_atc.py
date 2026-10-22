"""Unit tests for AuthorATC controller."""

from pathlib import Path
from author_mcp.atc import AuthorATC


def test_atc_inventory(tmp_path: Path):
    suite_dir = tmp_path / "Author"
    mcp_dir = suite_dir / "mcp"
    books_dir = suite_dir / "Books"
    mcp_dir.mkdir(parents=True)
    books_dir.mkdir(parents=True)

    atc = AuthorATC(author_root=suite_dir)
    inv = atc.get_inventory()

    assert inv["suite"] == "Author"
    assert len(inv["members"]) == 2
    assert any(m["name"] == "mcp" for m in inv["members"])
    assert any(m["name"] == "Books" for m in inv["members"])
    books_member = next(m for m in inv["members"] if m["name"] == "Books")
    assert books_member["site_enabled"] is False
