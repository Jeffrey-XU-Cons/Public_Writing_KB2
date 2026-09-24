#!/usr/bin/env python3
"""B1: Generate rules_master.yaml by consolidating all rule files into 5 categories.

Categories: FORMAT, TERM, LOGIC, STYLE, GENRE
Output: 02_rules/rules_master.yaml
"""

import yaml
import os
import sys

# ─── helpers ───────────────────────────────────────────────────────────────

def load_yaml(path):
    with open(path, encoding='utf-8') as f:
        return yaml.safe_load(f)

def entries_from(data):
    """Extract list of entry dicts from any structure."""
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        for key in ('entries', 'rules', 'entries_sp', 'oral_to_formal_mapping'):
            if key in data and isinstance(data[key], list):
                return data[key]
    return []

BASE = "D:/projects/Public_Writing_KB/02_rules"

# ─── load all sources ──────────────────────────────────────────────────────

BOOK_FILES = {
    "胡森林_公文写作底层心法":  "胡森林_公文写作底层心法.yaml",
    "胡森林_公文写作心法笔杆":  "胡森林_公文写作心法笔杆.yaml",
    "王群_公文写作大手笔":      "王群_公文写作大手笔.yaml",
    "公文高手自我修炼":         "公文高手自我修炼.yaml",
    "笔杆子炼成":               "笔杆子炼成.yaml",
    "李忠秋_结构化写作":        "李忠秋_结构化写作.yaml",
}

sources = {}
for key, fname in BOOK_FILES.items():
    sources[key] = load_yaml(f"{BASE}/book_principles/{fname}")
sources["format_rules"]   = load_yaml(f"{BASE}/format_compliance/format_rules.yaml")
sources["language_rules"] = load_yaml(f"{BASE}/language_style/language_rules.yaml")
sources["oral_to_formal"] = load_yaml(f"{BASE}/language_style/oral_to_formal_mapping.yaml")
sources["quality_rules"]  = load_yaml(f"{BASE}/content_quality/quality_rules.yaml")

# ─── assign rule_type for files that lack it ──────────────────────────────
# 李忠秋: all structure principles → LOGIC
# 笔杆子炼成: MT/SP entries → LOGIC, LR entries → STYLE
# format_rules: all → FORMAT
# language_rules/oral_to_formal: → TERM
# quality_rules: logic/style sub-cats

BOOK_SOURCE_KEYS = set(BOOK_FILES.keys())

TYPE_OVERRIDES = {
    "李忠秋_结构化写作": "LOGIC",    # all entries
}

def infer_rule_type(entry, source_key):
    rt = entry.get("rule_type")
    if rt:
        return rt
    if source_key in TYPE_OVERRIDES:
        return TYPE_OVERRIDES[source_key]
    if source_key == "笔杆子炼成":
        t = entry.get("type", "MT")
        if t in ("LR",):
            return "STYLE"
        if t in ("SP", "MT"):
            return "LOGIC"
        return "LOGIC"
    if source_key == "format_rules":
        return "FORMAT"
    if source_key == "oral_to_formal":
        return "TERM"
    if source_key == "language_rules":
        sub = entry.get("sub_category", "")
        if "oral" in sub:
            return "TERM"
        return "STYLE"
    if source_key == "quality_rules":
        sub = entry.get("sub_category", "logic")
        if sub in ("logic", "data_support", "policy_citation"):
            return "LOGIC"
        return "STYLE"
    return "LOGIC"

# ─── collect all entries ──────────────────────────────────────────────────

all_rules = {
    "FORMAT": [],
    "TERM":   [],
    "LOGIC":  [],
    "STYLE":  [],
    "GENRE":  [],
}

def normalize_entry(entry, source_key, rule_type):
    """Return a normalized dict for rules_master."""
    eid = entry.get("id", "?")
    # Handle oral_to_formal entries specially
    if source_key == "oral_to_formal" and "oral" in entry:
        oral = entry.get("oral", "")
        formal = entry.get("formal", "")
        title = f"{oral} → {formal}"
        content_summary = entry.get("notes", "")
        importance = "A" if entry.get("frequency") == "high" else "B"
        return {
            "id": eid,
            "title": title,
            "importance": importance,
            "execution": "code",
            "applicable_types": ["通用"],
            "content_summary": content_summary,
            "source_file": "02_rules/language_style/oral_to_formal_mapping.yaml",
        }
    title = entry.get("title", "")
    # For format_rules and quality_rules, map severity → importance
    if "importance" in entry:
        importance = entry["importance"]
    elif "severity" in entry:
        sev = entry["severity"]
        importance = "A" if sev == "error" else "B"
    else:
        importance = "B"
    applicable = entry.get("applicable_types", ["通用"])
    execution = entry.get("execution", "agent_prompt")
    # For format_rules, infer execution from type field
    if source_key == "format_rules":
        t = entry.get("type", "llm_review")
        execution = "code" if t == "auto_detect" else "agent_prompt"
    # For language/oral rules, these are auto-replace
    if source_key in ("language_rules", "oral_to_formal"):
        execution = "code"
    # For quality_rules, use check_question as content
    content = entry.get("content", entry.get("description", entry.get("check_question", "")))
    # Truncate long content to first 200 chars for index
    if content and len(content) > 300:
        content_summary = content[:280].strip() + "…"
    else:
        content_summary = content.strip() if content else ""

    return {
        "id": eid,
        "title": title,
        "importance": importance,
        "execution": execution,
        "applicable_types": applicable if isinstance(applicable, list) else list(applicable),
        "content_summary": content_summary,
        "source_file": (
            "02_rules/format_compliance/format_rules.yaml" if source_key == "format_rules" else
            f"02_rules/language_style/{'oral_to_formal_mapping' if source_key=='oral_to_formal' else source_key}.yaml" if source_key in ("language_rules", "oral_to_formal") else
            "02_rules/content_quality/quality_rules.yaml" if source_key == "quality_rules" else
            f"02_rules/book_principles/{BOOK_FILES.get(source_key, source_key+'.yaml')}"
        ),
    }

