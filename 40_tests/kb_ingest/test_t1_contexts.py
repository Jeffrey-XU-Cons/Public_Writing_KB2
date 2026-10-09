"""t1_contexts.py: corpus evidence for T1 definitions + the guarded write-back (P2.5, 2026-10-07)."""

import json
from pathlib import Path

import pytest

import t1_contexts as t1

ROOT = Path(__file__).resolve().parents[2]
TERMS = ROOT / "20_knowledge" / "terms" / "terms.jsonl"

GOOD_DEF = "卷烟零售终端在产品销售、形象展示、品牌培育、宣传促销、信息采集、消费跟踪等方面发挥的作用，是现代终端建设要激活和评价的内容。"


def _write(path: Path, text: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def test_iter_documents_reads_md_and_jsonl_text_and_skips_blocklist(tmp_path):
    _write(tmp_path / "a.md", "---\ntitle: 终端功能\n---\n正文提到终端功能。")
    _write(tmp_path / "secret.md", "终端功能 不外流")
    _write(tmp_path / "chunks.jsonl",
           json.dumps({"file_name": "x.docx", "text": "切块里的终端功能"}, ensure_ascii=False) + "\nnot json\n")
    _write(tmp_path / "skip.csv", "终端功能")
    docs = dict(t1.iter_documents([tmp_path], blocked_names={"secret.md"}))
    assert set(docs) == {"a.md", "chunks.jsonl:x.docx"}
    assert "title" not in docs["a.md"]  # frontmatter stripped


def test_collect_counts_hits_docs_and_prefers_definitional_cue():
    docs = [("d1", "推进终端功能建设，终端功能是指零售终端发挥的作用。"),
            ("d2", "终端功能"),
            ("d3", "与本词无关")]
    stats = t1.collect(["终端功能"], docs, per_term=5, window=4)
    s = stats["终端功能"]
    assert (s["hits"], s["docs"]) == (3, 2)
    # one candidate per document; d1's candidate is the cue occurrence, not the first one
    assert len(s["cands"]) == 2
    cue, src, text = s["cands"][0]
    assert cue and src == "d1" and "是指" in text


def test_pick_puts_cue_first_and_drops_duplicate_snippets():
    cands = [(False, "a", "同一句"), (False, "b", "同一句"), (True, "c", "定义句")]
    picked = t1.pick(cands, per_term=5)
    assert [c["src"] for c in picked] == ["c", "a"]


def test_run_with_empty_corpus_reports_zero():
    rows = t1.run(["卷烟营销"], [], per_term=1)
    assert rows == [{"term": "卷烟营销", "hits": 0, "docs": 0, "contexts": []}]


def test_run_masks_snippets(tmp_path):
    _write(tmp_path / "a.md", "河南中烟南阳卷烟厂的卷烟营销工作。")
    rows = t1.run(["卷烟营销"], [tmp_path], per_term=1, window=20)
    assert "河南中烟" not in rows[0]["contexts"][0]["text"]


@pytest.mark.parametrize("text, problem", [
    ("太短的定义。", "长度"),
    (GOOD_DEF.replace("“", '"') + '"引号"', "引号"),
    (GOOD_DEF[:-1] + "，销量增长12%。", "数字"),
    ("河南中烟" + GOOD_DEF, "单位名"),
])
def test_validate_definition_rejects(text, problem):
    assert any(problem in p for p in t1.validate_definition(text)), t1.validate_definition(text)


def test_validate_definition_accepts_clean_text_and_tool_names():
    assert t1.validate_definition(GOOD_DEF) == []
    with_tools = "推行精益管理时使用的分析和改进方法，如价值流图、目视化管理、标准作业、A3报告、5S现场管理等，用于发现浪费、分析问题和固化改进。"
    assert t1.validate_definition(with_tools) == []


def _rows():
    return [
        {"id": "T-1", "kind": "术语", "term": "老词", "t1_definition": "原有定义，一个字都不许动。"},
        {"id": "T-2", "kind": "术语", "term": "终端功能", "t1_definition": ""},
        {"id": "T-3", "kind": "术语", "term": "卷烟婚庆", "t1_definition": ""},
        {"id": "T-4", "kind": "禁用词", "term": "禁用", "rule": {}},
    ]


def test_apply_drafts_fills_only_empty_definitions_and_marks_draft():
    rows = _rows()
    filled, noted, problems = t1.apply_drafts(rows, {"终端功能": GOOD_DEF}, {"卷烟婚庆": "语料不足：截断"})
    assert (filled, noted, problems) == (1, 1, [])
    assert rows[1]["t1_definition"] == GOOD_DEF
    assert rows[1]["t1_status"] == "draft" and "未经人工审" in rows[1]["t1_source"]
    assert rows[2]["t1_definition"] == "" and rows[2]["t1_note"].startswith("语料不足")
    assert rows[0] == _rows()[0] and rows[3] == _rows()[3]


@pytest.mark.parametrize("drafts, notes, problem", [
    ({"老词": GOOD_DEF}, {}, "已有定义"),
    ({"不存在": GOOD_DEF}, {}, "没有"),
    ({"禁用": GOOD_DEF}, {}, "没有"),          # only kind=术语 rows are eligible
    ({"终端功能": "太短。"}, {}, "长度"),
    ({"终端功能": GOOD_DEF}, {"终端功能": "语料不足"}, "同时出现"),
])
def test_apply_drafts_refuses_and_changes_nothing(drafts, notes, problem):
    rows = _rows()
    filled, noted, problems = t1.apply_drafts(rows, drafts, notes)
    assert filled == noted == 0
    assert any(problem in p for p in problems), problems
    assert rows == _rows()


def test_cli_apply_writes_file_and_refuses_bad_batch(tmp_path):
    terms = _write(tmp_path / "terms.jsonl", "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in _rows()))
    good = _write(tmp_path / "d.tsv", f"终端功能\t{GOOD_DEF}\n")
    bad = _write(tmp_path / "bad.tsv", f"老词\t{GOOD_DEF}\n")
    before = terms.read_text(encoding="utf-8")
    assert t1.main(["--apply", str(bad), "--terms-file", str(terms)]) == 1
    assert terms.read_text(encoding="utf-8") == before
    assert t1.main(["--apply", str(good), "--terms-file", str(terms)]) == 0
    rows = [json.loads(line) for line in terms.read_text(encoding="utf-8").splitlines()]
    assert rows[1]["t1_definition"] == GOOD_DEF and rows[0]["t1_definition"] == "原有定义，一个字都不许动。"


def test_read_tsv_rejects_malformed_and_duplicate(tmp_path):
    with pytest.raises(ValueError):
        t1.read_tsv(_write(tmp_path / "a.tsv", "只有词没有文本\n"))
    with pytest.raises(ValueError):
        t1.read_tsv(_write(tmp_path / "b.tsv", f"词\t{GOOD_DEF}\n词\t{GOOD_DEF}\n"))


def test_real_terms_jsonl_drafts_are_marked_and_clean():
    """Regression guard on the real dictionary: every draft is labelled, valid, and never a legacy definition."""
    rows = [json.loads(line) for line in TERMS.read_text(encoding="utf-8").splitlines() if line.strip()]
    drafts = [r for r in rows if r.get("t1_status") == "draft"]
    assert drafts, "P2.5 drafts missing from terms.jsonl"
    for r in drafts:
        assert r["kind"] == "术语" and r["in_dict_before"] is False, r["term"]
        assert r["t1_source"] == t1.DRAFT_SOURCE
        assert t1.validate_definition(r["t1_definition"]) == [], r["term"]
    for r in rows:
        if "t1_note" in r:
            assert r["t1_definition"] == "" and r["t1_note"].startswith("语料不足"), r["term"]
        if r.get("in_dict_before"):
            assert "t1_status" not in r, r["term"]  # legacy definitions are not drafts
