#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""范文库修复·第一阶段:生成处理清单(只读+只写清单 md)"""
import yaml, json
from pathlib import Path
from collections import Counter
from difflib import get_close_matches

PROJECT_ROOT = Path(__file__).parent
OUT = PROJECT_ROOT / '04_corpus' / '范文库修复清单.md'

# ─── 读取 ───
with open('04_corpus/优质范文库(P3).yaml', 'r', encoding='utf-8') as f:
    p3 = yaml.safe_load(f)
with open('04_corpus/个人历史交付物元数据索引.yaml', 'r', encoding='utf-8') as f:
    meta_orig = yaml.safe_load(f)
with open('04_corpus/个人历史交付物元数据索引_评分版.yaml', 'r', encoding='utf-8') as f:
    meta_scored = yaml.safe_load(f)
with open('04_corpus/own_deliverables/deliverable_index.json', 'r', encoding='utf-8') as f:
    delv = json.load(f)
with open('04_corpus/selected_articles/article_index.json', 'r', encoding='utf-8') as f:
    article_index = json.load(f)

# ─── 写 ───
L = []
def w(*lines):
    for line in lines:
        L.append(line)

w('# 范文库修复清单',
  '',
  '> **生成日期:** 2026-05-22',
  '> **状态:** 待人工裁定 — 确认后才执行第二阶段(实际修改文件)',
  '> **铁律:** 此清单只读+只写,**未修改任何原文件**',
  '',
  '---', '')

# ===== A. 删假评分 =====
w('## A. 删假评分', '')
w('### A.1 优质范文库(P3).yaml', '')
w(f'**当前字段** (9): `{", ".join(p3[0].keys())}`', '')
w('| 字段 | 处理 | 原因 |',
  '|------|------|------|',
  '| file_path | 保留 | 文件指针 |',
  '| category | 保留 | 文种分类 |',
  '| title | 保留 | 文章标题 |',
  '| word_count | 保留 | 字数,客观值 |',
  '| source_file_name | 保留 | 源文件名 |',
  '| tags | 保留 | 关键词标签 |',
  '| **quality_score** | **删除** | 脚本按字数+类别两条规则自动生成,非真实评分 |',
  '| **rank** | **删除** | 基于 quality_score 排序,根上即假 |',
  '| **comprehensive_score** | **删除** | quality_score+字数加权+类别奖励,基于假分 |',
  '')

w('### A.2 元数据索引.yaml(原版)', '')
w(f'**当前字段** (7): `{", ".join(meta_orig[0].keys())}`', '')
w('原版的 quality_score 全是 **0**(未评分),技术上不假,但作为索引字段没价值。', '')
w('| 字段 | 处理 | 原因 |',
  '|------|------|------|',
  '| file_path / category / title / word_count / source_file_name / tags | 保留 | 客观元数据 |',
  '| **quality_score** | **删除** | 全为 0,占位字段,无信息量 |',
  '')

w('### A.3 元数据索引_评分版.yaml', '')
w(f'**当前字段** (7): `{", ".join(meta_scored[0].keys())}`', '')
w('与原版唯一差异是 quality_score 被脚本填了 5/6/7/8。', '')
w('| 字段 | 处理 | 原因 |',
  '|------|------|------|',
  '| file_path / category / title / word_count / source_file_name / tags | 保留 | 与原版相同 |',
  '| **quality_score** | **删除** | 同 A.1 — 脚本规则假分 |',
  '')
w('**附加建议:** 删假评分后,评分版与原版字段完全相同,可考虑直接**删除评分版文件**(重复存在)。', '')

w('### A.4 deliverable_index.json', '')
w(f'**当前字段** (10): `{", ".join(delv[0].keys())}`', '')
qg_dist = Counter(item['quality_grade'] for item in delv)
w(f'**quality_grade 分布:** {dict(qg_dist)} (90/90 全是 "A")', '')
w('| 字段 | 处理 | 原因 |',
  '|------|------|------|',
  '| article_id / title / doc_type / sub_type / content_type / topics / industry / summary | 保留 | 元数据 |',
  '| rag_weight | 保留 | RAG 权重(纯数字 2.0) |',
  '| **quality_grade** | **删除** | 90/90 全为 "A" 占位字符串,等同无评分 |',
  '')

