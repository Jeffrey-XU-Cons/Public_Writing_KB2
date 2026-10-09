"""真实成稿基线（82 份脱敏个人历史交付物）：draft_lint 的 block 结果逐份比对快照。
2026-09-25 去 jieba 重构时出过回归，单元测试没拦住，靠手工复跑才发现，故加此基线。
规则有意改进导致结果变化时，重新生成快照（见 40_tests/golden/README）。"""

import json
from pathlib import Path

import pytest

import draft_lint as dl

ROOT = Path(__file__).resolve().parents[2]
SNAP = ROOT / "40_tests/golden/draft_lint_real_docs.json"
BATCH = ROOT / "30_engine/batches/B-20261007-deid-个人历史交付物-r11"


@pytest.mark.skipif(not BATCH.exists(), reason="脱敏批次不在本机")
def test_real_docs_block_results_unchanged():
    snap = json.loads(SNAP.read_text(encoding="utf-8"))
    rules = dl.load_rules(ROOT)
    diffs = []
    for name, want in snap.items():
        res = dl.lint((BATCH / name).read_text(encoding="utf-8"), rules=rules)
        got = sorted(f"{r['gate']}|{r['rule']}" for r in res if r["severity"] == "block")
        if got != want:
            diffs.append(f"{name[:30]}: 快照{want} → 现在{got}")
    assert not diffs, "\n".join(diffs[:10])
