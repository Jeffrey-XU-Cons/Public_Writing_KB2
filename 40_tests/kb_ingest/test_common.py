"""Regression: without KBRAG_ROOT the tools must find the real project root.

History: project_root() once returned 30_engine/ (one level short), so
qa_dir() pointed at an empty dir — kb_validate passed on nothing, kb_ingest
restarted ids at 00001, and draft_lint loaded zero dictionary rules, all silently.
"""

from pathlib import Path

import common

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def test_project_root_without_env(monkeypatch):
    monkeypatch.delenv("KBRAG_ROOT", raising=False)
    assert common.project_root() == PROJECT_ROOT


def test_qa_dir_points_at_real_library(monkeypatch):
    monkeypatch.delenv("KBRAG_ROOT", raising=False)
    assert common.qa_dir() == PROJECT_ROOT / "20_knowledge" / "qa"
    assert list(common.qa_dir().glob("c[1-6]_*.jsonl")), "QA 真源目录下应有 c{n}_*.jsonl"


def test_env_override_still_wins(monkeypatch, tmp_path):
    monkeypatch.setenv("KBRAG_ROOT", str(tmp_path))
    assert common.project_root() == tmp_path