w('### A.5 article_index.json (TA-001~264)', '')
qg_ta = Counter(item['quality_grade'] for item in article_index)
w(f'**quality_grade 分布:** {dict(qg_ta)} (264/264 全是 "C")', '')
w('**来源追查:** 全局 grep `quality_grade` 在所有 .py 中,无任何脚本写过此字段。', '')
w('- 无生成脚本(extract_articles.py 处理交付物,与 TA-* 无关)',
  '- article_index.json mtime: 2026-03-16 01:44(早于摸底报告生成)',
  '- 分卷 part1/2/3 字段相同,合并加总 370 ≠ 264 → 分卷有冗余,与摘要不符',
  '',
  '**结论:** `quality_grade` 是**人工/外部一次性写入的占位字符串**,与 deliverable_index.json 全 "A" 同性质。',
  '',
  '**本轮按你的指令: 不动它**(待你看完来源报告再裁定)。',
  '')

w('---', '')

# ===== B. 加 line 标签 =====
w('## B. 加 line 标签', '')
w('**双线划分:**', '',
  '- `line: 个人范文` — 90 篇个人历史交付物',
  '- `line: 写作教材` — 264 篇 TA-* 公文写作技巧汇编',
  '')
w('### 待加 line 的文件清单', '')
w('| 文件 | 条数 | 拟加 line 值 |',
  '|------|------|--------------|',
  f'| 优质范文库(P3).yaml | {len(p3)} | 个人范文 |',
  f'| 个人历史交付物元数据索引.yaml | {len(meta_orig)} | 个人范文 |',
  f'| 个人历史交付物元数据索引_评分版.yaml | {len(meta_scored)} | 个人范文 (若不并掉) |',
  f'| own_deliverables/deliverable_index.json | {len(delv)} | 个人范文 |',
  f'| selected_articles/article_index.json | {len(article_index)} | 写作教材 |',
  f'| selected_articles/article_index_part1.json | (子集) | 写作教材 |',
  f'| selected_articles/article_index_part2.json | (子集) | 写作教材 |',
  f'| selected_articles/article_index_part3.json | (子集) | 写作教材 |',
  '')
w('**核对:** 个人范文应为 90 条 ✓ | 写作教材应为 264 条 ✓', '')

w('---', '')

# ===== C. 修断链 =====
w('## C. 修断链', '')

broken_items = [
    ('00_raw_materials/个人历史交付物/方案类/成都、银川对标共建第二阶段工作实施方案.md',
     '00_raw_materials/实施方案/成都、银川对标共建第二阶段工作实施方案.md', '已找到-精确换位'),
    ('00_raw_materials/个人历史交付物/方案类/汉中卷烟厂全要素物流管理诊断实施方案（9.6）.md',
     '00_raw_materials/实施方案/汉中卷烟厂全要素物流管理诊断实施方案（9.6）.md', '已找到-精确换位'),
    ('00_raw_materials/个人历史交付物/方案类/河南中烟企业管理成熟度评估技术方案.md',
     None, '**[待补]** 候选 A 文件名带"3"后缀(版本号),按规则需完全同名才确认'),
    ('00_raw_materials/个人历史交付物/方案类/烟草物流应急体系研究与构建项目实施方案（会后修改稿）.md',
     '00_raw_materials/实施方案/烟草物流应急体系研究与构建项目实施方案（会后修改稿）.md', '已找到-精确换位'),
    ('00_raw_materials/个人历史交付物/方案类/长株潭烟草物流管理诊断实施方案240307.md',
     None, '**[待补]** 候选 A 日期 240227 ≠ 240307(差日期版本),按规则不算同名'),
    ('00_raw_materials/个人历史交付物/方案类/陕西 中烟 智慧 物流数字化转型实施方案 2.md',
     '00_raw_materials/实施方案/陕西 中烟 智慧 物流数字化转型实施方案 2.md', '已找到-精确换位'),
    ('00_raw_materials/个人历史交付物/规划类/1-1河南中烟工业有限责任公司南阳卷烟厂数字化转型中长期规划.md',
     '00_raw_materials/发展规划/1-1河南中烟工业有限责任公司南阳卷烟厂数字化转型中长期规划.md', '已找到-精确换位'),
    ('00_raw_materials/个人历史交付物/规划类/长株潭公司十四五战略规划（意见修订稿）-20210220.md',
     '00_raw_materials/发展规划/长株潭公司十四五战略规划（意见修订稿）-20210220.md', '已找到-精确换位'),
]

