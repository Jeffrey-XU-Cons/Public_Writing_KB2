#!/usr/bin/env python3
"""
B1 后处理：对 rules_master.yaml 进行去重和冲突说明。

操作清单：
1. 删除跨类别精确重复（STYLE 中重复了 TERM 中政治术语的 LS- 规则）
2. 删除 LOGIC 中与其他条目完全重复的 PM-001（结构三字诀）
3. 合并/删除空话套话系列在 LOGIC、STYLE 中重复出现的条目
4. 为 5 处冲突规则添加 context_note 说明适用边界
5. 修复源文件中存在的重复 ID（不同书籍使用了相同 SP-003 等 ID）
"""

import yaml
import os
import copy
from difflib import SequenceMatcher

INPUT = "D:/projects/Public_Writing_KB/02_rules/rules_master.yaml"

# ─── 加载 ──────────────────────────────────────────────────────────────────

with open(INPUT, encoding="utf-8") as f:
    data = yaml.safe_load(f)


def get_rules(cat):
    return data[cat]["rules"]


def set_rules(cat, rules):
    data[cat]["rules"] = rules
    data[cat]["rule_count"] = len(rules)


# ─── 辅助函数 ──────────────────────────────────────────────────────────────

def similarity(a, b):
    """字符串相似度 0~1"""
    return SequenceMatcher(None, a, b).ratio()


def find_by_title(cat, title_fragment):
    return [r for r in get_rules(cat) if title_fragment in r.get("title", "")]


def remove_by_title(cat, title_fragment, reason=""):
    before = len(get_rules(cat))
    rules = [r for r in get_rules(cat) if title_fragment not in r.get("title", "")]
    removed = before - len(rules)
    if removed:
        print(f"  [{cat}] 删除 {removed} 条：含'{title_fragment}'  原因：{reason}")
    set_rules(cat, rules)
    return removed


def add_note(cat, title_fragment, note_key, note_text):
    for r in get_rules(cat):
        if title_fragment in r.get("title", ""):
            r[note_key] = note_text
            print(f"  [{cat}] 添加{note_key}：'{r['title'][:40]}'")


def merge_into(cat, source_title_frag, target_title_frag, reason=""):
    """把 source 的 content_summary 合并进 target，然后删除 source"""
    source = next((r for r in get_rules(cat)
                   if source_title_frag in r.get("title", "")), None)
    target = next((r for r in get_rules(cat)
                   if target_title_frag in r.get("title", "")), None)
    if source and target:
        if source.get("content_summary"):
            existing = target.get("merged_from", [])
            existing.append({
                "from_id": source.get("id"),
                "from_title": source.get("title"),
                "content": source.get("content_summary", ""),
            })
            target["merged_from"] = existing
        rules = [r for r in get_rules(cat)
                 if source_title_frag not in r.get("title", "")]
        print(f"  [{cat}] 合并 '{source.get('title','')[:35]}' → '{target.get('title','')[:35]}'  {reason}")
        set_rules(cat, rules)


# ═══════════════════════════════════════════════════════════════════════════
# 1. 删除 STYLE 中与 TERM 重复的政治术语规则（OTF 已覆盖）
# ═══════════════════════════════════════════════════════════════════════════
print("\n【1】删除 STYLE 跨类别重复（政治术语类）")

STYLE_POLITICAL_DUPES = [
    ("高质量发展", "已在TERM/OTF规则中覆盖，STYLE中重复"),
    ("绿水青山", "已在TERM/OTF规则中覆盖，STYLE中重复"),
    ("习近平新时代", "政治术语准确性已由TERM类规则统一管理"),
    ("中国式现代化", "政治术语准确性已由TERM类规则统一管理"),
    ("人类命运共同体", "政治术语准确性已由TERM类规则统一管理"),
]
for frag, reason in STYLE_POLITICAL_DUPES:
    remove_by_title("STYLE", frag, reason)


# ═══════════════════════════════════════════════════════════════════════════
# 2. 删除 LOGIC 中与 SP-006 完全重复的 PM-001（结构三字诀）
# ═══════════════════════════════════════════════════════════════════════════
print("\n【2】删除 LOGIC 中完全重复条目")

