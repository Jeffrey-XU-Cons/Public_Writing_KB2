import json

from conftest import VALID_ANSWER
import kb_ingest
import common
import vocab

ANSWER2 = VALID_ANSWER.replace("请示", "报告")

HEAD = ("| category_l1 | 问题 | 答案 | answer_type | tags | scenarios "
        "| question_keywords | category_l2 | doc_types | source_anchor |\n")
SEP = "|---|---|---|---|---|---|---|---|---|---|\n"


def _row(i, ans, l1=1, l2="请示报告", doc="请示"):
    return (
        f"| {l1} | 问题甲{i}怎么办？ / 问题乙{i}怎么写？ / 问题丙{i}用什么？ "
        f"| {ans} | 条文型 | 请示；结语规范；上行文；文种规范；公文惯用语 "
        f"| 【主要适用场景】场景。【典型使用者】文书。【触发时机】定稿前。【注意】无。 "
        f"| 请示结尾{i}；妥否请批示；结语；上行文收尾；请示怎么收 "
        f"| {l2} | {doc} | 第{i}节 |\n"
    )


def write_batch(tmp_root, batch_id="B-20260705-01", answers=None, rows=None):
    batch = tmp_root / "batches" / batch_id
    batch.mkdir(parents=True, exist_ok=True)
    header = (
        f"---\nbatch_id: {batch_id}\n"
        f"source_path: {tmp_root / 'source' / 'source_doc.md'}\nextract_method: v7.1\n---\n\n"
    )
    if rows is None:
        answers = answers or [VALID_ANSWER, ANSWER2]
        rows = "".join(_row(i, ans) for i, ans in enumerate(answers, 1))
    (batch / "raw_output.md").write_text(header + HEAD + SEP + rows, encoding="utf-8")
    return batch


def read_lib(tmp_root):
    f = common.qa_dir() / vocab.QA_FILENAMES[1]
    return [json.loads(l) for l in f.read_text(encoding="utf-8").splitlines() if l.strip()]


def test_ingest_end_to_end(tmp_root):
    batch = write_batch(tmp_root)
    assert kb_ingest.ingest_batch(batch) == 0
    recs = read_lib(tmp_root)
    assert len(recs) == 2
    assert recs[0]["id"] == "QA-C1-00001"
    assert recs[1]["id"] == "QA-C1-00002"
    assert (batch / "check_report.md").exists()


def test_ingest_rejects_duplicate_answer(tmp_root):
    assert kb_ingest.ingest_batch(write_batch(tmp_root)) == 0
    # 第二批内容与第一批完全相同 → answer_hash 重复，整批拒收
    batch2 = write_batch(tmp_root, batch_id="B-20260705-02")
    assert kb_ingest.ingest_batch(batch2) == 1
    assert len(read_lib(tmp_root)) == 2  # 库未被污染


def test_ingest_rejects_bad_row_without_writing(tmp_root):
    batch = write_batch(tmp_root, answers=["太短的答案。"])
    assert kb_ingest.ingest_batch(batch) == 1
    assert not (common.qa_dir() / vocab.QA_FILENAMES[1]).exists()
    report = (batch / "check_report.md").read_text(encoding="utf-8")
    assert "未通过" in report


def test_ids_continue_across_batches(tmp_root):
    assert kb_ingest.ingest_batch(write_batch(tmp_root)) == 0
    batch2 = write_batch(tmp_root, batch_id="B-20260705-02",
                         answers=[VALID_ANSWER.replace("请示", "批复")])
    assert kb_ingest.ingest_batch(batch2) == 0
    assert read_lib(tmp_root)[-1]["id"] == "QA-C1-00003"


def test_batch_routes_rows_to_own_categories(tmp_root):
    """ADR-016: one batch spanning c1/c3 auto-routes each row to its file."""
    a1 = VALID_ANSWER
    a3 = "方法：结构化写作有结论先行、以上统下、归类分组、逻辑递进四原则。" + "结构化写作要点展开说明。" * 45
    rows = (
        _row(1, a1, l1=1, l2="请示报告", doc="请示")
        + f"| 3 | 怎么把材料写清楚？ / 结构化写作怎么搭框架？ / 结构化写作最容易犯什么错误？ "
          f"| {a3} | 方法型 | 结构化写作；结论先行；归类分组；主体展开；结构与逻辑 "
          f"| 【主要适用场景】起草长材料。【典型使用者】笔杆子。【触发时机】搭框架时。【注意】先想后写。 "
          f"| 材料没条理；结构化写作；怎么搭框架；逻辑不清；金字塔结构 "
          f"| 主体展开 | 通用 | 基础篇 |\n"
    )
    batch = write_batch(tmp_root, batch_id="B-20260706-09", rows=rows)
    assert kb_ingest.ingest_batch(batch) == 0
    c1 = common.qa_dir() / vocab.QA_FILENAMES[1]
    c3 = common.qa_dir() / vocab.QA_FILENAMES[3]
    assert c1.exists() and c3.exists()
    r3 = [json.loads(l) for l in c3.read_text(encoding="utf-8").splitlines() if l.strip()]
    assert r3[0]["id"] == "QA-C3-00001" and r3[0]["category_l1"] == 3


