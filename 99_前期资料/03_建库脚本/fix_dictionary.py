#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
词典库修复脚本 - dictionary_unified.jsonl
修复内容：
  1. 删除重复ID条目（保留第一次出现的）
  2. 标记content为空的条目，输出到待人工补充清单
  3. 输出修复后的新文件 dictionary_unified_fixed.jsonl
  4. 输出问题清单 dictionary_issues.md（供人工核查）
用法：python fix_dictionary.py
"""

import json
from pathlib import Path
from datetime import datetime
from collections import defaultdict

PROJECT_ROOT = Path(__file__).parent
INPUT_FILE = PROJECT_ROOT / "data_prep/dictionary_unified.jsonl"
OUTPUT_FILE = PROJECT_ROOT / "data_prep/dictionary_unified_fixed.jsonl"
ISSUES_FILE = PROJECT_ROOT / "data_prep/dictionary_issues.md"


def fix_dictionary():
    if not INPUT_FILE.exists():
        print(f"❌ 文件不存在：{INPUT_FILE}")
        return

    all_records = []
    parse_errors = []

    # ── 读取所有记录 ──────────────────────────────────────────
    with open(INPUT_FILE, "r", encoding="utf-8") as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
                record["_line_num"] = line_num
                all_records.append(record)
            except json.JSONDecodeError as e:
                parse_errors.append(f"行{line_num}：{e}")

    print(f"读取完成：共{len(all_records)}条记录")

    # ── 处理重复ID ────────────────────────────────────────────
    seen_ids = {}
    duplicates = []
    deduped_records = []

    for record in all_records:
        rid = record.get("id", "")
        if not rid:
            # 无ID的记录直接保留
            deduped_records.append(record)
            continue

        if rid in seen_ids:
            duplicates.append({
                "id": rid,
                "first_line": seen_ids[rid]["_line_num"],
                "duplicate_line": record["_line_num"],
                "content_preview": str(record.get("content", ""))[:50]
            })
        else:
            seen_ids[rid] = record
            deduped_records.append(record)

    print(f"去重完成：删除{len(duplicates)}条重复记录，剩余{len(deduped_records)}条")

    # ── 识别content为空的条目 ─────────────────────────────────
    empty_content = []
    valid_records = []

    for record in deduped_records:
        content = record.get("content", "")
        if content is None or (isinstance(content, str) and content.strip() == ""):
            empty_content.append(record)
        else:
            valid_records.append(record)

    print(f"空content：{len(empty_content)}条需要人工补充")
    print(f"有效记录：{len(valid_records)}条")

    # ── 输出修复后的文件（只包含有效记录）────────────────────
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        for record in valid_records:
            # 移除内部辅助字段
            clean = {k: v for k, v in record.items() if not k.startswith("_")}
            f.write(json.dumps(clean, ensure_ascii=False) + "\n")

    print(f"✅ 修复文件已输出：{OUTPUT_FILE}")

    # ── 生成问题清单 ──────────────────────────────────────────
    lines = []
    lines.append(f"# 词典库问题清单")
    lines.append(f"**生成时间：** {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    lines.append(f"**原始文件：** {INPUT_FILE}")
    lines.append(f"**修复文件：** {OUTPUT_FILE}")
    lines.append("")
    lines.append("---")
    lines.append("")

    # 统计
    lines.append("## 一、修复统计")
    lines.append("")
    lines.append(f"| 项目 | 数量 |")
    lines.append(f"|------|------|")
    lines.append(f"| 原始总条数 | {len(all_records)} |")
    lines.append(f"| 删除重复ID | {len(duplicates)} |")
    lines.append(f"| content为空（需补充） | {len(empty_content)} |")
    lines.append(f"| JSON解析失败 | {len(parse_errors)} |")
    lines.append(f"| **修复后有效条数** | **{len(valid_records)}** |")
    lines.append("")

    # 重复ID清单
    if duplicates:
        lines.append("## 二、被删除的重复ID清单（已保留首次出现的记录）")
        lines.append("")
        lines.append("| 重复ID | 首次出现行 | 重复出现行 | 内容预览 |")
        lines.append("|--------|-----------|-----------|---------|")
        for d in duplicates:
            lines.append(f"| {d['id']} | 行{d['first_line']} | 行{d['duplicate_line']} | {d['content_preview']} |")
        lines.append("")

    # content为空的条目
    if empty_content:
        lines.append("## 三、content为空的条目（需人工补充后重新导入）")
        lines.append("")
        lines.append("以下条目已从修复文件中移除，请补充content后手动添加回 dictionary_unified_fixed.jsonl")
        lines.append("")
        lines.append("| ID | 其他字段 |")
        lines.append("|-----|---------|")
        for record in empty_content:
            rid = record.get("id", "无ID")
            other_fields = {k: v for k, v in record.items()
                          if k not in ["id", "content", "_line_num"]}
            other_str = str(other_fields)[:80]
            lines.append(f"| {rid} | {other_str} |")
        lines.append("")
        lines.append("### 完整的空content条目（JSON格式，供直接编辑）")
        lines.append("")
        lines.append("```json")
        for record in empty_content[:20]:  # 最多显示20条
            clean = {k: v for k, v in record.items() if not k.startswith("_")}
            lines.append(json.dumps(clean, ensure_ascii=False))
        if len(empty_content) > 20:
            lines.append(f"... 还有{len(empty_content) - 20}条，请查看原文件")
        lines.append("```")
        lines.append("")

    # 解析错误
    if parse_errors:
        lines.append("## 四、JSON解析失败的行")
        lines.append("")
        for err in parse_errors:
            lines.append(f"- {err}")
        lines.append("")

    lines.append("---")
    lines.append("")
    lines.append("## 五、下一步操作")
    lines.append("")
    lines.append("1. 确认修复文件 `dictionary_unified_fixed.jsonl` 内容正确")
    lines.append("2. 逐条补充「三」中列出的空content条目")
    lines.append("3. 补充完成后将这些条目追加到 `dictionary_unified_fixed.jsonl`")
    lines.append("4. 用修复文件替换原文件：")
    lines.append("   `copy data_prep\\dictionary_unified_fixed.jsonl data_prep\\dictionary_unified.jsonl`")
    lines.append("5. 回到 Claude Project 告知词典库修复完成")

    with open(ISSUES_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    print(f"✅ 问题清单已输出：{ISSUES_FILE}")

    # 控制台摘要
    print("\n" + "="*50)
    print("修复完成摘要")
    print("="*50)
    print(f"原始条数：{len(all_records)}")
    print(f"删除重复：{len(duplicates)}条")
    print(f"空content（移出待补充）：{len(empty_content)}条")
    print(f"修复后有效条数：{len(valid_records)}条")
    print(f"\n输出文件：")
    print(f"  {OUTPUT_FILE}")
    print(f"  {ISSUES_FILE}")
    print(f"\n请将 dictionary_issues.md 粘贴到 Claude Project 确认后再替换原文件。")


if __name__ == "__main__":
    fix_dictionary()
