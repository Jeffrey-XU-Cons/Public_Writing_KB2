#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
范文库修复第二阶段执行脚本
A. 删假评分字段
B. 加 line 标签
C. 修 6 条确认断链
D. 去重 P3: 90 → 73
E. 归档坏分卷(元数据评分版 + article_index_part1/2/3)
"""

import json
import shutil
import yaml
from pathlib import Path

BASE = Path("d:/projects/Public_Writing_KB")

# ── 路径常量 ──────────────────────────────────────────────
P3_PATH          = BASE / "04_corpus/优质范文库(P3).yaml"
META_ORIG_PATH   = BASE / "04_corpus/个人历史交付物元数据索引.yaml"
META_SCORED_PATH = BASE / "04_corpus/个人历史交付物元数据索引_评分版.yaml"
DELIV_PATH       = BASE / "04_corpus/own_deliverables/deliverable_index.json"
ARTICLE_PATH     = BASE / "04_corpus/selected_articles/article_index.json"
ARCHIVE_DIR      = BASE / "99_archive_废弃内容库"

PART_FILES = [
    BASE / "04_corpus/selected_articles/article_index_part1.json",
    BASE / "04_corpus/selected_articles/article_index_part2.json",
    BASE / "04_corpus/selected_articles/article_index_part3.json",
]

# ── C. 断链修复映射(仅6条确认) ────────────────────────────
BROKEN_LINK_FIXES = {
    "00_raw_materials/个人历史交付物/方案类/成都、银川对标共建第二阶段工作实施方案.md":
        "00_raw_materials/实施方案/成都、银川对标共建第二阶段工作实施方案.md",
    "00_raw_materials/个人历史交付物/方案类/汉中卷烟厂全要素物流管理诊断实施方案（9.6）.md":
        "00_raw_materials/实施方案/汉中卷烟厂全要素物流管理诊断实施方案（9.6）.md",
    "00_raw_materials/个人历史交付物/方案类/烟草物流应急体系研究与构建项目实施方案（会后修改稿）.md":
        "00_raw_materials/实施方案/烟草物流应急体系研究与构建项目实施方案（会后修改稿）.md",
    "00_raw_materials/个人历史交付物/方案类/陕西 中烟 智慧 物流数字化转型实施方案 2.md":
        "00_raw_materials/实施方案/陕西 中烟 智慧 物流数字化转型实施方案 2.md",
    "00_raw_materials/个人历史交付物/规划类/1-1河南中烟工业有限责任公司南阳卷烟厂数字化转型中长期规划.md":
        "00_raw_materials/发展规划/1-1河南中烟工业有限责任公司南阳卷烟厂数字化转型中长期规划.md",
    "00_raw_materials/个人历史交付物/规划类/长株潭公司十四五战略规划（意见修订稿）-20210220.md":
        "00_raw_materials/发展规划/长株潭公司十四五战略规划（意见修订稿）-20210220.md",
}

# ── 南阳三胞胎:仅保留无数字前缀的规范命名 ──────────────
NANYANG_KEEP = "00_raw_materials/个人历史交付物/规划类/河南中烟工业有限责任公司南阳卷烟厂数字化转型中长期规划.md"
NANYANG_DELETE = {
    "00_raw_materials/个人历史交付物/规划类/1-1河南中烟工业有限责任公司南阳卷烟厂数字化转型中长期规划.md",
    "00_raw_materials/个人历史交付物/规划类/1.河南中烟工业有限责任公司南阳卷烟厂数字化转型中长期规划.md",
}


def load_yaml(path):
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def save_yaml(data, path):
    with open(path, "w", encoding="utf-8") as f:
        yaml.dump(data, f, allow_unicode=True, default_flow_style=False, sort_keys=False)


def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_json(data, path):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    # 末尾加换行
    with open(path, "a", encoding="utf-8") as f:
        f.write("\n")


def fix_link(fp):
    return BROKEN_LINK_FIXES.get(fp, fp)


# ════════════════════════════════════════════════════════
# 步骤 1: 处理 P3.yaml  (A+B+C+D)
# ════════════════════════════════════════════════════════
print("=" * 60)
print("步骤 1: 处理 P3.yaml")
print("=" * 60)

raw_p3 = load_yaml(P3_PATH)
print(f"  加载完成: {len(raw_p3)} 条(含重复)")

# D: 去重 — 先按 file_path 保留首次出现
seen_fps = {}
for item in raw_p3:
    fp = item["file_path"]
    if fp not in seen_fps:
        seen_fps[fp] = item  # 保留首次

deduped = list(seen_fps.values())
print(f"  去重后(排除完全重复): {len(deduped)} 条")

# D: 南阳三胞胎 — 删除有数字前缀的两种变体
before_nanyang = len(deduped)
deduped = [item for item in deduped if item["file_path"] not in NANYANG_DELETE]
print(f"  删除南阳三胞胎冗余变体: {before_nanyang - len(deduped)} 条 → 剩 {len(deduped)} 条")

if len(deduped) != 73:
    print(f"  ⚠️ 警告: 预期73条，实际{len(deduped)}条，请检查！")
    raise SystemExit(1)

# A: 删除假评分字段
FAKE_FIELDS_P3 = {"quality_score", "rank", "comprehensive_score"}
fields_removed = 0
for item in deduped:
    for field in FAKE_FIELDS_P3:
        if field in item:
            del item[field]
            fields_removed += 1

print(f"  删除假评分字段: {fields_removed} 个字段值")

# C: 修断链
link_fixed = 0
for item in deduped:
    old_fp = item["file_path"]
    new_fp = fix_link(old_fp)
    if new_fp != old_fp:
        item["file_path"] = new_fp
        link_fixed += 1

print(f"  修复断链: {link_fixed} 条")

# B: 加 line 标签
for item in deduped:
    item["line"] = "个人范文"

save_yaml(deduped, P3_PATH)
print(f"  ✅ P3.yaml 保存完成: {len(deduped)} 条")

# ════════════════════════════════════════════════════════
# 步骤 2: 处理 元数据索引.yaml (原版)  (A+B+C)
# ════════════════════════════════════════════════════════
print("\n" + "=" * 60)
print("步骤 2: 处理 元数据索引.yaml (原版)")
print("=" * 60)

meta_orig = load_yaml(META_ORIG_PATH)
print(f"  加载完成: {len(meta_orig)} 条")

# A: 删 quality_score
qs_removed = 0
for item in meta_orig:
    if "quality_score" in item:
        del item["quality_score"]
        qs_removed += 1
print(f"  删除 quality_score: {qs_removed} 条")

# C: 修断链
link_fixed_meta = 0
for item in meta_orig:
    old_fp = item["file_path"]
    new_fp = fix_link(old_fp)
    if new_fp != old_fp:
        item["file_path"] = new_fp
        link_fixed_meta += 1
print(f"  修复断链: {link_fixed_meta} 条")

# B: 加 line 标签
for item in meta_orig:
    item["line"] = "个人范文"

save_yaml(meta_orig, META_ORIG_PATH)
print(f"  ✅ 元数据索引.yaml 保存完成: {len(meta_orig)} 条")

# ════════════════════════════════════════════════════════
# 步骤 3: 归档 元数据索引_评分版.yaml  (E)
# ════════════════════════════════════════════════════════
print("\n" + "=" * 60)
print("步骤 3: 归档 元数据索引_评分版.yaml")
print("=" * 60)

dest = ARCHIVE_DIR / META_SCORED_PATH.name
shutil.move(str(META_SCORED_PATH), str(dest))
print(f"  ✅ 已移动至 {dest.relative_to(BASE)}")

# ════════════════════════════════════════════════════════
# 步骤 4: 处理 deliverable_index.json  (A+B)
# ════════════════════════════════════════════════════════
print("\n" + "=" * 60)
print("步骤 4: 处理 deliverable_index.json")
print("=" * 60)

deliv = load_json(DELIV_PATH)
print(f"  加载完成: {len(deliv)} 条")

removed_grade = 0
for item in deliv:
    if "quality_grade" in item:
        del item["quality_grade"]
        removed_grade += 1
    item["line"] = "个人范文"

print(f"  删除 quality_grade: {removed_grade} 条")
print(f"  加 line=个人范文: {len(deliv)} 条")

save_json(deliv, DELIV_PATH)
print(f"  ✅ deliverable_index.json 保存完成")

# ════════════════════════════════════════════════════════
# 步骤 5: 处理 article_index.json  (A+B)
# ════════════════════════════════════════════════════════
print("\n" + "=" * 60)
print("步骤 5: 处理 article_index.json")
print("=" * 60)

articles = load_json(ARTICLE_PATH)
print(f"  加载完成: {len(articles)} 条")

removed_grade = 0
for item in articles:
    if "quality_grade" in item:
        del item["quality_grade"]
        removed_grade += 1
    item["line"] = "写作教材"

print(f"  删除 quality_grade: {removed_grade} 条")
print(f"  加 line=写作教材: {len(articles)} 条")

save_json(articles, ARTICLE_PATH)
print(f"  ✅ article_index.json 保存完成")

# ════════════════════════════════════════════════════════
# 步骤 6: 归档 article_index_part1/2/3.json  (E)
# ════════════════════════════════════════════════════════
print("\n" + "=" * 60)
print("步骤 6: 归档 article_index_part*.json")
print("=" * 60)

for part_file in PART_FILES:
    if part_file.exists():
        dest = ARCHIVE_DIR / part_file.name
        shutil.move(str(part_file), str(dest))
        print(f"  ✅ 已归档: {part_file.name}")
    else:
        print(f"  ⚠️ 文件不存在，跳过: {part_file.name}")

# ════════════════════════════════════════════════════════
# 汇总报告
# ════════════════════════════════════════════════════════
print("\n" + "=" * 60)
print("汇总报告")
print("=" * 60)

# 验证 P3 最终状态
final_p3 = load_yaml(P3_PATH)
line_counts = {}
for item in final_p3:
    line_counts[item.get("line", "无")] = line_counts.get(item.get("line", "无"), 0) + 1

print(f"\nP3 最终条数: {len(final_p3)}")
print(f"P3 line 分布: {line_counts}")
print(f"P3 含 quality_score: {sum(1 for i in final_p3 if 'quality_score' in i)} 条(应为0)")

# 验证 article_index
final_articles = load_json(ARTICLE_PATH)
art_line = {}
for item in final_articles:
    art_line[item.get("line", "无")] = art_line.get(item.get("line", "无"), 0) + 1
print(f"\narticle_index 条数: {len(final_articles)}")
print(f"article_index line 分布: {art_line}")
print(f"article_index 含 quality_grade: {sum(1 for i in final_articles if 'quality_grade' in i)} 条(应为0)")

# 验证 deliverable_index
final_deliv = load_json(DELIV_PATH)
print(f"\ndeliverable_index 条数: {len(final_deliv)}")
print(f"deliverable_index 含 quality_grade: {sum(1 for i in final_deliv if 'quality_grade' in i)} 条(应为0)")

print("\n归档文件列表:")
for f in ARCHIVE_DIR.iterdir():
    print(f"  {f.name}")

print("\n✅ 第二阶段执行完毕")
