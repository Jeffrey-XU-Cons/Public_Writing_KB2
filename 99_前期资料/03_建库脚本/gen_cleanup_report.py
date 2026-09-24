#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""第四步：生成清洗清单报告（等待人工批准）"""

import pickle
from pathlib import Path
from datetime import date

PROJECT_ROOT = Path(__file__).parent
TODAY = date.today().strftime('%Y-%m-%d')
OUT = PROJECT_ROOT / f'_清洗清单_{TODAY}.md'

with open('.scan_result.pkl', 'rb') as f:
    R = pickle.load(f)

gs = R['gs']
pg = R['pg']
tpl = R['tpl']

lines = []
lines.append(f'# 清洗清单报告 — {TODAY}')
lines.append('')
lines.append('> **状态：** 第四步完成 · 等待人工批准后才进入第五步删除')
lines.append('> **本次仅建议删除 🔴 类；⚠️ 类按"模棱两可一律保留"原则默认保留**')
lines.append('')

lines.append('---')
lines.append('')
lines.append('## 第一步备份确认 ✅')
lines.append('')
lines.append('备份目录：`_backup_清洗前_2026-05-22/`')
lines.append('')
lines.append('| 目标 | 原始 | 备份 | 一致性 |')
lines.append('|------|------|------|--------|')
lines.append('| 金句库 P4 | 194512 字节 | 194512 字节 | ✓ |')
lines.append('| 段落库 P4 | 291573 字节 | 291573 字节 | ✓ |')
lines.append('| 01_templates 目录 | 49 文件 | 49 文件 | ✓ |')
lines.append('')

lines.append('---')
lines.append('')
lines.append('## 第二步垃圾特征定义（执行用规则）')
lines.append('')
lines.append('| 类别 | 正则模式 | 说明 |')
lines.append('|------|---------|------|')
lines.append('| 页码 | `第\\s*\\d+\\s*页[,，]\\s*共\\s*\\d+\\s*页` | "第X页,共Y页"组合 |')
lines.append('| 页码 | `第\\s*\\d+\\s*页` | 单独的"第X页" |')
lines.append('| 页码 | `共\\s*\\d+\\s*页` | "共Y页" |')
lines.append('| 页码 | `^\\s*\\d+\\s*$` | 纯数字行 |')
lines.append('| MD 残片 | `##\\s*第\\s*\\d+\\s*页` | "## 第X页" |')
lines.append('| MD 残片 | `^#{1,6}\\s+.+$` | 孤立 # 标题行 |')
lines.append('| MD 残片 | `^---+\\s*$` | --- 分隔符 |')
lines.append('| 表格 | `\\|[-\\s]*\\|` | 表格分隔行 |')
lines.append('| 表格 | `^\\|[^|]+\\|[^|]+\\|` | 多列竖线表格行 |')
lines.append('')
lines.append('**🔴 判定标准（严格收紧版，符合"模棱两可一律保留"）：**')
lines.append('去除所有垃圾片段后，剩余有意义字符（去掉标点空白后）**< 10 字**，才标为 🔴。')
lines.append('')

lines.append('---')
lines.append('')
lines.append('## 第三步扫描总览')
lines.append('')
lines.append('| 库 | 总条目 | ✅ 干净 | ⚠️ 可疑 | 🔴 垃圾（建议删除） |')
lines.append('|------|--------|---------|---------|---------|')
lines.append(f'| 金句库 P4 | {gs["total"]} | {len(gs["clean"])} ({len(gs["clean"])/gs["total"]*100:.0f}%) | {len(gs["suspect"])} ({len(gs["suspect"])/gs["total"]*100:.0f}%) | **{len(gs["trash"])}** ({len(gs["trash"])/gs["total"]*100:.1f}%) |')
lines.append(f'| 段落库 P4 | {pg["total"]} | {len(pg["clean"])} ({len(pg["clean"])/pg["total"]*100:.0f}%) | {len(pg["suspect"])} ({len(pg["suspect"])/pg["total"]*100:.0f}%) | **{len(pg["trash"])}** ({len(pg["trash"])/pg["total"]*100:.1f}%) |')
lines.append(f'| 模板库 | {tpl["total"]} | {len(tpl["clean"])} | {len(tpl["suspect"])}（字段级污染） | **{len(tpl["trash"])}**（模板库不整删） |')
lines.append('')

