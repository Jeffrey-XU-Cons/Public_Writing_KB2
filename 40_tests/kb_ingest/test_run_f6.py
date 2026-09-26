"""run_f6_kbrag.py 的判定逻辑（实跑要 Kb-RAG 索引，在 ThinkBook 做；这里只测判定）。"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "cases"))
from run_f6_kbrag import CASES, evaluate  # noqa: E402

CASE = {c["id"]: c for c in map(json.loads, CASES.read_text(encoding="utf-8").splitlines())}


def test_hit_in_top5_passes():
    assert evaluate(CASE["F6-01"], ["X", "QA-C3-00001"])[1] is True


def test_axiom_acceptable_for_why_question():
    assert evaluate(CASE["F6-03"], ["QA-C6-00008"])[1] is True


def test_miss_fails():
    assert evaluate(CASE["F6-01"], ["QA-C1-00001"] * 5)[1] is False


def test_hit_beyond_top5_fails():
    assert evaluate(CASE["F6-02"], ["X"] * 5 + ["QA-C5-00002"])[1] is False


def test_known_gap_reported_not_failed():
    kind, ok, note = evaluate(CASE["F6-05"], ["QA-C4-00001"])
    assert kind == "known_gap" and ok and "QA-C4-00001" in note


def test_all_eight_cases_classified():
    kinds = [evaluate(c, [])[0] for c in CASE.values()]
    assert kinds.count("expect_hit") == 4 and kinds.count("known_gap") == 4
