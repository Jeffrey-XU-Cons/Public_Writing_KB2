"""F6 单点问答 8 条：经 Kb-RAG search.py 实跑验收（11章 P3.7/P3.8）。纯标准库。
在 ThinkBook 上：py 40_tests\\cases\\run_f6_kbrag.py [Kb-RAG 目录]（默认 ../Kb-RAG）

判定：有 acceptable_hits 的用例，Top5 命中其一 = 通过；"确认未命中"类用例是已知缺口，
只报告 Top1 是什么（看是不是在瞎凑），不算失败。退出码：通过类用例全过=0，否则 1。"""

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CASES = ROOT / "40_tests/cases/scenarios/batch1_F6单点问答.jsonl"
KB = "public_writing_qa"


def evaluate(case, result_ids):
    """返回 (类别, 是否通过, 说明)。类别：expect_hit / known_gap"""
    acc = case.get("acceptable_hits")
    if acc:
        rank = next((i for i, x in enumerate(result_ids[:5], 1) if x in acc), None)
        return "expect_hit", rank is not None, f"Top5 第{rank}位命中" if rank else f"未命中；Top5={result_ids[:5]}"
    top1 = result_ids[0] if result_ids else "无结果"
    return "known_gap", True, f"已知缺口；Top1={top1}（人工看一眼是否在硬凑）"


def search(kbrag, query):
    cmd = [sys.executable, str(kbrag / "tools/search.py"), "--q", query, "--kb", KB, "--top", "5", "--json"]
    out = subprocess.run(cmd, cwd=kbrag, capture_output=True, text=True, encoding="utf-8", timeout=300)
    if out.returncode != 0:
        raise RuntimeError(out.stderr[-500:])
    return [r["id"] for r in json.loads(out.stdout)["results"]]


def main(argv):
    kbrag = Path(argv[0]) if argv else ROOT.parent / "Kb-RAG"
    cases = [json.loads(l) for l in CASES.read_text(encoding="utf-8").splitlines() if l.strip()]
    failed = 0
    for c in cases:
        kind, ok, note = evaluate(c, search(kbrag, c["query"]))
        failed += (kind == "expect_hit" and not ok)
        print(f"{c['id']} [{'通过' if ok else '失败'}] {c['question_type']}｜{c['query'][:24]}｜{note}")
    print(f"应命中类失败 {failed} 条" + ("" if failed else "——F6 验收通过"))
    return 1 if failed else 0


if __name__ == "__main__":
    for s in (sys.stdout, sys.stderr):
        if hasattr(s, "reconfigure"):
            s.reconfigure(encoding="utf-8")
    sys.exit(main(sys.argv[1:]))