lines.append('**关键说明：**')
lines.append('- 模板库 🔴 永远为 0，因为每个模板的 `structure_skeleton/constraints/quality_checklist` 三字段质量良好（前面排查已确认），不应整删；模板的 PDF 污染只在 `prompt_template/prompt_system` 字段层面，属字段级清洗，不在本次"整条删除"范围')
lines.append('- 段落库 🔴 为 0 — 之前定性 audit 看到的"表格残片段落"（含「第24期 河南中烟办公室 2024年9月26日」等文档版头）按"模棱两可保留"原则归入 ⚠️ 类（共 9 条命中数≥5 的可疑段落），见下文 ⚠️ 段落库清单')
lines.append('')

# ──────────────────────────────────────────────
# 🔴 类清单
# ──────────────────────────────────────────────
lines.append('---')
lines.append('')
lines.append('## 🔴 类完整清单（**建议本次删除的全部条目**）')
lines.append('')
lines.append(f'**总数：{len(gs["trash"]) + len(pg["trash"]) + len(tpl["trash"])} 条**（金句库 {len(gs["trash"])} + 段落库 {len(pg["trash"])} + 模板库 {len(tpl["trash"])}）')
lines.append('')

lines.append('### 金句库 🔴 （3 条）')
lines.append('')
for r in gs['trash']:
    lines.append(f'#### 条目 #{r["index"]}（长度 {r["length"]} 字，类别 [{r["category"]}]，文件 [{r["file_title"]}]）')
    lines.append('')
    lines.append('原文：')
    lines.append('```')
    lines.append(r['sentence'])
    lines.append('```')
    lines.append('')
    lines.append(f'命中特征：{len(r["hits"])} 个 — ' + ' / '.join(f'{h[1]}' for h in r['hits'][:5]))
    lines.append('')

lines.append('### 段落库 🔴 （0 条）')
lines.append('')
lines.append('**无 — 严格判定下未发现"主体是垃圾"的段落。可疑段落请见 ⚠️ 类清单。**')
lines.append('')

lines.append('### 模板库 🔴 （0 条）')
lines.append('')
lines.append('**无 — 模板库按规则不整删，字段级清洗（清洗 prompt_template 中的页码碎片）属于另一项任务，不在本次"整条删除"范围。**')
lines.append('')

# ──────────────────────────────────────────────
# ⚠️ 类清单 — 金句库
# ──────────────────────────────────────────────
lines.append('---')
lines.append('')
lines.append('## ⚠️ 类完整清单（**默认保留，需人工逐条裁决**）')
lines.append('')

lines.append(f'### 金句库 ⚠️ （{len(gs["suspect"])} 条）')
lines.append('')
lines.append('**分类提示：**')
short_count = sum(1 for r in gs['suspect'] if r['length'] < 8)
contaminated_count = sum(1 for r in gs['suspect'] if r['hits'])
lines.append(f'- 长度 <8 字（不成句）：{short_count} 条')
lines.append(f'- 含垃圾特征但夹杂有用内容：{contaminated_count} 条')
lines.append('')

for r in gs['suspect']:
    sentence_preview = r['sentence'].replace('\n', '⏎')[:200]
    hit_summary = ' / '.join(f'{h[1]}' for h in r['hits'][:3])
    if len(r['hits']) > 3:
        hit_summary += f' (+{len(r["hits"])-3})'
    if not r['hits']:
        hit_summary = '（无命中，仅因长度 < 8 字）'
    lines.append(f'- **#{r["index"]:>3}** [{r["length"]:>3}字] [{r["category"]}] | 命中: {hit_summary}')
    lines.append(f'   `{sentence_preview}`')