# PM-001 "结构三字诀（不板不乱浑然一体）" 与 SP-006 "结构不板不乱浑然一体原则" 内容相同
remove_by_title("LOGIC", "结构三字诀", "与 SP-006'结构不板不乱浑然一体原则'内容完全重复，保留 SP-006")

# PM-002 "研究者意识三句话" 在胡森林两本书中均有，保留 content 更完整的
# 检查 STYLE 和 LOGIC 中是否有同名重复
logic_titles = [r.get("title", "") for r in get_rules("LOGIC")]
style_titles = [r.get("title", "") for r in get_rules("STYLE")]

cross_dupes = []
for lt in logic_titles:
    for st in style_titles:
        if lt == st:
            cross_dupes.append(lt)
        elif lt and st and similarity(lt, st) > 0.85:
            cross_dupes.append((lt, st))

if cross_dupes:
    print(f"  发现 LOGIC/STYLE 跨类重复（标题相似度>85%）：")
    for d in cross_dupes[:10]:
        print(f"    {d}")


# ═══════════════════════════════════════════════════════════════════════════
# 3. 空话套话系列合并（CQ-011 为主条目，其余合并进入或添加 see_also）
# ═══════════════════════════════════════════════════════════════════════════
print("\n【3】空话套话系列：标注 see_also 关联关系")

# LOGIC 中的空话检测规则群：CQ-008、CQ-009、CQ-010、CQ-011、CQ-012、CQ-013、CQ-014
# CQ-011 为"正确的废话"最综合，其他为具体场景
# 方案：CQ-011 升为主规则，其余添加 see_also

EMPTY_TALK_MASTER = '"正确的废话"检测'  # CQ-011

for r in get_rules("LOGIC"):
    title = r.get("title", "")
    if any(kw in title for kw in ["套话", "废话", "开头", "结尾", "过渡语", "面面俱到"]):
        if EMPTY_TALK_MASTER not in title:
            r["see_also"] = "CQ-011（'正确的废话'检测）为套话废话的综合规则"
            print(f"  [LOGIC] 关联 CQ-011：'{title[:45]}'")

# STYLE 中的简洁文风规则群关联
for r in get_rules("STYLE"):
    title = r.get("title", "")
    if any(kw in title for kw in ["奥卡姆", "废话", "套话", "三弊"]):
        r["see_also"] = "CQ-011（'正确的废话'检测）为套话废话的综合规则；CQ-012（措施可操作性）"
        print(f"  [STYLE] 关联 CQ-011：'{title[:45]}'")


# ═══════════════════════════════════════════════════════════════════════════
# 4. 数据支撑系列关联（MT-010 为主规则）
# ═══════════════════════════════════════════════════════════════════════════
print("\n【4】数据支撑系列：标注 see_also")

for r in get_rules("LOGIC"):
    title = r.get("title", "")
    if any(kw in title for kw in ["数据支撑", "成效表述", "排他性", "数据时效", "数据来源"]):
        if "三维检验" not in title:
            r["see_also"] = "MT-010（言之有理有据有物三维检验）为数据支撑的综合规则"
            print(f"  [LOGIC] 关联 MT-010：'{title[:45]}'")


# ═══════════════════════════════════════════════════════════════════════════
# 5. 为 5 处冲突规则添加 context_note 说明适用边界
# ═══════════════════════════════════════════════════════════════════════════
print("\n【5】为冲突规则添加 context_note 适用边界说明")