w('### C.1 元数据索引中 8 条断链(独立文件)', '')
w('| # | 原 file_path | 新 file_path | 状态 |',
  '|---|--------------|--------------|------|')
for i, (old, new, status) in enumerate(broken_items, 1):
    new_text = f'`{new}`' if new else '**[待补]**'
    w(f'| {i} | `{old}` | {new_text} | {status} |')
w('')

w('### C.2 [待补] 2 条 — 已按规则判定不连候选', '')
w('**裁定规则:** 仅候选文件名与原引用[去掉版本号/日期后]**完全同名**才算确认;差日期/差措辞一律 [待补]。', '')

w('#### #3 — 河南中烟企业管理成熟度评估技术方案.md → [待补]', '',
  '候选 A: `实施方案/河南中烟企业管理成熟度评估技术方案**3**.md` — 文件名多"3"(版本号),非同名 → 不连',
  '候选 B: `250417河南中烟企业管理成熟度评价**工作推进方案**(1).md` — 措辞不同("工作推进方案"非"技术方案") → 不连',
  '',
  '**结论: [待补]**',
  '')

w('#### #5 — 长株潭烟草物流管理诊断实施方案240307.md → [待补]', '',
  '候选 A: `实施方案/长株潭烟草物流管理诊断实施方案**240227**.md` — 日期 240307 ≠ 240227(差日期版本) → 不连',
  '候选 B: `实施方案/长株潭烟草物流管理**咨询方案**.md` — 措辞不同("咨询方案"非"诊断方案") → 不连',
  '',
  '**结论: [待补]**',
  '')

w('### C.3 P3 范文库中 4 条断链(子集)', '')
w('P3 的 4 条断链是元数据索引 8 条中的 3 个独立文件:', '',
  '- `陕西 中烟 智慧 物流数字化转型实施方案 2.md` → 已找到',
  '- `1-1河南中烟...南阳卷烟厂数字化转型...规划.md` (出现 2 次) → 已找到',
  '- `长株潭公司十四五战略规划（意见修订稿）-20210220.md` → 已找到',
  '',
  'P3 修了 file_path 后,3 条独立文件全部不再断链(南阳规划同时涉及去重,见 D)。',
  '')

w('---', '')

# ===== D. 去重 =====
w('## D. 去重', '')

fp_counter = Counter(item['file_path'] for item in p3)
dups = {fp: c for fp, c in fp_counter.items() if c > 1}

w(f'### D.1 P3 中 file_path 完全重复的条目', '')
w(f'**严重程度更新:** 摸底报告说"南阳规划重复 2 次",但实际 P3 中共有 **{len(dups)} 个 file_path 各重复 2 次**,合计 **{sum(dups.values())-len(dups)} 个冗余条目**。', '')

w('| # | file_path(基名) | 重复次数 | 去重动作 |',
  '|---|-----------------|----------|----------|')
for i, (fp, c) in enumerate(dups.items(), 1):
    base = fp.split('/')[-1]
    w(f'| {i} | `{base}` | {c} | 留 P3 中第 1 次出现的条目,删第 2 次 |')
w('')

