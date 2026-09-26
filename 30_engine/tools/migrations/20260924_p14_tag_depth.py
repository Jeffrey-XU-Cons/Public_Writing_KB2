# 一次性数据迁移，已于 2026-09-24 执行完毕，留档备查。勿重跑：会重复写入。
# -*- coding: utf-8 -*-
"""P1.4: 现有 34 条补打 depth/enforce/w_layer，挂 derives_from。
判断依据：answer_type -> depth 机械映射（条文型->rule 方法型->method 拆解型->principle，
个别拆解型内容实为具体可复述框架的改判 method，见随附报告说明）；
enforce 统一 soft（这 34 条都需要语义判断，没有纯格式类可机检内容）；
w_layer 按内容主要使用阶段判一层（首轮判断，后续按实际检索命中调整）；
derives_from 挂到内容上最贴近的一条 A1-A6 公理（QA-C6-00007~00012）或已判定的 principle。
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, "/home/febin/projects/Public_Writing_KB/30_engine/tools")
import kb_validate  # noqa: E402

QA_DIR = Path("/home/febin/projects/Public_Writing_KB/20_knowledge/qa")

A1, A2, A3, A4, A5, A6 = (
    "QA-C6-00007", "QA-C6-00008", "QA-C6-00009",
    "QA-C6-00010", "QA-C6-00011", "QA-C6-00012",
)

# id -> (depth, w_layer(list), derives_from(list or None for rule))
PATCH = {
    "QA-C1-00001": ("rule", ["W1"], None),
    "QA-C1-00002": ("rule", ["W1"], None),
    "QA-C1-00003": ("rule", ["W1"], None),
    "QA-C1-00004": ("rule", ["W1"], None),  # 方法型但内容是文种要件层面的做法，仍按 C1 骨架惯例走 rule
    "QA-C1-00005": ("rule", ["W1"], None),
    "QA-C1-00006": ("rule", ["W1"], None),

    "QA-C3-00001": ("method", ["W2"], ["QA-C6-00001"]),
    "QA-C3-00002": ("method", ["W2"], [A3]),
    "QA-C3-00003": ("method", ["W2"], [A5]),
    "QA-C3-00004": ("method", ["W2"], [A5]),
    "QA-C3-00005": ("method", ["W4"], [A2]),
    "QA-C3-00006": ("method", ["W2"], [A2]),
    "QA-C3-00007": ("method", ["W2"], [A5]),
    "QA-C3-00008": ("method", ["W2"], [A5]),
    "QA-C3-00009": ("method", ["W3"], [A5]),
    "QA-C3-00010": ("method", ["W2"], [A3]),
    "QA-C3-00011": ("method", ["W3"], [A4]),
    "QA-C3-00012": ("method", ["W3"], [A4]),
    "QA-C3-00013": ("method", ["W2"], [A6]),
    "QA-C3-00014": ("method", ["W3"], [A4]),
    "QA-C3-00015": ("method", ["W4"], [A2]),

    "QA-C4-00001": ("method", ["W4"], [A2]),

    "QA-C5-00001": ("method", ["W3"], [A4]),
    "QA-C5-00002": ("method", ["W3"], [A4]),
    "QA-C5-00003": ("method", ["W2"], [A1]),
    "QA-C5-00004": ("method", ["W2"], [A6]),
    "QA-C5-00005": ("method", ["W1"], [A6]),
    "QA-C5-00006": ("method", ["W5"], [A6]),

    "QA-C6-00001": ("principle", ["W2"], [A2]),
    "QA-C6-00002": ("principle", ["W2"], [A3]),
    "QA-C6-00003": ("method", ["W1"], [A1]),
    "QA-C6-00004": ("principle", ["W1"], [A1]),
    "QA-C6-00005": ("principle", ["W1"], [A1]),
    "QA-C6-00006": ("method", ["W1"], [A1]),
}

changed = 0
for f in sorted(QA_DIR.glob("c[1-6]_*.jsonl")):
    lines = f.read_text(encoding="utf-8").splitlines()
    out_lines = []
    for line in lines:
        if not line.strip():
            continue
        rec = json.loads(line)
        if rec["id"] in PATCH:
            depth, w_layer, derives = PATCH[rec["id"]]
            rec["depth"] = depth
            rec["enforce"] = "soft"
            rec["w_layer"] = w_layer
            if derives is not None:
                rec["derives_from"] = derives
            changed += 1
        out_lines.append(json.dumps(rec, ensure_ascii=False))
    f.write_text("\n".join(out_lines) + "\n", encoding="utf-8")

print("patched", changed, "records (expect 34)")

# sanity: every PATCH id must have been found
found_ids = set()
for f in sorted(QA_DIR.glob("c[1-6]_*.jsonl")):
    for line in f.read_text(encoding="utf-8").splitlines():
        if line.strip():
            found_ids.add(json.loads(line)["id"])
missing = set(PATCH) - found_ids
print("missing ids (should be empty):", missing)
