"""Baseline Local Quality Gate smoke test scaffolded by Hath0r CLI."""

from pathlib import Path


def test_thresholds_json_present() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    assert (repo_root / "thresholds.json").is_file()