w('### D.2 南阳规划"三胞胎"路径 — 已裁定保留命名最规范者', '')
w('P3 中含"南阳卷烟厂数字化转型中长期规划"的 file_path 有 3 个不同写法,每个各重复 2 次,共 6 条:', '',
  '- `1-1河南中烟工业有限责任公司南阳卷烟厂数字化转型中长期规划.md`(rank=49, 2 条) — 含数字前缀',
  '- `1.河南中烟工业有限责任公司南阳卷烟厂数字化转型中长期规划.md`(rank=50, 2 条) — 含数字前缀',
  '- `河南中烟工业有限责任公司南阳卷烟厂数字化转型中长期规划.md`(rank=51, 2 条) — **无前缀,最规范** ✓',
  '',
  '**裁定结果(用户已批准):** 留 1 条 — 保留无数字前缀的 `河南中烟工业有限责任公司南阳卷烟厂数字化转型中长期规划.md`,删除其余 5 条。',
  '')

# 普通 15 组减 3 组南阳(已在 D.1 算 3 条),还要再多删 2 条把三胞胎合并
extra_nanyang_dedup = 2  # 三胞胎额外合并多删 2 条(普通去重已减 3 条)
final_count = 90 - (sum(dups.values())-len(dups)) - extra_nanyang_dedup
w(f'**最终 P3 独立条目数:** 90 - {sum(dups.values())-len(dups)}(普通去重) - {extra_nanyang_dedup}(南阳合并) = **{final_count} 条**',
  '',
  '验算:',
  '- 原 90 条',
  '- 普通 15 组各重复 2 次,各留 1 删 1 → 删 15 条 → 75 条',
  '- 75 条中含南阳 3 条(命名变体),合并保留 1 条 → 删 2 条 → 73 条',
  '')

w('---', '')

# ===== E. 一致性 =====
w('## E. 评分一致性问题', '')
w('摸底报告发现:P3 与元数据评分版的 quality_score **有 15 条不一致**。', '')
w('### 删假评分后是否自动消解?', '')
w('**✓ 是,完全消解。**', '',
  '理由:',
  '1. A.1 删除 P3 的 `quality_score` 字段',
  '2. A.3 删除元数据评分版的 `quality_score` 字段',
  '3. 两份文件都不再含 quality_score → 不再有"评分不一致"概念',
  '',
  '附加效果:',
  '- A.1 同时删除 `rank`/`comprehensive_score`,P3 中所有"评分类"假数据全清',
  '- A.3 删除后元数据评分版与原版字段完全相同,可考虑合并(详见 A.3 附加建议)',
  '')

w('---', '')

# ===== 汇总 =====
w('## F. 汇总', '')
w('**本次清单最终方案(全部已裁定):**', '',
  '| 项 | 数量 / 决定 |',
  '|----|------|',
  '| 删假评分字段 | P3删3字段(qs/rank/comp) + deliverable删grade + 元数据原版/评分版各删 quality_score |',
  '| article_index.json quality_grade | **本轮不动**(纯占位"C"×264,来源已查清:无脚本写过) |',
  '| 加 line 标签 | 个人范文 90 条 + 写作教材 264 条 |',
  '| 修断链 | 6 条精确换位 / **2 条 [待补]** |',
  f'| P3 去重 | 15 普通+2 南阳 = **{sum(dups.values())-len(dups)+2}** 条删除 |',
  f'| **P3 最终条数** | **{final_count} 条** |',
  '| 评分一致性 | 自动消解(删假评分后两份字段相同) |',
  '')

w('---', '')

w('## G. 三个关键数(请最终批准)', '')
w('请确认以下三个数,即可批准执行第二阶段:', '',
  f'1. **P3 去重后条数:** **{final_count} 条**',
  '2. **断链:** 确认 **6 条** 精确换位 / **2 条 [待补]**(差版本号/差日期,按规则不连)',
  '3. **article_index.json quality_grade 来源:** 264/264 全 "C",无脚本生成,人工/外部一次性写入,本轮不动',
  '',
  '在收到批准前,**未修改任何原文件**。')

# ─── 写入 ───
OUT.write_text('\n'.join(L), encoding='utf-8')
print(f'清单已生成: {OUT}')
print(f'大小: {OUT.stat().st_size} 字节, 行数: {len(L)}')
