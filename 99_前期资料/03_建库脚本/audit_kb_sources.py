#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
01-05 知识库源文件质量核查脚本（不是 data_prep 转换产物）

核查维度：
  A. 语法合法性 (YAML/JSON)
  B. 文件清单与索引引用一致性
  C. 必要字段完整性（按文件类型定制）
  D. ID 唯一性
  E. 内容长度合理性
  F. 跨文件引用断链
  G. 与文档声明（README/进度报告）的差异

输出：audit_kb_sources_report.md
"""

import json
import yaml
import os
import re
from pathlib import Path
from collections import defaultdict, Counter
from datetime import datetime

PROJECT_ROOT = Path(__file__).parent
OUTPUT_FILE = PROJECT_ROOT / "audit_kb_sources_report.md"

# ─────────────────────────────────────────────
# 检查结果收集器
# ─────────────────────────────────────────────
results = {
    "01_templates": {"errors": [], "warnings": [], "stats": {}},
    "02_rules":     {"errors": [], "warnings": [], "stats": {}},
    "03_dictionary":{"errors": [], "warnings": [], "stats": {}},
    "04_corpus":    {"errors": [], "warnings": [], "stats": {}},
    "05_metadata":  {"errors": [], "warnings": [], "stats": {}},
}

def add_err(mod, msg):  results[mod]["errors"].append(msg)
def add_warn(mod, msg): results[mod]["warnings"].append(msg)
def set_stat(mod, k, v): results[mod]["stats"][k] = v


# ─────────────────────────────────────────────
# 通用工具
# ─────────────────────────────────────────────
def safe_yaml_load(path):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f), None
    except Exception as e:
        return None, str(e)

def safe_json_load(path):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f), None
    except Exception as e:
        return None, str(e)


# ═════════════════════════════════════════════
# 01_templates 核查
# ═════════════════════════════════════════════
def audit_templates():
    mod = "01_templates"
    tpl_dir = PROJECT_ROOT / "01_templates"

    # A. 列出所有实际存在的 JSON 模板
    json_files = sorted(tpl_dir.rglob("*.json"))
    json_files = [f for f in json_files if f.name != "by_usage_index.json"]
    set_stat(mod, "实际存在的 JSON 模板数", len(json_files))

    # B. 检查 by_usage_index.json
    index_path = tpl_dir / "by_usage_index.json"
    if not index_path.exists():
        add_err(mod, "by_usage_index.json 不存在")
        return

    idx, err = safe_json_load(index_path)
    if err:
        add_err(mod, f"by_usage_index.json 解析失败: {err}")
        return

    set_stat(mod, "by_usage_index 声称的模板总数", idx.get("metadata", {}).get("total_templates", 0))

    # 收集索引中所有引用的文件路径
    indexed_paths = set()
    scenarios_count = {}
    for scenario, scen_data in idx.get("scenarios", {}).items():
        count_decl = scen_data.get("count", 0)
        tpls = scen_data.get("templates", [])
        scenarios_count[scenario] = {"declared": count_decl, "actual": len(tpls)}
        for t in tpls:
            indexed_paths.add(t.get("file_path", ""))

    set_stat(mod, "by_usage_index 引用的唯一文件路径数", len(indexed_paths))
    set_stat(mod, "各场景声称数量", scenarios_count)

    # C. 检查索引中的路径是否都存在
    missing_files = []
    existing_indexed = []
    for p in indexed_paths:
        full = tpl_dir / p
        if not full.exists():
            missing_files.append(p)
        else:
            existing_indexed.append(p)

    set_stat(mod, "索引引用但文件缺失数", len(missing_files))
    if missing_files:
        add_err(mod, f"by_usage_index 引用了 {len(missing_files)} 个不存在的模板文件（占索引 {len(indexed_paths)} 个的 {len(missing_files)/len(indexed_paths)*100:.0f}%）")
        for p in missing_files[:10]:
            add_err(mod, f"  缺失: {p}")
        if len(missing_files) > 10:
            add_err(mod, f"  …（还有 {len(missing_files)-10} 个）")

    # D. 检查实际存在的文件是否都在索引中
    actual_rel = set([f.relative_to(tpl_dir).as_posix() for f in json_files])
    orphaned = actual_rel - indexed_paths
    if orphaned:
        add_warn(mod, f"实际存在但未在索引中的模板：{len(orphaned)} 个")
        for p in sorted(orphaned)[:5]:
            add_warn(mod, f"  孤儿: {p}")

    # E. 检查每个 JSON 模板的字段完整性
    empty_system_prompt = 0
    empty_content = 0
    missing_skeleton = 0
    field_stats = defaultdict(int)
    template_ids = []

    for f in json_files:
        data, err = safe_json_load(f)
        if err:
            add_err(mod, f"JSON 解析失败 {f.relative_to(tpl_dir)}: {err}")
            continue

        for k in data.keys():
            field_stats[k] += 1

        # 模板的核心字段
        sp = data.get("system_prompt") or data.get("prompt_system") or ""
        if not sp or (isinstance(sp, str) and not sp.strip()):
            empty_system_prompt += 1

        content = data.get("content") or data.get("prompt_template") or ""
        if not content or (isinstance(content, str) and not content.strip()):
            empty_content += 1

        # 检查骨架字段（A3 批量写入的）
        if "structure_skeleton" not in data:
            missing_skeleton += 1

        tid = data.get("template_id") or data.get("id") or f.stem
        template_ids.append(tid)

    set_stat(mod, "system_prompt 为空", f"{empty_system_prompt} / {len(json_files)}")
    set_stat(mod, "content 字段为空", f"{empty_content} / {len(json_files)}")
    set_stat(mod, "缺失 structure_skeleton 字段", f"{missing_skeleton} / {len(json_files)}")
    set_stat(mod, "字段分布", dict(field_stats))

    if empty_system_prompt > 0:
        add_err(mod, f"system_prompt 为空: {empty_system_prompt}/{len(json_files)} 个模板（占 {empty_system_prompt/len(json_files)*100:.0f}%）")

    if missing_skeleton > 0:
        add_warn(mod, f"缺失 structure_skeleton 字段: {missing_skeleton}/{len(json_files)}（A3 批量写入未覆盖到的模板）")

    # F. ID 重复检查
    dup_ids = [k for k, v in Counter(template_ids).items() if v > 1]
    if dup_ids:
        add_err(mod, f"模板 ID 重复: {dup_ids}")

    # G. 检查 A2 骨架 YAML
    for fname in ["A2_审核草稿_11种文体骨架.yaml", "A2_补充骨架_修订版.yaml"]:
        ypath = tpl_dir / fname
        if not ypath.exists():
            add_err(mod, f"骨架文件不存在: {fname}")
            continue
        # YAML 是多文档的（按 --- 分隔），需要 safe_load_all
        try:
            with open(ypath, "r", encoding="utf-8") as f:
                docs = list(yaml.safe_load_all(f))
            valid_docs = [d for d in docs if d]
            set_stat(mod, f"骨架文件 {fname} 文档数", len(valid_docs))

            for d in valid_docs:
                if not isinstance(d, dict):
                    continue
                dt = d.get("doc_type", "(未知)")
                # 检查骨架必要字段
                for req in ["doc_type", "usage_scene", "word_count_range",
                            "structure_skeleton", "constraints", "quality_checklist"]:
                    if req not in d:
                        add_warn(mod, f"{fname}/{dt}: 缺少字段 {req}")
        except Exception as e:
            add_err(mod, f"{fname} YAML 解析失败: {e}")

    # H. CLAUDE.md 声明的文件是否都存在
    claude_md = PROJECT_ROOT / "CLAUDE.md"
    if claude_md.exists():
        text = claude_md.read_text(encoding="utf-8", errors="replace")
        # 抽取 01_templates 下的引用
        refs = re.findall(r'`(01_templates/[^`]+)`', text)
        for r in refs:
            if not (PROJECT_ROOT / r).exists():
                add_err(mod, f"CLAUDE.md 引用但不存在: {r}")


# ═════════════════════════════════════════════
# 02_rules 核查
# ═════════════════════════════════════════════
def audit_rules():
    mod = "02_rules"
    rul_dir = PROJECT_ROOT / "02_rules"

    yaml_files = sorted(rul_dir.rglob("*.yaml"))
    json_files = sorted(rul_dir.rglob("*.json"))
    md_files = sorted(rul_dir.rglob("*.md"))

    set_stat(mod, "YAML 文件数", len(yaml_files))
    set_stat(mod, "JSON 文件数", len(json_files))
    set_stat(mod, "MD 文件数", len(md_files))

    # A. 每个文件语法核查
    for yf in yaml_files:
        data, err = safe_yaml_load(yf)
        if err:
            add_err(mod, f"YAML 解析失败 {yf.relative_to(rul_dir)}: {err}")

    for jf in json_files:
        data, err = safe_json_load(jf)
        if err:
            add_err(mod, f"JSON 解析失败 {jf.relative_to(rul_dir)}: {err}")

    # B. 重点检查 rules_master.yaml
    master_path = rul_dir / "rules_master.yaml"
    if master_path.exists():
        data, err = safe_yaml_load(master_path)
        if err:
            add_err(mod, f"rules_master.yaml 解析失败: {err}")
        else:
            meta = data.get("metadata", {})
            decl_total = meta.get("total_rules", 0)
            decl_counts = meta.get("rule_counts", {})

            # 统计每个类别下的实际规则数和字段完整性
            actual_counts = {}
            all_ids = []
            missing_fields_count = defaultdict(int)
            empty_summary = 0

            for cat in ["FORMAT", "TERM", "LOGIC", "STYLE", "GENRE"]:
                cat_data = data.get(cat, {})
                rules = cat_data.get("rules", []) or []
                actual_counts[cat] = len(rules)
                for r in rules:
                    rid = r.get("id", "")
                    if rid:
                        all_ids.append(rid)
                    for req in ["id", "title", "importance", "execution", "content_summary"]:
                        if not r.get(req):
                            missing_fields_count[req] += 1
                    if not r.get("content_summary") or not str(r.get("content_summary", "")).strip():
                        empty_summary += 1

            actual_total = sum(actual_counts.values())
            set_stat(mod, "rules_master.yaml 声称规则总数", decl_total)
            set_stat(mod, "rules_master.yaml 实际规则总数", actual_total)
            set_stat(mod, "rules_master.yaml 声称分布", decl_counts)
            set_stat(mod, "rules_master.yaml 实际分布", actual_counts)
            set_stat(mod, "字段缺失统计", dict(missing_fields_count))

            if actual_total != decl_total:
                add_err(mod, f"rules_master.yaml: 声称 {decl_total} 条 vs 实际 {actual_total} 条（差异 {actual_total - decl_total}）")
            for cat in decl_counts:
                if decl_counts[cat] != actual_counts.get(cat, 0):
                    add_warn(mod, f"rules_master.yaml: {cat} 声称 {decl_counts[cat]} vs 实际 {actual_counts.get(cat, 0)}")

            # ID 重复
            dup_ids = [k for k, v in Counter(all_ids).items() if v > 1]
            if dup_ids:
                add_err(mod, f"rules_master.yaml: ID 重复 {len(dup_ids)} 个: {dup_ids[:5]}")

            if empty_summary > 0:
                add_warn(mod, f"rules_master.yaml: content_summary 为空 {empty_summary} 条")

    # C. 检查 book_principles 各文件条目数
    book_dir = rul_dir / "book_principles"
    for bf in sorted(book_dir.glob("*.yaml")):
        data, err = safe_yaml_load(bf)
        if err:
            continue
        if isinstance(data, dict):
            # 顶层 keys 数
            top_keys = list(data.keys())
            # 找规则列表
            rules_count = 0
            for k, v in data.items():
                if isinstance(v, list):
                    rules_count = max(rules_count, len(v))
            set_stat(mod, f"book_principles/{bf.name}", {"top_keys": len(top_keys), "max_list_len": rules_count})


# ═════════════════════════════════════════════
# 03_dictionary 核查
# ═════════════════════════════════════════════
def audit_dictionary():
    mod = "03_dictionary"
    dic_dir = PROJECT_ROOT / "03_dictionary"

    yaml_files = sorted(dic_dir.rglob("*.yaml"))
    set_stat(mod, "YAML 文件数", len(yaml_files))

    all_ids = []
    total_entries = 0
    file_summaries = {}

    for yf in yaml_files:
        data, err = safe_yaml_load(yf)
        rel = yf.relative_to(dic_dir).as_posix()
        if err:
            add_err(mod, f"YAML 解析失败 {rel}: {err}")
            continue

        if data is None:
            add_warn(mod, f"{rel}: 文件为空或无内容")
            continue

        # 统计条目和 ID
        entry_count = 0
        file_ids = []

        if isinstance(data, dict):
            # 可能是嵌套结构，扫描所有列表
            def scan(node):
                nonlocal entry_count
                if isinstance(node, list):
                    for item in node:
                        if isinstance(item, dict):
                            entry_count += 1
                            for id_field in ["id", "ID", "term_id", "entry_id"]:
                                if id_field in item:
                                    file_ids.append((id_field, item[id_field]))
                                    break
                        scan(item)
                elif isinstance(node, dict):
                    for v in node.values():
                        scan(v)
            scan(data)

        elif isinstance(data, list):
            entry_count = len(data)
            for item in data:
                if isinstance(item, dict):
                    for id_field in ["id", "ID", "term_id", "entry_id"]:
                        if id_field in item:
                            file_ids.append((id_field, item[id_field]))
                            break

        total_entries += entry_count
        file_summaries[rel] = {"entries": entry_count, "ids": len(file_ids)}
        all_ids.extend([(rel, idval) for _, idval in file_ids])

    set_stat(mod, "总条目数（扫描所有列表）", total_entries)
    set_stat(mod, "各文件条目数", file_summaries)

    # 跨文件 ID 重复检查
    id_to_files = defaultdict(list)
    for rel, idval in all_ids:
        id_to_files[idval].append(rel)

    cross_dups = {k: v for k, v in id_to_files.items() if len(v) > 1}
    if cross_dups:
        add_warn(mod, f"跨文件出现的相同 ID: {len(cross_dups)} 个")
        for k, v in list(cross_dups.items())[:5]:
            add_warn(mod, f"  ID '{k}' 出现在: {v}")

    # 重点：official_terms_v2.yaml 是否真的有结构化条目（还是被包在 content: | 中的纯文本）
    v2_path = dic_dir / "official_terms_v2.yaml"
    if v2_path.exists():
        data, err = safe_yaml_load(v2_path)
        if data and isinstance(data, dict):
            keys = list(data.keys())
            if keys == ["content"] and isinstance(data.get("content"), str):
                add_err(mod, f"official_terms_v2.yaml: 是纯文本包装在 content: | 中（共 {len(data['content'])} 字符），未结构化为可检索条目 —— 这是已知缺陷（见 今日工作计划 C1 任务）")

    # 检查烟草术语库（5 个文件）
    tobacco_dir = dic_dir / "tobacco_terms"
    if tobacco_dir.exists():
        for tf in sorted(tobacco_dir.glob("*.yaml")):
            data, err = safe_yaml_load(tf)
            if err:
                continue
            top_keys = list(data.keys()) if isinstance(data, dict) else []
            set_stat(mod, f"tobacco_terms/{tf.name}", {"top_keys": top_keys, "size_kb": tf.stat().st_size // 1024})


# ═════════════════════════════════════════════
# 04_corpus 核查
# ═════════════════════════════════════════════
def audit_corpus():
    mod = "04_corpus"
    cor_dir = PROJECT_ROOT / "04_corpus"

    # 顶层文件
    top_files = list(cor_dir.glob("*"))
    set_stat(mod, "顶层文件/目录数", len(top_files))

    # 范文索引核查
    p3_path = cor_dir / "优质范文库(P3).yaml"
    meta_path = cor_dir / "个人历史交付物元数据索引.yaml"
    meta_scored_path = cor_dir / "个人历史交付物元数据索引_评分版.yaml"
    high_val_path = cor_dir / "高价值文件清单.yaml"

    for p in [p3_path, meta_path, meta_scored_path, high_val_path]:
        if not p.exists():
            add_err(mod, f"缺失文件: {p.name}")
            continue
        data, err = safe_yaml_load(p)
        if err:
            add_err(mod, f"YAML 解析失败 {p.name}: {err}")
            continue
        if isinstance(data, list):
            set_stat(mod, f"{p.name} 条目数", len(data))

    # 检查范文索引中的 file_path 是否真实存在
    if p3_path.exists():
        data, _ = safe_yaml_load(p3_path)
        if isinstance(data, list):
            missing_raw = []
            for item in data:
                if isinstance(item, dict):
                    fp = item.get("file_path", "")
                    if fp:
                        full = PROJECT_ROOT / fp
                        if not full.exists():
                            missing_raw.append(fp)
            if missing_raw:
                add_err(mod, f"优质范文库(P3).yaml 中引用的原始文件缺失: {len(missing_raw)} 个")
                for m in missing_raw[:5]:
                    add_err(mod, f"  缺失: {m}")
            else:
                set_stat(mod, "P3 范文原始文件引用", "全部存在")

    # 检查 selected_articles 目录
    sa_dir = cor_dir / "selected_articles"
    if sa_dir.exists():
        md_files = sorted(sa_dir.glob("TA-*.md"))
        idx_files = list(sa_dir.glob("article_index*.json"))
        set_stat(mod, "selected_articles TA-*.md 文件数", len(md_files))
        set_stat(mod, "selected_articles 索引文件数", len(idx_files))

        # 检查索引和文件是否对应
        for idx_file in idx_files:
            if idx_file.name == "article_index.json":
                data, err = safe_json_load(idx_file)
                if not err and isinstance(data, list):
                    set_stat(mod, "article_index.json 索引条目数", len(data))
                    # 检查每个索引条目对应的 md 文件是否存在
                    missing = []
                    for entry in data:
                        if isinstance(entry, dict):
                            aid = entry.get("id") or entry.get("article_id", "")
                            if aid:
                                md_path = sa_dir / f"{aid}.md"
                                if not md_path.exists():
                                    missing.append(aid)
                    if missing:
                        add_err(mod, f"article_index.json 引用但 .md 缺失: {len(missing)} 个")

    # 段落库
    p4_path = cor_dir / "段落库(P4).yaml"
    if p4_path.exists():
        data, err = safe_yaml_load(p4_path)
        if not err and isinstance(data, list):
            set_stat(mod, "段落库(P4).yaml 条目数", len(data))
            # 检查内容长度
            short = sum(1 for x in data if isinstance(x, dict) and len(str(x.get("content", ""))) < 30)
            if short > 0:
                add_warn(mod, f"段落库(P4).yaml: 段落 content 长度 <30 字的 {short} 条")
            # 字段统计
            field_stats = Counter()
            for x in data:
                if isinstance(x, dict):
                    for k in x.keys():
                        field_stats[k] += 1
            set_stat(mod, "段落库 字段分布", dict(field_stats))


# ═════════════════════════════════════════════
# 05_metadata 核查
# ═════════════════════════════════════════════
def audit_metadata():
    mod = "05_metadata"
    md_dir = PROJECT_ROOT / "05_metadata"

    files = list(md_dir.glob("*.json"))
    set_stat(mod, "JSON 文件数", len(files))

    # 读 stats
    stats_path = md_dir / "knowledge_base_stats.json"
    if stats_path.exists():
        data, err = safe_json_load(stats_path)
        if err:
            add_err(mod, f"knowledge_base_stats.json 解析失败: {err}")
        else:
            modules = data.get("modules", {})
            for mname, mdata in modules.items():
                set_stat(mod, f"声称 {mname}", mdata)
            summary = data.get("summary", {})
            set_stat(mod, "声称全库实体数", summary.get("total_core_entities", 0))
            set_stat(mod, "声称就绪度", summary.get("readiness", ""))

    # 检查 cross_library_index.json
    cross_path = md_dir / "cross_library_index.json"
    if cross_path.exists():
        data, err = safe_json_load(cross_path)
        if err:
            add_err(mod, f"cross_library_index.json 解析失败: {err}")
        else:
            set_stat(mod, "cross_library_index 顶层 keys", list(data.keys()) if isinstance(data, dict) else "non-dict")

    # 检查 integration_test_report.json
    test_path = md_dir / "integration_test_report.json"
    if test_path.exists():
        data, err = safe_json_load(test_path)
        if err:
            add_err(mod, f"integration_test_report.json 解析失败: {err}")
        else:
            tests = data.get("tests", []) if isinstance(data, dict) else []
            set_stat(mod, "测试用例数", len(tests))

    # 元数据陈旧度检查（最后更新时间）
    import time
    for f in files:
        mtime = f.stat().st_mtime
        age_days = (time.time() - mtime) / 86400
        if age_days > 60:
            add_warn(mod, f"{f.name} 已 {age_days:.0f} 天未更新（最后修改 {datetime.fromtimestamp(mtime).strftime('%Y-%m-%d')}）")


# ═════════════════════════════════════════════
# 主流程 + 报告生成
# ═════════════════════════════════════════════
def main():
    print("→ 开始扫描 01-05 知识库源文件...")
    audit_templates()
    audit_rules()
    audit_dictionary()
    audit_corpus()
    audit_metadata()

    lines = ["# 01-05 知识库源文件质量核查报告", ""]
    lines.append(f"**生成时间：** {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    lines.append(f"**项目路径：** `{PROJECT_ROOT}`")
    lines.append("")

    # 总览
    total_errors = sum(len(v["errors"]) for v in results.values())
    total_warnings = sum(len(v["warnings"]) for v in results.values())
    lines.append(f"**问题总览：** 🔴 {total_errors} 个错误 ｜ ⚠️ {total_warnings} 个警告")
    lines.append("")
    lines.append("---")
    lines.append("")

    for mod_name in ["01_templates", "02_rules", "03_dictionary", "04_corpus", "05_metadata"]:
        m = results[mod_name]
        lines.append(f"## {mod_name}")
        lines.append("")

        if m["stats"]:
            lines.append("### 统计")
            for k, v in m["stats"].items():
                if isinstance(v, (dict, list)):
                    lines.append(f"- **{k}：** `{json.dumps(v, ensure_ascii=False)}`")
                else:
                    lines.append(f"- **{k}：** {v}")
            lines.append("")

        if m["errors"]:
            lines.append(f"### 🔴 错误（{len(m['errors'])}）")
            for e in m["errors"]:
                lines.append(f"- {e}")
            lines.append("")

        if m["warnings"]:
            lines.append(f"### ⚠️ 警告（{len(m['warnings'])}）")
            for w in m["warnings"]:
                lines.append(f"- {w}")
            lines.append("")

        if not m["errors"] and not m["warnings"]:
            lines.append("### ✅ 无错误无警告")
            lines.append("")

        lines.append("---")
        lines.append("")

    OUTPUT_FILE.write_text("\n".join(lines), encoding="utf-8")
    print(f"→ 报告已生成：{OUTPUT_FILE}")
    print(f"→ 总问题数：🔴 {total_errors} ｜ ⚠️ {total_warnings}")


if __name__ == "__main__":
    main()
