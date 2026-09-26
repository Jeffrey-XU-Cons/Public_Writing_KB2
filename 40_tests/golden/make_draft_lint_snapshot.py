"""重新生成 draft_lint 真实成稿基线快照。规则有意改进、逐条确认变化后才跑。
用法：KBRAG_ROOT=$PWD python3 40_tests/golden/make_draft_lint_snapshot.py"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "30_engine/tools"))
import draft_lint as dl  # noqa: E402

BATCH = ROOT / "30_engine/batches/B-20260925-deid-个人历史交付物-r7"
rules = dl.load_rules(ROOT)
snap = {}
for f in sorted(BATCH.glob("*.md")):
    if f.name.startswith(("复核报告", "首批")):
        continue
    res = dl.lint(f.read_text(encoding="utf-8"), rules=rules)
    snap[f.name] = sorted(f"{r['gate']}|{r['rule']}" for r in res if r["severity"] == "block")
(ROOT / "40_tests/golden/draft_lint_real_docs.json").write_text(json.dumps(snap, ensure_ascii=False, indent=1), encoding="utf-8")
print(f"{len(snap)} 份；block 合计 {sum(map(len, snap.values()))}；0 block {sum(1 for v in snap.values() if not v)} 份")
