# -*- coding: utf-8 -*-
"""P2.1: official_terms_v2.yaml (9179字塞进一个 content 字段) 解构成机检可读 JSONL。
范围：PW(禁用词)/MM(搭配)/CP(套话) 三类，11章 P2.1 明确要求的范围。
COU(常用语建议)、TT(行业术语)不在本次范围内，太长的解释见随附报告。
"""
import json
import re
import sys
import yaml

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import common
SRC = common.project_root() / "20_knowledge/terms/legacy/official_terms_v2.yaml"

with open(SRC, encoding="utf-8") as f:
    data = yaml.safe_load(f)
text = data["content"]
lines = text.splitlines()


def section_slice(lines, start_marker, end_marker):
    start = next(i for i, l in enumerate(lines) if start_marker in l)
    end = next(i for i, l in enumerate(lines) if end_marker in l and i > start)
    return lines[start:end]


out = []

# ---------- PW 禁用词 ----------
pw_lines = section_slice(lines, "第二部分：禁用词表与风险词", "第三部分：高频易错搭配")
subgroup = None
group_code = None
n = 0
for line in pw_lines:
    s = line.strip()
    m = re.match(r"^###\s*(PW-\d+)\s+(\S+)", s)
    if m:
        group_code, subgroup = m.group(1), m.group(2)
        n = 0
        continue
    m = re.match(r"^\*\*(.+?)\*\*", s)
    if m and "：" in s or (m and s.endswith("：")):
        subgroup_detail = m.group(1)
        continue
    m = re.match(r"^-\s*(⚠️|❌)\s*(.+?)\s*→\s*(?:✅\s*)?(.+)$", s)
    if m and group_code:
        n += 1
        mark, banned, repl = m.groups()
        if mark == "❌":
            # 真禁用：repl 是替换词
            replace_with = [r.strip() for r in re.split(r"[/／]", repl) if r.strip()]
            out.append({
                "id": f"{group_code}-{n:02d}",
                "category": "禁用词",
                "subgroup": subgroup,
                "banned": banned.strip(),
                "replace_with": replace_with,
                "severity": "禁止",
                "enforce": "hard",
            })
        else:
            # ⚠️ 谨慎：repl 是使用条件说明，不是替换词，字段和 enforce 都要分开处理
            out.append({
                "id": f"{group_code}-{n:02d}",
                "category": "禁用词",
                "subgroup": subgroup,
                "banned": banned.strip(),
                "replace_with": [],
                "condition": repl.strip(),
                "severity": "谨慎",
                "enforce": "soft",
            })

# ---------- MM 搭配 ----------
mm_lines = section_slice(lines, "第三部分：高频易错搭配", "第四部分：高频套话替换表")
group_code, subgroup = None, None
n = 0
in_table = False
for line in mm_lines:
    s = line.strip()
    m = re.match(r"^###\s*(MM-\d+)\s+(\S+)", s)
    if m:
        group_code, subgroup = m.group(1), m.group(2)
        n = 0
        in_table = False
        continue
    if s.startswith("|") and "序号" in s:
        in_table = True
        continue
    if s.startswith("|---"):
        continue
    if in_table and s.startswith("|"):
        cols = [c.strip() for c in s.strip("|").split("|")]
        if len(cols) >= 4 and cols[0].startswith("MM-"):
            if len(cols) == 5:
                _id, wrong, correct, example, note = cols
            else:
                _id, wrong, correct, note = cols
                example = ""
            correct_stripped = re.sub(r"[（(]正确[）)]", "", correct).strip()
            alts = [a.strip() for a in re.split(r"[/／]", correct_stripped)]
            # 源表自相矛盾的行不是错误搭配：备注写"通用"（MM-004 深化改革——中央固定表述"全面深化改革"），
            # 或正确写法里就包含错误写法（MM-005 进行研究→开展研究/进行研究）。P3 用真实成稿跑机检时发现
            if wrong == correct or wrong == correct_stripped or wrong in alts or "通用" in note:
                continue  # 表格里"XX（正确）"这类行是在确认某用法本身没错，不是错误搭配，跳过
            n += 1
            out.append({
                "id": f"{group_code}-{n:02d}",
                "category": "搭配",
                "subgroup": subgroup,
                "wrong": wrong,
                "correct": correct,
                "example": example,
                "note": note,
                "enforce": "hard",
            })
        continue
    m = re.match(r"^-\s*❌\s*(.+?)\s*→\s*✅\s*(.+)$", s)
    if m and group_code:
        wrong, correct = m.groups()
        wrong, correct = wrong.strip(), correct.strip()
        if wrong == re.sub(r"[（(]正确[）)]", "", correct).strip():
            continue  # 同上：确认用法没错的行，不是错误搭配
        n += 1
        out.append({
            "id": f"{group_code}-{n:02d}",
            "category": "搭配",
            "subgroup": subgroup,
            "wrong": wrong.strip(),
            "correct": correct.strip(),
            "example": "",
            "note": "",
            "enforce": "hard",
        })

# ---------- CP 套话 ----------
cp_lines = section_slice(lines, "第四部分：高频套话替换表", "第五部分：烟草行业专业术语库")
group_code, subgroup = None, None
n = 0
in_table = False
for line in cp_lines:
    s = line.strip()
    m = re.match(r"^###\s*(CP-\d+)\s+(\S+)", s)
    if m:
        group_code, subgroup = m.group(1), m.group(2)
        n = 0
        in_table = False
        continue
    if s.startswith("|") and "原套话" in s:
        in_table = True
        continue
    if s.startswith("|---"):
        continue
    if in_table and s.startswith("|"):
        cols = [c.strip() for c in s.strip("|").split("|")]
        if len(cols) == 4 and cols[0] not in ("原套话",):
            original, suggested, scene, note = cols
            n += 1
            out.append({
                "id": f"{group_code}-{n:02d}",
                "category": "套话",
                "subgroup": subgroup,
                "original": original,
                "suggested": suggested,
                "scene": scene,
                "note": note,
                "enforce": "advice",
            })

# ---------- 输出 ----------
by_cat = {}
for r in out:
    by_cat.setdefault(r["category"], 0)
    by_cat[r["category"]] += 1

print("解析结果：", by_cat, "总计", len(out))

dst = sys.argv[1] if len(sys.argv) > 1 else common.project_root() / "20_knowledge/terms/official_terms_解构.jsonl"
with open(dst, "w", encoding="utf-8") as f:
    for r in out:
        f.write(json.dumps(r, ensure_ascii=False) + "\n")
print("写入", dst)
