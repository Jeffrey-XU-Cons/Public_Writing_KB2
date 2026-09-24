"""Shared fixtures: a throwaway project root + a valid record factory."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "30_engine" / "tools"))

import kb_validate  # noqa: E402


@pytest.fixture()
def tmp_root(tmp_path, monkeypatch):
    """Point all tools at a temporary project root via KBRAG_ROOT."""
    (tmp_path / "knowledge" / "qa").mkdir(parents=True)
    (tmp_path / "batches").mkdir()
    (tmp_path / ".claude" / "skills").mkdir(parents=True)
    (tmp_path / "source").mkdir()
    source = tmp_path / "source" / "source_doc.md"
    source.write_text("测试素材原文", encoding="utf-8")
    monkeypatch.setenv("KBRAG_ROOT", str(tmp_path))
    return tmp_path


VALID_ANSWER = (
    "条文：请示的结语应当使用规范用语，常见的三种写法为「妥否，请批示」"
    "「以上请示当否，请批复」「特此请示，请予审批」。出处：党政机关公文处理工作条例及"
    "各级机关行文惯例。正误对照：正——「妥否，请批示」；误——「请领导批准」（口语化、"
    "对象含混）。易错点：一是把请示结语写成报告结语「特此报告」；二是结语后再附加"
    "客套语造成画蛇添足；三是一文多事时结语无法对应单一请求事项，违背一文一事原则。"
)


def make_record(tmp_root, **overrides):
    rec = {
        "id": "QA-C1-00001",
        "question": "请示的结尾怎么写才规范？ / 请示结语有哪几种标准写法？ / 给上级的请示最后一句话用什么？",
        "answer": VALID_ANSWER,
        "answer_type": "条文型",
        "tags": ["请示", "结语规范", "上行文", "文种规范", "公文惯用语"],
        "scenarios": "【主要适用场景】①向上级机关请示资金；②请示政策事项。"
                     "【典型使用者】办公室文书人员、部门负责人。"
                     "【触发时机】起草请示定稿前检查结语。"
                     "【注意】不适用于报告类文种，报告不得夹带请示事项。",
        "question_keywords": ["请示结尾", "妥否请批示", "请示结语", "上行文收尾", "请示怎么收"],
        "category_l1": 1,
        "category_l2": "请示报告",
        "doc_types": ["请示"],
        "source_path": str(tmp_root / "source" / "source_doc.md"),
        "source_anchor": "第1节",
        "extract_method": "v7.1",
        "quality_grade": "B",
        "quality_checked": False,
        "batch_id": "B-20260705-01",
        "status": "active",
        "created": "2026-07-05",
        "updated": "2026-07-05",
        "answer_hash": kb_validate.answer_hash(VALID_ANSWER),
    }
    rec.update(overrides)
    if "answer" in overrides and "answer_hash" not in overrides:
        rec["answer_hash"] = kb_validate.answer_hash(rec["answer"])
    return rec