for source_key, data in sources.items():
    entries = entries_from(data)
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        rt = infer_rule_type(entry, source_key)
        if rt not in all_rules:
            rt = "LOGIC"
        norm = normalize_entry(entry, source_key, rt)
        all_rules[rt].append(norm)

# ─── sort by importance (A > B > C) ─────────────────────────────────────

IMP_ORDER = {"A": 0, "B": 1, "C": 2}
for cat in all_rules:
    all_rules[cat].sort(key=lambda e: IMP_ORDER.get(e["importance"], 3))

# ─── print stats ──────────────────────────────────────────────────────────

total = 0
for cat, rules in all_rules.items():
    a = sum(1 for r in rules if r["importance"] == "A")
    b = sum(1 for r in rules if r["importance"] == "B")
    c = sum(1 for r in rules if r["importance"] == "C")
    print(f"  {cat}: {len(rules)}条 (A:{a} B:{b} C:{c})")
    total += len(rules)
print(f"  TOTAL: {total}条")

# ─── build master structure ───────────────────────────────────────────────

CATEGORY_DESCS = {
    "FORMAT": "格式合规类规则——针对公文格式、标点、编号、行文方向等可自动检测的规范问题。主要由Agent 4（格式审核）code节点执行。",
    "TERM":   "术语规范类规则——口语词汇替换为公文规范表述，禁用词识别，术语统一。主要由Agent 5（术语校对）code节点执行。",
    "LOGIC":  "逻辑结构类规则——结构完整性、论点论据一致性、层次逻辑、段落组织等。主要由Agent 4/5 LLM节点执行。",
    "STYLE":  "语言风格类规则——文风简练、避免套话废话、语体适当、语气匹配等。主要由Agent 6（润色）和Agent 5执行。",
    "GENRE":  "文种规范类规则——各文种特有的结构要求、禁止事项、适用场景。主要由Agent 1（意图识别）和Agent 3（起草）参考。",
}

master = {
    "metadata": {
        "name": "公文写作规则总库 (Rules Master)",
        "version": "1.0",
        "generated_at": "2026-03-18",
        "description": (
            "整合所有规则来源，按FORMAT/TERM/LOGIC/STYLE/GENRE五大类组织。"
            "A级规则为必查项，B级为建议检查项，C级为参考项。"
            "execution字段：code=可程序化检测，agent_prompt=需LLM判断。"
        ),
        "total_rules": total,
        "rule_counts": {cat: len(rules) for cat, rules in all_rules.items()},
        "source_files": [
            "02_rules/book_principles/胡森林_公文写作底层心法.yaml",
            "02_rules/book_principles/胡森林_公文写作心法笔杆.yaml",
            "02_rules/book_principles/王群_公文写作大手笔.yaml",
            "02_rules/book_principles/公文高手自我修炼.yaml",
            "02_rules/book_principles/笔杆子炼成.yaml",
            "02_rules/book_principles/李忠秋_结构化写作.yaml",
            "02_rules/format_compliance/format_rules.yaml",
            "02_rules/language_style/language_rules.yaml",
            "02_rules/language_style/oral_to_formal_mapping.yaml",
            "02_rules/content_quality/quality_rules.yaml",
        ],
    },
    "FORMAT": {
        "description": CATEGORY_DESCS["FORMAT"],
        "rule_count": len(all_rules["FORMAT"]),
        "rules": all_rules["FORMAT"],
    },
    "TERM": {
        "description": CATEGORY_DESCS["TERM"],
        "rule_count": len(all_rules["TERM"]),
        "rules": all_rules["TERM"],
    },
    "LOGIC": {
        "description": CATEGORY_DESCS["LOGIC"],
        "rule_count": len(all_rules["LOGIC"]),
        "rules": all_rules["LOGIC"],
    },
    "STYLE": {
        "description": CATEGORY_DESCS["STYLE"],
        "rule_count": len(all_rules["STYLE"]),
        "rules": all_rules["STYLE"],
    },
    "GENRE": {
        "description": CATEGORY_DESCS["GENRE"],
        "rule_count": len(all_rules["GENRE"]),
        "rules": all_rules["GENRE"],
    },
}

# ─── write output ─────────────────────────────────────────────────────────

out_path = "D:/projects/Public_Writing_KB/02_rules/rules_master.yaml"
with open(out_path, 'w', encoding='utf-8') as f:
    yaml.dump(
        master,
        f,
        allow_unicode=True,
        default_flow_style=False,
        sort_keys=False,
        indent=2,
        width=120,
    )

print(f"\nWrote: {out_path}")
sz = os.path.getsize(out_path)
print(f"File size: {sz/1024:.1f} KB")
