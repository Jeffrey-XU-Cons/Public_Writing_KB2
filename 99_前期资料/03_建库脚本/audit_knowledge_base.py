#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
知识库核查脚本 - Public_Writing_KB
用途：扫描所有知识库文件，自动发现格式问题、空字段、重复条目
用法：python audit_knowledge_base.py
输出：audit_report.md（问题清单，供人工核查使用）
"""

import json
import yaml
import os
import sys
from pathlib import Path
from collections import defaultdict
from datetime import datetime

# ── 配置：脚本放在项目根目录下运行 ──────────────────────────
PROJECT_ROOT = Path(__file__).parent
OUTPUT_FILE = PROJECT_ROOT / "audit_report.md"

# ── 核查目标文件清单 ─────────────────────────────────────────
JSONL_FILES = {
    "模板库": "data_prep/templates_import.jsonl",
    "词典库": "data_prep/dictionary_unified.jsonl",
    "语料库_范文": "data_prep/corpus_documents.jsonl",
    "段落库": "data_prep/corpus_paragraphs.jsonl",
    "金句库": "data_prep/corpus_golden_sentences.jsonl",
}

YAML_FILES = {
    "规则总表": "02_rules/rules_master.yaml",
    "公文用语词典v2": "03_dictionary/official_terms_v2.yaml",
    "格式规则": "02_rules/format_compliance/format_rules.yaml",
    "质量规则": "02_rules/content_quality/quality_rules.yaml",
    "语言风格规则": "02_rules/language_style/language_rules.yaml",
    "烟草组织术语": "03_dictionary/tobacco_terms/01_组织术语.yaml",
    "烟草业务术语": "03_dictionary/tobacco_terms/02_业务术语.yaml",
    "烟草政策术语": "03_dictionary/tobacco_terms/03_政策术语.yaml",
    "烟草管理成熟度术语": "03_dictionary/tobacco_terms/04_管理成熟度术语.yaml",
    "烟草十五五规划术语": "03_dictionary/tobacco_terms/05_十五五规划术语.yaml",
    "金句库P4": "03_dictionary/金句库(P4).yaml",
    "段落库P4": "04_corpus/段落库(P4).yaml",
}

# ── JSONL核查规则：每种文件必须有的字段 ─────────────────────
JSONL_REQUIRED_FIELDS = {
    "模板库": ["id", "name", "usage", "doc_type", "system_prompt"],
    "词典库": ["id", "content"],
    "语料库_范文": ["id", "content"],
    "段落库": ["id", "content"],
    "金句库": ["id", "content"],
}

# ── 结果收集器 ───────────────────────────────────────────────
issues = defaultdict(list)
stats = {}


# ════════════════════════════════════
# JSONL 文件核查
# ════════════════════════════════════

def audit_jsonl(name, filepath):
    """核查单个JSONL文件"""
    full_path = PROJECT_ROOT / filepath
    file_issues = []
    
    if not full_path.exists():
        issues[name].append(f"❌ 文件不存在：{filepath}")
        return 0

    required = JSONL_REQUIRED_FIELDS.get(name, [])
    total = 0
    empty_system_prompt = 0
    empty_content = 0
    missing_fields = defaultdict(int)
    duplicate_ids = []
    seen_ids = set()
    short_content = []  # 内容过短（可能不完整）
    
    try:
        with open(full_path, "r", encoding="utf-8") as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                if not line:
                    continue
                try:
                    record = json.loads(line)
                    total += 1
                    
                    # 检查重复ID
                    record_id = record.get("id", "")
                    if record_id:
                        if record_id in seen_ids:
                            duplicate_ids.append(f"行{line_num}: {record_id}")
                        seen_ids.add(record_id)
                    
                    # 检查必要字段
                    for field in required:
                        val = record.get(field)
                        if val is None:
                            missing_fields[field] += 1
                        elif isinstance(val, str) and val.strip() == "":
                            missing_fields[field] += 1
                    
                    # 针对模板库：检查system_prompt是否为空
                    if name == "模板库":
                        sp = record.get("system_prompt", "")
                        if not sp or sp.strip() == "":
                            empty_system_prompt += 1
                    
                    # 检查content字段内容长度
                    content = record.get("content", "")
                    if isinstance(content, str):
                        if content.strip() == "":
                            empty_content += 1
                        elif len(content) < 10:
                            short_content.append(f"行{line_num}: id={record_id}, 内容仅{len(content)}字")
                    
                except json.JSONDecodeError as e:
                    file_issues.append(f"⚠️ 行{line_num} JSON解析失败：{e}")
    
    except Exception as e:
        issues[name].append(f"❌ 文件读取失败：{e}")
        return 0
    
    stats[name] = {"总条数": total}
    
    # 汇总问题
    if missing_fields:
        for field, count in missing_fields.items():
            file_issues.append(f"⚠️ 字段「{field}」缺失或为空：{count}条（共{total}条）")
    
    if name == "模板库" and empty_system_prompt > 0:
        file_issues.append(f"🔴 system_prompt为空：{empty_system_prompt}条（共{total}条）"
                          f"——这些模板无法正常使用，需要人工补充")
    
    if empty_content > 0:
        file_issues.append(f"⚠️ content字段为空：{empty_content}条")
    
    if short_content:
        file_issues.append(f"⚠️ content过短（<10字）的条目：{len(short_content)}条")
        for s in short_content[:5]:  # 最多显示5条
            file_issues.append(f"    → {s}")
    
    if duplicate_ids:
        file_issues.append(f"🔴 发现重复ID：{len(duplicate_ids)}个")
        for d in duplicate_ids[:5]:
            file_issues.append(f"    → {d}")
    
    if file_issues:
        issues[name].extend(file_issues)
    else:
        issues[name].append(f"✅ 格式检查通过，共{total}条")
    
    return total


# ════════════════════════════════════
# YAML 文件核查
# ════════════════════════════════════

def audit_yaml(name, filepath):
    """核查单个YAML文件"""
    full_path = PROJECT_ROOT / filepath
    
    if not full_path.exists():
        issues[name].append(f"❌ 文件不存在：{filepath}")
        return
    
    file_issues = []
    
    try:
        with open(full_path, "r", encoding="utf-8") as f:
            content = f.read()
        
        # 检查文件是否为空
        if not content.strip():
            issues[name].append(f"❌ 文件为空：{filepath}")
            return
        
        # 尝试解析YAML
        try:
            data = yaml.safe_load(content)
        except yaml.YAMLError as e:
            issues[name].append(f"❌ YAML格式错误：{e}")
            return
        
        if data is None:
            issues[name].append(f"❌ YAML内容为空（解析结果为None）")
            return
        
        # 统计顶层条目数量
        if isinstance(data, dict):
            item_count = len(data)
            stats[name] = {"顶层键数": item_count}
            
            # 检查空值
            empty_keys = [k for k, v in data.items() 
                         if v is None or (isinstance(v, str) and v.strip() == "")]
            if empty_keys:
                file_issues.append(f"⚠️ 以下顶层键的值为空：{empty_keys[:10]}")
        
        elif isinstance(data, list):
            item_count = len(data)
            stats[name] = {"条目数": item_count}
            
            # 检查列表中的空项
            empty_items = sum(1 for item in data 
                            if item is None or (isinstance(item, str) and item.strip() == ""))
            if empty_items:
                file_issues.append(f"⚠️ 列表中有{empty_items}个空项")
            
            # 检查字典列表的必要字段
            if data and isinstance(data[0], dict):
                all_keys = set()
                for item in data:
                    if isinstance(item, dict):
                        all_keys.update(item.keys())
                stats[name]["字段列表"] = list(all_keys)[:10]
        
        # 检查文件大小
        file_size_kb = full_path.stat().st_size / 1024
        stats[name]["文件大小"] = f"{file_size_kb:.1f}KB"
        
        if file_size_kb < 0.5:
            file_issues.append(f"⚠️ 文件过小（{file_size_kb:.1f}KB），内容可能不完整")
        
        if not file_issues:
            file_issues.append(f"✅ YAML格式正常")
        
    except Exception as e:
        file_issues.append(f"❌ 读取失败：{e}")
    
    issues[name].extend(file_issues)


# ════════════════════════════════════
# 模板库专项核查：usage分布
# ════════════════════════════════════

def audit_template_usage_distribution():
    """统计模板库中各usage类型的分布"""
    filepath = PROJECT_ROOT / "data_prep/templates_import.jsonl"
    if not filepath.exists():
        return {}
    
    usage_dist = defaultdict(int)
    doc_type_dist = defaultdict(int)
    empty_sp_by_usage = defaultdict(int)
    
    with open(filepath, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
                usage = record.get("usage", "未知")
                doc_type = record.get("doc_type", "未知")
                usage_dist[usage] += 1
                doc_type_dist[doc_type] += 1
                
                sp = record.get("system_prompt", "")
                if not sp or sp.strip() == "":
                    empty_sp_by_usage[usage] += 1
            except:
                pass
    
    return usage_dist, doc_type_dist, empty_sp_by_usage


# ════════════════════════════════════
# 范文库专项核查：文种分布
# ════════════════════════════════════

def audit_corpus_distribution():
    """统计范文库中各文种的分布"""
    filepath = PROJECT_ROOT / "data_prep/corpus_documents.jsonl"
    if not filepath.exists():
        return {}
    
    doc_type_dist = defaultdict(int)
    score_dist = defaultdict(int)
    
    with open(filepath, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
                doc_type = record.get("doc_type", record.get("category", "未知"))
                score = record.get("quality_score", record.get("score", "无评分"))
                doc_type_dist[doc_type] += 1
                score_dist[str(score)] += 1
            except:
                pass
    
    return doc_type_dist, score_dist


# ════════════════════════════════════
# 检查selected_articles目录
# ════════════════════════════════════

def audit_selected_articles():
    """检查264篇范文的基本情况"""
    articles_dir = PROJECT_ROOT / "04_corpus/selected_articles"
    index_file = articles_dir / "article_index.json"
    
    result = []
    
    if not articles_dir.exists():
        result.append("❌ selected_articles目录不存在")
        return result
    
    md_files = list(articles_dir.glob("TA-*.md"))
    result.append(f"MD文件数量：{len(md_files)}")
    
    # 检查空文件
    empty_files = []
    short_files = []
    for md_file in md_files:
        size = md_file.stat().st_size
        if size == 0:
            empty_files.append(md_file.name)
        elif size < 500:  # 小于500字节可能内容不完整
            short_files.append(f"{md_file.name}（{size}字节）")
    
    if empty_files:
        result.append(f"❌ 空文件：{len(empty_files)}个 → {empty_files[:10]}")
    if short_files:
        result.append(f"⚠️ 内容过少（<500字节）：{len(short_files)}个")
        for s in short_files[:5]:
            result.append(f"    → {s}")
    
    # 检查索引文件
    if index_file.exists():
        try:
            with open(index_file, "r", encoding="utf-8") as f:
                index = json.load(f)
            if isinstance(index, list):
                result.append(f"索引条目数：{len(index)}")
                if len(index) != len(md_files):
                    result.append(f"⚠️ 索引数量({len(index)})与MD文件数量({len(md_files)})不一致")
            elif isinstance(index, dict):
                result.append(f"索引键数：{len(index)}")
        except Exception as e:
            result.append(f"⚠️ 索引文件解析失败：{e}")
    else:
        result.append("⚠️ article_index.json不存在")
    
    if not empty_files and not short_files:
        result.append("✅ 文件完整性检查通过")
    
    return result


# ════════════════════════════════════
# 生成报告
# ════════════════════════════════════

def generate_report():
    """生成Markdown格式的核查报告"""
    
    lines = []
    lines.append(f"# 知识库核查报告")
    lines.append(f"**生成时间：** {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    lines.append(f"**项目路径：** {PROJECT_ROOT}")
    lines.append("")
    lines.append("---")
    lines.append("")
    
    # ── P0：JSONL文件核查 ──
    lines.append("## 一、JSONL文件核查（P0 优先处理）")
    lines.append("")
    
    for name, filepath in JSONL_FILES.items():
        total = audit_jsonl(name, filepath)
        lines.append(f"### {name}")
        lines.append(f"**文件：** `{filepath}` | **总条数：** {total}")
        lines.append("")
        for issue in issues.get(name, []):
            lines.append(f"- {issue}")
        lines.append("")
    
    # ── 模板库专项：usage分布 ──
    lines.append("### 模板库专项：usage分布统计")
    lines.append("")
    try:
        usage_dist, doc_type_dist, empty_sp_by_usage = audit_template_usage_distribution()
        lines.append("**按usage分类：**")
        for usage, count in sorted(usage_dist.items(), key=lambda x: -x[1]):
            empty = empty_sp_by_usage.get(usage, 0)
            empty_note = f"（其中system_prompt为空：{empty}条）" if empty > 0 else ""
            lines.append(f"- `{usage}`：{count}条 {empty_note}")
        lines.append("")
        lines.append("**⚠️ 重点关注：以下usage类型与四类核心文种的对应关系**")
        lines.append("- `汇报类` → 汇报文种")
        lines.append("- `方案类` → 方案文种")
        lines.append("- `讲话类` → 讲话稿文种")
        lines.append("- `其他` → 暂不使用，数量最多，建议确认是否有遗漏归类")
        lines.append("")
    except Exception as e:
        lines.append(f"- 统计失败：{e}")
        lines.append("")
    
    # ── 范文库专项：文种分布 ──
    lines.append("### 语料库专项：文种分布统计")
    lines.append("")
    try:
        doc_type_dist, score_dist = audit_corpus_distribution()
        lines.append("**按doc_type分类：**")
        for dt, count in sorted(doc_type_dist.items(), key=lambda x: -x[1]):
            lines.append(f"- `{dt}`：{count}条")
        lines.append("")
        lines.append("**按质量评分分类：**")
        for score, count in sorted(score_dist.items()):
            lines.append(f"- 评分`{score}`：{count}条")
        lines.append("")
    except Exception as e:
        lines.append(f"- 统计失败：{e}")
        lines.append("")
    
    # ── P0：YAML规则文件核查 ──
    lines.append("## 二、YAML文件核查（P0-P1）")
    lines.append("")
    
    for name, filepath in YAML_FILES.items():
        audit_yaml(name, filepath)
        stat = stats.get(name, {})
        stat_str = " | ".join([f"{k}：{v}" for k, v in stat.items()])
        lines.append(f"### {name}")
        lines.append(f"**文件：** `{filepath}` | {stat_str}")
        lines.append("")
        for issue in issues.get(name, []):
            lines.append(f"- {issue}")
        lines.append("")
    
    # ── P2：selected_articles核查 ──
    lines.append("## 三、范文全文核查（P2）")
    lines.append("")
    article_results = audit_selected_articles()
    for r in article_results:
        lines.append(f"- {r}")
    lines.append("")
    
    # ── 汇总 ──
    lines.append("---")
    lines.append("")
    lines.append("## 四、问题汇总与处理优先级")
    lines.append("")
    
    p0_issues = []
    p1_issues = []
    
    for name, file_issues in issues.items():
        for issue in file_issues:
            if "❌" in issue:
                p0_issues.append(f"**{name}**：{issue}")
            elif "🔴" in issue:
                p0_issues.append(f"**{name}**：{issue}")
            elif "⚠️" in issue:
                p1_issues.append(f"**{name}**：{issue}")
    
    lines.append("### 🔴 必须处理（影响系统运行）")
    if p0_issues:
        for i in p0_issues:
            lines.append(f"- {i}")
    else:
        lines.append("- 无")
    lines.append("")
    
    lines.append("### ⚠️ 建议处理（影响生成质量）")
    if p1_issues:
        for i in p1_issues:
            lines.append(f"- {i}")
    else:
        lines.append("- 无")
    lines.append("")
    
    lines.append("---")
    lines.append("")
    lines.append("## 五、下一步操作建议")
    lines.append("")
    lines.append("1. 先处理所有🔴问题")
    lines.append("2. 把有⚠️问题的文件逐个粘贴到Claude Project，由架构师协助分析内容质量")
    lines.append("3. 重点人工核查：模板库中usage=汇报类/方案类/讲话类的条目")
    lines.append("4. 人工核查完成后，回到Claude Project确认知识库就绪，再进入T-001")
    
    return "\n".join(lines)


# ════════════════════════════════════
# 主程序
# ════════════════════════════════════

if __name__ == "__main__":
    print("=" * 50)
    print("公文写作AI助手 - 知识库核查脚本")
    print("=" * 50)
    print(f"项目路径：{PROJECT_ROOT}")
    print("")
    print("正在扫描文件...")
    
    report = generate_report()
    
    # 写入报告文件
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(report)
    
    print(f"\n✅ 核查完成！报告已生成：{OUTPUT_FILE}")
    print("\n发现的主要问题：")
    
    # 控制台简要输出
    for name, file_issues in issues.items():
        has_problem = any("❌" in i or "🔴" in i or "⚠️" in i for i in file_issues)
        if has_problem:
            print(f"\n  【{name}】")
            for issue in file_issues:
                if any(mark in issue for mark in ["❌", "🔴", "⚠️"]):
                    print(f"    {issue}")
    
    print(f"\n完整报告请查看：{OUTPUT_FILE}")
    print("请将 audit_report.md 的内容粘贴到 Claude Project 进行下一步分析。")
