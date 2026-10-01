"""kb_dedup_vec：判定逻辑用假编码器测；真模型用例要 Kb-RAG 的 venv（ThinkBook），否则跳过。"""

import importlib.util
from pathlib import Path

import pytest

import kb_dedup_vec as dv

KBRAG = Path(__file__).resolve().parents[3] / "Kb-RAG"


def rec(qid, answer, question="问法一 / 问法二"):
    return {"id": qid, "question": question, "answer": answer, "status": "active"}


# 假编码器：按答案里的关键字给向量，方向相同 = 相似度 1
FAKE = {"甲": [1.0, 0.0, 0.0], "乙": [0.0, 1.0, 0.0], "甲乙": [1.0, 1.0, 0.0]}


def fake_encode(texts):
    return [FAKE[t] for t in texts]


RECORDS = [rec("QA-C1-00001", "甲"), rec("QA-C1-00002", "甲"),
           rec("QA-C2-00001", "乙"), rec("QA-C3-00001", "甲乙")]


def test_self_similarity_is_one():
    assert dv.cosine([0.3, 0.4], [0.3, 0.4]) == pytest.approx(1.0)


def test_over_threshold_and_top():
    result = dv.analyze(RECORDS, fake_encode, threshold=0.92, top=2)
    over = [(r["a"], r["b"]) for r in result["over_threshold"]]
    assert over == [("QA-C1-00001", "QA-C1-00002")]
    assert len(result["top"]) == 2 and result["top"][0]["score"] == pytest.approx(1.0)
    assert result["over_threshold"][0]["q_a"] == "问法一"


def test_pairs_returns_requested_scores():
    wanted = dv.parse_pairs(["QA-C1-00001,QA-C2-00001", "QA-C1-00001,QA-X-99999"])
    result = dv.analyze(RECORDS, fake_encode, wanted=wanted)
    assert [(r["a"], r["b"]) for r in result["pairs"]] == wanted
    assert result["pairs"][0]["score"] == pytest.approx(0.0)
    assert result["pairs"][1]["score"] is None


def test_inactive_records_skipped(tmp_path):
    (tmp_path / "c1_x.jsonl").write_text(
        '{"id": "QA-C1-00001", "question": "q", "answer": "甲", "status": "active"}\n'
        '{"id": "QA-C1-00002", "question": "q", "answer": "甲", "status": "deprecated"}\n',
        encoding="utf-8")
    assert [r["id"] for r in dv.load_records(tmp_path)] == ["QA-C1-00001"]


@pytest.mark.skipif(importlib.util.find_spec("sentence_transformers") is None or not KBRAG.is_dir(),
                    reason="需 Kb-RAG 的 venv 解释器与 Kb-RAG 目录")
def test_real_model_unrelated_pair_below_threshold():
    records = [r for r in dv.load_records() if r["id"] in ("QA-C2-00004", "QA-C6-00016")]
    assert len(records) == 2
    result = dv.analyze(records, dv.model_encoder(KBRAG),
                        wanted=[("QA-C2-00004", "QA-C2-00004"), ("QA-C2-00004", "QA-C6-00016")])
    same, unrelated = result["pairs"]
    assert same["score"] == pytest.approx(1.0, abs=1e-3)
    assert unrelated["score"] < 0.92