# ──────────────────────────────────────────────
# ⚠️ 类清单 — 段落库
# ──────────────────────────────────────────────
lines.append('')
lines.append(f'### 段落库 ⚠️ （{len(pg["suspect"])} 条）')
lines.append('')
short_pg = sum(1 for r in pg['suspect'] if r['length'] < 50)
contaminated_pg = sum(1 for r in pg['suspect'] if r['hits'])
table_heavy = sum(1 for r in pg['suspect'] if len([h for h in r['hits'] if h[0] == 'table']) >= 3)
lines.append(f'**分类提示：**')
lines.append(f'- 长度 <50 字（不连贯段落）：{short_pg} 条')
lines.append(f'- 含垃圾特征但夹杂有用内容：{contaminated_pg} 条')
lines.append(f'- 其中含 ≥3 个表格残片命中（可能是版头/页脚/表格行）：**{table_heavy} 条**，可重点查看')
lines.append('')

for r in pg['suspect']:
    content_preview = r['content'].replace('\n', '⏎')[:180]
    hit_summary = ' / '.join(f'{h[1]}' for h in r['hits'][:3])
    if len(r['hits']) > 3:
        hit_summary += f' (+{len(r["hits"])-3})'
    if not r['hits']:
        hit_summary = '（无命中，仅因长度 < 50 字）'
    lines.append(f'- **#{r["index"]:>3}** [{r["length"]:>4}字] [{r["paragraph_type"]}] [{r["category"]}] | 命中: {hit_summary}')
    lines.append(f'   `{content_preview}`')

# ──────────────────────────────────────────────
# ⚠️ 类清单 — 模板库
# ──────────────────────────────────────────────
lines.append('')
lines.append(f'### 模板库 ⚠️ （{len(tpl["suspect"])} 条字段级污染，不整删）')
lines.append('')
lines.append('**说明：** 这 40 个模板的 `prompt_template`（或 `prompt_system`）字段含 PDF 页码/标题碎片，但模板整体（含 `structure_skeleton/constraints/quality_checklist`）质量良好。不在"整条删除"范围内，建议另起字段级清洗任务。')
lines.append('')

for r in tpl['suspect']:
    fields_polluted = set(h[0] for h in r['all_hits'])
    lines.append(f'- {r["path"]} | doc_type=[{r["doc_type"]}] | 污染字段: {", ".join(sorted(fields_polluted))} | 命中 {len(r["all_hits"])} 处')

# ──────────────────────────────────────────────
# 末尾说明
# ──────────────────────────────────────────────
lines.append('')
lines.append('---')
lines.append('')
lines.append('## 一句话说明')
lines.append('')
lines.append(f'**本次建议删除的只有 🔴 类共 {len(gs["trash"]) + len(pg["trash"]) + len(tpl["trash"])} 条**（仅金句库 3 条），')
lines.append(f'⚠️ 类共 **{len(gs["suspect"]) + len(pg["suspect"]) + len(tpl["suspect"])} 条**默认保留，等待人工裁决。')
lines.append('')
lines.append('---')
lines.append('')
lines.append('## 等待批准')
lines.append('')
lines.append('请回复以下之一：')
lines.append('')
lines.append('- **「批准清洗」** — 执行第五步，删除 🔴 类 3 条金句')
lines.append('- **「批准 + 追加 #X #Y #Z...」** — 在 🔴 之外，再删除指定的 ⚠️ 条目编号（请明确指明库名 + 编号）')
lines.append('- **「不批准」/ 「重新分类」** — 调整判定标准或停止任务')
lines.append('')
lines.append('在收到明确批准前，不会删除或修改任何原始文件。')

# 写入
OUT.write_text('\n'.join(lines), encoding='utf-8')
print(f'报告已生成: {OUT}')
print(f'文件大小: {OUT.stat().st_size} 字节')
print(f'总行数: {len(lines)}')