CONFLICT_NOTES = [
    # (category, title_fragment, note)
    (
        "LOGIC",
        "面面俱到",
        "【适用边界】本规则针对段落级深度：单个段落不得蜻蜓点水覆盖多个无关主题。"
        "与SP-005（六要素完整性）不冲突——SP-005要求文档整体覆盖6个维度，本规则要求每个维度有足够深度。"
    ),
    (
        "STYLE",
        "领导讲稿",
        "【适用边界】本规则适用于现场宣读的领导讲话稿，强调口语化、情感感染力。"
        "正式存档公文（报告/方案）应遵循LR-002（公文语言四特点：准确/庄重/简要/平实）。"
    ),
    (
        "STYLE",
        "公文语言四特点",
        "【适用边界】本规则适用于正式存档公文（报告/方案/通知等）。"
        "领导现场讲话稿另有语言要求（见WQ_MT_011：讲稿主体四性要求：生动/鼓动/通俗）。"
    ),
    (
        "LOGIC",
        "内容决定结构",
        "【适用边界】本原则适用于经验材料、调研报告等内容驱动型文体，鼓励因内容灵活设计结构。"
        "标准化文种（通知、请示、批复等）应遵循GB/T 9704规定的固定格式，不适用本原则。"
    ),
    (
        "LOGIC",
        "公文六要素框架",
        "【适用边界】本框架适用于方案/计划类文体的完整性检查。"
        "与CQ-013（面面俱到问题）不冲突：六要素是文档级完整性要求，CQ-013是段落级深度要求。"
    ),
]

for cat, frag, note in CONFLICT_NOTES:
    found = False
    for r in get_rules(cat):
        if frag in r.get("title", ""):
            r["context_note"] = note
            found = True
            print(f"  [{cat}] 添加context_note：'{r['title'][:40]}'")
    if not found:
        print(f"  [{cat}] 未找到：'{frag}'（跳过）")


# ═══════════════════════════════════════════════════════════════════════════
# 6. 修复同名 ID 冲突（不同书同一 ID 如 SP-003）
# ═══════════════════════════════════════════════════════════════════════════
print("\n【6】修复跨书同名 ID 冲突")

for cat in ["FORMAT", "TERM", "LOGIC", "STYLE", "GENRE"]:
    seen_ids = {}
    for r in get_rules(cat):
        eid = r.get("id", "")
        src = r.get("source_file", "")
        key = eid
        if key in seen_ids:
            # 同一 ID 出现两次（来自不同书），添加书籍后缀
            old_src = seen_ids[key]
            if old_src != src:
                suffix = src.split("/")[-1].replace(".yaml", "").replace("_", "")[:6]
                new_id = f"{eid}_{suffix}"
                r["id"] = new_id
                print(f"  [{cat}] 重命名重复ID：{eid} → {new_id}（来自 {src.split('/')[-1]}）")
        else:
            seen_ids[key] = src


# ═══════════════════════════════════════════════════════════════════════════
# 7. 更新 metadata 统计
# ═══════════════════════════════════════════════════════════════════════════
total = sum(len(get_rules(cat)) for cat in ["FORMAT", "TERM", "LOGIC", "STYLE", "GENRE"])
data["metadata"]["total_rules"] = total
data["metadata"]["last_dedup"] = "2026-03-18"
data["metadata"]["dedup_notes"] = (
    "2026-03-18 去重处理：删除STYLE中与TERM重复的政治术语规则；"
    "删除LOGIC中与SP-006完全重复的PM-001；"
    "为空话套话系列、数据支撑系列添加see_also关联；"
    "为5处冲突规则添加context_note适用边界说明；"
    "修复跨书同名ID冲突。"
)
for cat in ["FORMAT", "TERM", "LOGIC", "STYLE", "GENRE"]:
    data[cat]["rule_count"] = len(get_rules(cat))


# ─── 输出 ──────────────────────────────────────────────────────────────────

with open(INPUT, "w", encoding="utf-8") as f:
    yaml.dump(data, f, allow_unicode=True, default_flow_style=False,
              sort_keys=False, indent=2, width=120)

print(f"\n✅ 完成。总规则数：{total}（原 349）")
print(f"   写入：{INPUT}")

# 输出各类别最终统计
for cat in ["FORMAT", "TERM", "LOGIC", "STYLE", "GENRE"]:
    rules = get_rules(cat)
    a = sum(1 for r in rules if r.get("importance") == "A")
    print(f"   {cat}: {len(rules)}条 (A:{a})")
