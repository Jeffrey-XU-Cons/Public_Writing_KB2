# 一次性数据迁移，2026-10-07 执行（B-20261007-01 C2 格式规范 9 条独立核查后的修正），留档备查。
# 可重跑：已改过的不再动。核查记录见 30_engine/batches/B-20261007-C2-01/核查记录.md
#   QA-C2-00012：发文字号“由机关代字、年份、顺序号组成”“联合行文使用主办机关的发文字号”
#               出自《党政机关公文处理工作条例》第九条，不在 GB/T 9704 7.2 → 依据补条例
#   QA-C2-00014：纪要格式漏了 GB/T 9704 10.3 末句“纪要格式可以根据实际制定”，
#               不补会让人把纪要版式当成刚性规定 → 补上（legacy json 未收此句，须对照标准原文复核）
# 同时把同样的替换施加到批次 raw_output.md，保持批次留档与库内一致。
# -*- coding: utf-8 -*-
import json
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import common  # noqa: E402
from kb_validate import answer_hash, validate_record  # noqa: E402

TODAY = date.today().isoformat()
BATCH_RAW = Path(__file__).resolve().parents[2] / "batches" / "B-20261007-C2-01" / "raw_output.md"

# (id, 字段, 旧文本, 新文本)
REPLACEMENTS = [
    ("QA-C2-00012", "answer",
     "依据：《党政机关公文格式》（GB/T 9704—2012）7.2；legacy 规则 FC-004、FC-005。",
     "依据：组成与联合行文——《党政机关公文处理工作条例》第九条；标注格式——《党政机关公文格式》（GB/T 9704—2012）7.2；legacy 规则 FC-004、FC-005。"),
    ("QA-C2-00014", "answer",
     "并将“出席”二字改为“请假”或“列席”。\n依据：",
     "并将“出席”二字改为“请假”或“列席”。纪要格式可以根据实际制定。\n依据："),
    ("QA-C2-00014", "scenarios",
     "【注意】纪要的写法（议定事项、主语用法）属文种规范，不在本条",
     "【注意】标准允许纪要格式根据实际制定，单位另有纪要模板的从其规定；纪要的写法（议定事项、主语用法）属文种规范，不在本条"),
]


def main():
    files = {f: [json.loads(l) for l in f.read_text(encoding="utf-8").splitlines() if l.strip()]
             for f in sorted(common.qa_dir().glob("c[1-6]_*.jsonl"))}
    recs = {r["id"]: r for rs in files.values() for r in rs}
    done = []
    for rid, field, old, new in REPLACEMENTS:
        rec = recs[rid]
        if old in rec[field]:
            rec[field] = rec[field].replace(old, new, 1)
            rec["updated"] = TODAY
            done.append(f"{rid}.{field}")
    errors = []
    for rid in {d.split(".")[0] for d in done}:
        recs[rid]["answer_hash"] = answer_hash(recs[rid]["answer"])
        errors += [f"{rid}: {e}" for e in validate_record(recs[rid])]
    if errors:
        raise SystemExit("校验未过，终止且未写任何文件：\n" + "\n".join(errors))
    changed_ids = {d.split(".")[0] for d in done}
    for f, rs in files.items():
        if not any(r["id"] in changed_ids for r in rs):
            continue  # only rewrite files that actually changed
        tmp = f.with_suffix(".jsonl.tmp")
        tmp.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in rs) + "\n", encoding="utf-8")
        tmp.replace(f)
    # batch record: raw_output.md stores answers with <br> for newlines
    if BATCH_RAW.exists():
        raw = BATCH_RAW.read_text(encoding="utf-8")
        for _rid, _field, old, new in REPLACEMENTS:
            old_md, new_md = old.replace("\n", "<br>"), new.replace("\n", "<br>")
            if old_md in raw:
                raw = raw.replace(old_md, new_md, 1)
                done.append(f"raw_output.md: {old_md[:20]}…")
        BATCH_RAW.write_text(raw, encoding="utf-8")
    print("\n".join(done) or "无变化（已改过）")


if __name__ == "__main__":
    common.force_utf8_stdout()
    main()