def test_answer_over_ceiling_rejected(tmp_root):
    huge = "很长的方法型答案。" * 260  # > 2000 chars
    batch = write_batch(tmp_root, batch_id="B-20260706-10",
                        rows=_row(1, huge).replace("| 条文型 |", "| 方法型 |"))
    assert kb_ingest.ingest_batch(batch) == 1
    assert not (common.qa_dir() / vocab.QA_FILENAMES[1]).exists()


# ---- 15 列表：逐行 source_path + depth/enforce/w_layer/挂钩（P5，2026-09-29） ----

import pytest  # noqa: E402

HEAD15 = HEAD.rstrip("\n") + " source_path | depth | enforce | w_layer | 挂钩 |\n"
SEP15 = "|---" * 15 + "|\n"


def _row15(i, ans, extra):
    return _row(i, ans).rstrip("\n") + " " + " | ".join(extra) + " |\n"


def write_batch15(tmp_root, rows, header_source=True, head=HEAD15):
    batch = tmp_root / "batches" / "B-20260929-01"
    batch.mkdir(parents=True, exist_ok=True)
    src = f"source_path: {tmp_root / 'source' / 'source_doc.md'}\n" if header_source else ""
    header = f"---\nbatch_id: B-20260929-01\n{src}extract_method: v7.1\n---\n\n"
    (batch / "raw_output.md").write_text(header + head + SEP15 + rows, encoding="utf-8")
    return batch


def test_15col_row_source_path_overrides_header(tmp_root):
    other = tmp_root / "source" / "汇编四.md"
    other.write_text("另一分册", encoding="utf-8")
    rows = (_row15(1, VALID_ANSWER, [str(other), "", "", "", ""])
            + _row15(2, ANSWER2, ["", "", "", "", ""]))
    assert kb_ingest.ingest_batch(write_batch15(tmp_root, rows)) == 0
    recs = read_lib(tmp_root)
    assert recs[0]["source_path"] == str(other)
    assert recs[1]["source_path"] == str(tmp_root / "source" / "source_doc.md")
    assert "depth" not in recs[1]  # 空格子 = 不打标，与老记录一致


def test_15col_without_header_source_path_needs_every_row(tmp_root):
    src = str(tmp_root / "source" / "source_doc.md")
    rows = (_row15(1, VALID_ANSWER, [src, "", "", "", ""])
            + _row15(2, ANSWER2, ["", "", "", "", ""]))
    with pytest.raises(ValueError, match="source_path"):
        kb_ingest.ingest_batch(write_batch15(tmp_root, rows, header_source=False))


def test_15col_layer_fields_routed_by_depth(tmp_root):
    rows = (_row15(1, VALID_ANSWER, ["", "method", "soft", "W1；W2", "QA-C6-00008；QA-C6-00009"])
            + _row15(2, ANSWER2, ["", "axiom", "hard", "W2", "C1；3"]))
    assert kb_ingest.ingest_batch(write_batch15(tmp_root, rows)) == 0
    a, b = read_lib(tmp_root)
    assert (a["depth"], a["enforce"], a["w_layer"]) == ("method", "soft", ["W1", "W2"])
    assert a["derives_from"] == ["QA-C6-00008", "QA-C6-00009"]
    assert b["governs"] == [1, 3] and "derives_from" not in b


def test_15col_method_without_link_rejected_by_validator(tmp_root):
    rows = _row15(1, VALID_ANSWER, ["", "method", "soft", "W2", ""])
    batch = write_batch15(tmp_root, rows)
    assert kb_ingest.ingest_batch(batch) == 1
    assert "derives_from" in (batch / "check_report.md").read_text(encoding="utf-8")


def test_15col_link_without_depth_rejected(tmp_root):
    rows = _row15(1, VALID_ANSWER, ["", "", "", "", "QA-C6-00008"])
    with pytest.raises(ValueError, match="挂钩"):
        kb_ingest.ingest_batch(write_batch15(tmp_root, rows))


def test_15col_misordered_header_rejected(tmp_root):
    bad_head = HEAD.rstrip("\n") + " depth | source_path | enforce | w_layer | 挂钩 |\n"
    rows = _row15(1, VALID_ANSWER, ["", "", "", "", ""])
    with pytest.raises(ValueError, match="表头"):
        kb_ingest.ingest_batch(write_batch15(tmp_root, rows, head=bad_head))


def test_10col_header_without_source_path_rejected(tmp_root):
    batch = write_batch(tmp_root)
    raw = batch / "raw_output.md"
    raw.write_text("\n".join(l for l in raw.read_text(encoding="utf-8").splitlines()
                             if not l.startswith("source_path:")) + "\n", encoding="utf-8")
    with pytest.raises(ValueError, match="source_path"):
        kb_ingest.ingest_batch(batch)
