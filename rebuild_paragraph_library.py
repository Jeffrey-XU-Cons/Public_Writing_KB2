#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""段落库重建·第二阶段 — 仅生成裁定表(不写新库)

依据:
  - 04_corpus/段落库_合格标准_v1.0.md
  - 04_corpus/段落库筛查报告.md
输出:
  - 04_corpus/段落库重建裁定表.md
铁律:
  - 仅读 段落库(P4).yaml
  - 仅写 段落库重建裁定表.md
  - 绝不修改/删除/重建段落库本身
"""

import yaml
import re
from pathlib import Path
from collections import defaultdict
from difflib import SequenceMatcher

PROJECT_ROOT = Path(__file__).parent
SRC = PROJECT_ROOT / '04_corpus' / '段落库(P4).yaml'
OUT = PROJECT_ROOT / '04_corpus' / '段落库重建裁定表.md'
NEW_LIB = PROJECT_ROOT / '04_corpus' / '段落库_v2.yaml'
EXECUTE_MODE = '--execute' in __import__('sys').argv

# ─────────────────────────────────────────
# 复用第一阶段的判定函数
# ─────────────────────────────────────────
COVER_KEYWORDS_STRONG = [
    '课题名称', '申报单位', '填报日期', '项目结题', '完成时间',
    '项目负责人', '课题组成员', '项目组', '申请人', '编制单位',
]


def has_pua(text):
    return any(0xE000 <= ord(c) <= 0xF8FF for c in text)


def has_spaced_chars(text):
    return bool(re.search(r'(?:[一-鿿]\s+){3,}[一-鿿]', text))


def has_isolated_page_no(text):
    if re.search(r'-\s*\d+\s*-', text):
        return True
    if re.search(r'(?:^|\n)\s*\d{1,4}\s*(?:$|\n)', text):
        return True
    if re.search(r'第\s*\d+\s*页', text):
        return True
    return False


def has_table_fragment(text):
    if re.search(r'\|[^\n]*\|', text):
        return True
    if re.search(r'\|[-\s:]+\|', text):
        return True
    return False


def has_dots_toc(text):
    if re.search(r'\.{6,}', text):
        return True
    if re.search(r'…{3,}', text):
        return True
    return False


def is_cover_fragment(text):
    strong_hits = sum(1 for k in COVER_KEYWORDS_STRONG if k in text)
    if strong_hits >= 1 and len(text) < 200:
        return True
    has_unit = bool(re.search(r'烟草专卖局|烟草公司|中烟工业', text))
    has_year_month = bool(re.search(r'20\d{2}\s*年\s*\d{1,2}\s*月', text))
    has_team = '项目组' in text or '课题组' in text
    if has_unit and has_year_month and has_team and len(text) < 150:
        return True
    return False


def has_pdf_residue(text):
    return (has_spaced_chars(text) or has_isolated_page_no(text)
            or has_table_fragment(text) or has_pua(text) or has_dots_toc(text))


def is_residue_clearable(text):
    if not has_pdf_residue(text):
        return False
    residue_chars = 0
    for m in re.finditer(r'-\s*\d+\s*-|第\s*\d+\s*页|\d+\s*页', text):
        residue_chars += len(m.group(0))
    for m in re.finditer(r'\|[^\n]*\|', text):
        residue_chars += len(m.group(0))
    for m in re.finditer(r'\.{6,}', text):
        residue_chars += len(m.group(0))
    for m in re.finditer(r'(?:[一-鿿]\s+){3,}[一-鿿]', text):
        residue_chars += len(m.group(0))
    ratio = residue_chars / max(len(text), 1)
    return ratio < 0.15 and len(text) > 80


def is_semantically_broken(text):
    stripped = text.strip()
    if not stripped:
        return True
    if stripped[0] in '。,;:.?!?！）)】」』':
        return True
    leading_conjs = ['坚持', '限制', '但是', '然而', '因此', '所以', '而且', '并且', '或者']
    for c in leading_conjs:
        if stripped.startswith(c + '。') or stripped.startswith('。' + c):
            return True
    bad_endings = ['和', '与', '及', '为', '在', '由', '从', '对', '把', '将', '的']
    last_char = stripped[-1]
    if last_char in bad_endings:
        return True
    if stripped[-1] in '，,；;、' and len(stripped) > 30:
        return True
    return False


def detect_labels(text):
    labels = []
    if is_cover_fragment(text):
        labels.append('封面残片')
    if has_pdf_residue(text):
        labels.append('PDF残渣')
        if is_residue_clearable(text):
            labels.append('残渣可清')
    if is_semantically_broken(text):
        labels.append('语义残缺')
    if not labels:
        labels.append('合格候选')
    return labels


def is_table_sequence_after_clean(text):
    """规则收紧:判断清洗后的文本是否仍为表格行序列(非完整论述)

    特征:
      - 多行以"数字 + 业务诊断/类别字"开头
      - 含 ★ 优先级标记
      - 含"地市级/省级/行业级"分类
      - 完整句子(>=15 字 + 以。或！结尾)极少
    """
    lines = [l.strip() for l in text.split('\n') if l.strip()]
    if len(lines) < 3:
        return False

    # 特征 1: 行首数字序号(如 "18 业务诊断 ...")
    numbered_lines = sum(1 for l in lines if re.match(r'^\d{1,3}\s+[一-鿿]', l))

    # 特征 2: ★ 优先级标记
    star_lines = sum(1 for l in lines if '★' in l)

    # 特征 3: "地市级/省级/行业级" 分类标记
    classifier_lines = sum(1 for l in lines if re.search(r'(地市级|省级|行业级|国家级)', l))

    # 特征 4: 完整句子(>=15字 + 以 。/！/？结尾)
    full_sentences = sum(1 for l in lines if len(l) >= 15 and l[-1] in '。！？')

    table_indicators = numbered_lines + star_lines + classifier_lines

    # 表格指标显著多于完整句子,且占比 ≥40% → 判定为表格序列
    if table_indicators >= len(lines) * 0.4 and table_indicators > full_sentences * 2:
        return True

    # 也判:完整句子极少(0-1)且表格指标存在
    if full_sentences <= 1 and table_indicators >= 3:
        return True

    return False


# ─────────────────────────────────────────
# 残渣清洗器
# ─────────────────────────────────────────
def clean_residue(text):
    """清除字间空格串、孤立页码、目录点线、表格残片"""
    cleaned = text

    # 1. 字间空格串还原: "项 目 报 告" → "项目报告"
    def collapse_spaced(match):
        return re.sub(r'\s+', '', match.group(0))
    cleaned = re.sub(r'(?:[一-鿿]\s+){2,}[一-鿿]', collapse_spaced, cleaned)

    # 2. 孤立页码
    cleaned = re.sub(r'-\s*\d+\s*-', '', cleaned)
    cleaned = re.sub(r'第\s*\d+\s*页[,，]?\s*共\s*\d+\s*页', '', cleaned)
    cleaned = re.sub(r'第\s*\d+\s*页', '', cleaned)

    # 3. 目录点线
    cleaned = re.sub(r'\.{6,}', '', cleaned)
    cleaned = re.sub(r'…{3,}', '', cleaned)

    # 4. 表格行碎片（仅删纯表格行,保留嵌入正文的)
    lines = cleaned.split('\n')
    kept_lines = []
    for line in lines:
        # 纯表格分隔行
        if re.match(r'^\s*\|[-\s:]+\|\s*$', line):
            continue
        # 全是 |...|...|...| 的行
        if re.match(r'^\s*(?:\|[^\n|]*){2,}\|\s*$', line) and len(line) < 100:
            continue
        kept_lines.append(line)
    cleaned = '\n'.join(kept_lines)

    # 5. 行内纯数字行
    cleaned = re.sub(r'(?:^|\n)\s*\d{1,4}\s*(?=\n|$)', '\n', cleaned)

    # 6. 合并多余空行
    cleaned = re.sub(r'\n{3,}', '\n\n', cleaned)

    # 7. 首尾空白
    cleaned = cleaned.strip()

    return cleaned


# ─────────────────────────────────────────
# paragraph_type 重判
# ─────────────────────────────────────────
def has_numeric_density(text):
    if re.search(r'\d{2,}', text):
        return True
    if re.search(r'\d+(\.\d+)?\s*%', text):
        return True
    if re.search(r'\d+\s*[元万亿千百十]', text):
        return True
    if re.search(r'20\d{2}\s*年|\d+\s*月\s*\d+\s*日', text):
        return True
    return False


def suggest_paragraph_type(text, current_type):
    has_num = has_numeric_density(text)
    if current_type == '数据段落' and not has_num:
        if '总之' in text or '综上' in text or '展望' in text:
            return '收尾段', '无任何数字'
        if text.strip().startswith('为') or '目的' in text[:30]:
            return '开头段', '无任何数字'
        return '论述段', '无任何数字'
    if current_type != '数据段落' and has_num:
        nums = re.findall(r'\d+(?:\.\d+)?', text)
        if len(nums) >= 3:
            return '数据段落', f'含 {len(nums)} 个数字'
    return None, None


# ─────────────────────────────────────────
# usage 标签
# ─────────────────────────────────────────
def classify_usage(content, paragraph_type):
    """可改写直用 vs 仅供学结构

    判据(标准第三条):
      - 含具体数据/单位名/项目细节 → 仅供学结构
      - 纯务虚的目的段/方法论/收尾套路 → 可改写直用
      - 拿不准 → 仅供学结构(保守)
    """
    text = content

    # 含具体数字/百分比/金额/年份 → 学结构
    if has_numeric_density(text):
        return '仅供学结构'

    # 含具体单位名(烟草专卖局/中烟工业等)
    if re.search(r'(烟草专卖局|烟草公司|中烟工业|卷烟厂|滤嘴有限|物流中心)', text):
        return '仅供学结构'

    # 含具体省份/市名 + 单位
    if re.search(r'(陕西|河南|湖南|福建|广东|浙江|贵州|云南|重庆|河北|安徽|江苏|山东|湖北|四川)中烟', text):
        return '仅供学结构'

    # 含具体项目名/课题名
    if re.search(r'(项目|课题)[名称编号]', text):
        return '仅供学结构'

    # 收尾套路类
    if paragraph_type in ('结尾段落', '收尾段', '总结段落'):
        if not re.search(r'[一-鿿]{2,4}(局|公司|厂|中心)', text):
            return '可改写直用'

    # 开头务虚的目的段
    if paragraph_type in ('开头段落', '开头段'):
        if text.strip().startswith('为') and not has_numeric_density(text):
            return '可改写直用'

    # 默认保守: 仅供学结构
    return '仅供学结构'


# ─────────────────────────────────────────
# 主流程
# ─────────────────────────────────────────
def main():
    print('Step 1: 读取段落库 ...')
    with open(SRC, 'r', encoding='utf-8') as f:
        data = yaml.safe_load(f)
    assert len(data) == 330, f'条目数应为 330, 实际 {len(data)}'
    print(f'  ✓ 330 条')

    # ──────── 给每条打标签 ────────
    print('Step 2: 给每条打标签 + 决定动作 ...')
    decisions = []
    for i, item in enumerate(data):
        content = str(item.get('content', ''))
        labels = detect_labels(content)

        # 决定动作
        if '封面残片' in labels:
            action = '删除-封面残片'
        elif '语义残缺' in labels:
            action = '删除-语义残缺'
        elif 'PDF残渣' in labels and '残渣可清' not in labels:
            action = '删除-PDF残渣不可清'
        elif '残渣可清' in labels:
            action = '清洗保留'
        else:
            action = '保留'

        decisions.append({
            'index': i,
            'file_title': item.get('file_title', ''),
            'paragraph_type': item.get('paragraph_type', ''),
            'category': item.get('category', ''),
            'file_path': item.get('file_path', ''),
            'content': content,
            'word_count': item.get('word_count', 0),
            'quality_score': item.get('quality_score', ''),
            'labels': labels,
            'action': action,
        })
    print(f'  ✓ 标签 + 动作已分配')

    # ──────── 清洗"残渣可清" + 规则收紧后二次判定 ────────
    print('Step 3: 清洗"残渣可清"(规则收紧:清洗后仍为表格序列改判删除) ...')
    clean_pairs = []
    reclassified_to_delete = []
    for d in decisions:
        if d['action'] == '清洗保留':
            before = d['content']
            after = clean_residue(before)
            # 规则收紧:清洗后仍为表格序列 → 改判删除
            if is_table_sequence_after_clean(after):
                d['action'] = '删除-PDF残渣不可清'
                reclassified_to_delete.append({
                    'index': d['index'],
                    'file_title': d['file_title'],
                    'before': before,
                    'after': after,
                })
            else:
                d['cleaned_content'] = after
                clean_pairs.append({
                    'index': d['index'],
                    'file_title': d['file_title'],
                    'before': before,
                    'after': after,
                })
    print(f'  ✓ 清洗保留 {len(clean_pairs)} 条 | 收紧后改判删除 {len(reclassified_to_delete)} 条')

    # ──────── 重复检测(只在"未标记删除"的条目中找) ────────
    print('Step 4: 重复检测(只在保留候选内找,且只删一字不差) ...')
    survivor_indices = [d['index'] for d in decisions if d['action'] in ('保留', '清洗保留')]

    # 用于"一字不差"比对的文本(strip 后)
    def get_compare_text(idx):
        d = decisions[idx]
        if d['action'] == '清洗保留':
            return d['cleaned_content'].strip()
        return d['content'].strip()

    # 用于"相似度"比对的归一化文本
    def normalize(text):
        return re.sub(r'[\s\W_]+', '', text, flags=re.UNICODE)

    normalized_map = {idx: normalize(get_compare_text(idx)) for idx in survivor_indices}

    duplicate_groups = []
    visited = set()
    for i, idx_a in enumerate(survivor_indices):
        if idx_a in visited:
            continue
        norm_a = normalized_map[idx_a]
        if len(norm_a) < 30:
            continue
        group = [idx_a]
        for idx_b in survivor_indices[i+1:]:
            if idx_b in visited:
                continue
            norm_b = normalized_map[idx_b]
            if len(norm_b) < 30:
                continue
            if abs(len(norm_a) - len(norm_b)) > max(len(norm_a), len(norm_b)) * 0.3:
                continue
            sim = SequenceMatcher(None, norm_a, norm_b).ratio()
            if sim >= 0.85:
                group.append(idx_b)
                visited.add(idx_b)
        if len(group) > 1:
            visited.add(idx_a)
            duplicate_groups.append(group)

    # 对每组判定"一字不差" or "略异"
    group_decisions = []
    for group in duplicate_groups:
        texts = [get_compare_text(idx) for idx in group]
        # 严格"一字不差": 所有 strip 后的文本完全相同
        identical_set = set(texts)
        all_identical = len(identical_set) == 1

        if all_identical:
            # 选 quality_score 最高,同分选 word_count 最大,留 1 删其余
            sorted_group = sorted(
                group,
                key=lambda i: (
                    -_score_to_num(decisions[i]['quality_score']),
                    -decisions[i]['word_count']
                )
            )
            keep_idx = sorted_group[0]
            delete_idxs = sorted_group[1:]
            group_decisions.append({
                'group': group,
                'identical': True,
                'action': '一字不差',
                'keep': keep_idx,
                'delete': delete_idxs,
            })
            # 标记删除
            for idx in delete_idxs:
                decisions[idx]['action'] = '删除-重复(一字不差)'
        else:
            group_decisions.append({
                'group': group,
                'identical': False,
                'action': '略异',
                'keep': group,
                'delete': [],
            })
    print(f'  ✓ {len(duplicate_groups)} 组,其中 {sum(1 for g in group_decisions if g["identical"])} 组一字不差')

    # ──────── type 重判 ────────
    print('Step 5: type 重判 ...')
    type_changes = []
    for d in decisions:
        if not d['action'].startswith('删除'):
            content_for_type = d.get('cleaned_content', d['content'])
            new_type, reason = suggest_paragraph_type(content_for_type, d['paragraph_type'])
            if new_type:
                type_changes.append({
                    'index': d['index'],
                    'file_title': d['file_title'],
                    'original': d['paragraph_type'],
                    'new': new_type,
                    'reason': reason,
                })
                d['new_paragraph_type'] = new_type
            else:
                d['new_paragraph_type'] = d['paragraph_type']
        else:
            d['new_paragraph_type'] = d['paragraph_type']
    print(f'  ✓ 改判 {len(type_changes)} 条')

    # ──────── usage 标签 ────────
    print('Step 6: 打 usage 标签 ...')
    usage_counter = defaultdict(int)
    for d in decisions:
        if not d['action'].startswith('删除'):
            content_for_usage = d.get('cleaned_content', d['content'])
            usage = classify_usage(content_for_usage, d['new_paragraph_type'])
            d['usage'] = usage
            usage_counter[usage] += 1
    print(f'  ✓ usage: {dict(usage_counter)}')

    # ──────── 写裁定表 ────────
    print('Step 7: 生成裁定表 ...')
    delete_records = [d for d in decisions if d['action'].startswith('删除')]
    keep_records = [d for d in decisions if not d['action'].startswith('删除')]

    delete_by_action = defaultdict(list)
    for d in delete_records:
        delete_by_action[d['action']].append(d)

    lines = []
    lines.append('# 段落库重建裁定表')
    lines.append('')
    lines.append('> **生成日期:** 2026-05-22')
    lines.append('> **状态:** 待人工确认 — 确认后才执行 Step 2(写新库 + 归档旧库)')
    lines.append('> **依据:** [段落库_合格标准_v1.0.md](段落库_合格标准_v1.0.md) + [段落库筛查报告.md](段落库筛查报告.md)')
    lines.append('')
    lines.append('---')
    lines.append('')

    # ─── 汇总(放最前面便于扫读) ───
    lines.append('## E. 汇总')
    lines.append('')
    lines.append(f'**原 330 条 → 删除 {len(delete_records)} 条 → 保留 {len(keep_records)} 条**')
    lines.append('')
    lines.append('### 删除分布')
    lines.append('')
    lines.append('| 删除原因 | 条数 |')
    lines.append('|---------|------|')
    for action_name in ['删除-封面残片', '删除-语义残缺', '删除-PDF残渣不可清', '删除-重复(一字不差)']:
        cnt = len(delete_by_action.get(action_name, []))
        lines.append(f'| {action_name} | {cnt} |')
    lines.append(f'| **合计删除** | **{len(delete_records)}** |')
    lines.append('')
    lines.append('### 保留分布')
    lines.append('')
    lines.append('| usage | 条数 |')
    lines.append('|-------|------|')
    for k, v in sorted(usage_counter.items()):
        lines.append(f'| {k} | {v} |')
    lines.append(f'| **合计保留** | **{len(keep_records)}** |')
    lines.append('')
    lines.append('### type 重判')
    lines.append('')
    lines.append(f'采纳 **{len(type_changes)} 条** type 字段改判')
    lines.append('')

    # ─── A. 删除清单 ───
    lines.append('---')
    lines.append('')
    lines.append('## A. 删除清单')
    lines.append('')
    lines.append(f'**共 {len(delete_records)} 条**')
    lines.append('')

    for action_name in ['删除-封面残片', '删除-语义残缺', '删除-PDF残渣不可清', '删除-重复(一字不差)']:
        records = delete_by_action.get(action_name, [])
        if not records:
            continue
        lines.append(f'### {action_name}({len(records)} 条)')
        lines.append('')
        lines.append('| 序号 | 文件来源 | 原 paragraph_type | 前60字 |')
        lines.append('|------|---------|------------------|--------|')
        for d in records:
            preview = d['content'].replace('\n', '⏎').replace('|', '·')[:60]
            title = d['file_title'][:30]
            lines.append(f'| #{d["index"]} | {title} | {d["paragraph_type"]} | `{preview}` |')
        lines.append('')

    # ─── B. 残渣清洗对比 ───
    lines.append('---')
    lines.append('')
    lines.append('## B. 残渣清洗对比清单')
    lines.append('')
    lines.append(f'**共 {len(clean_pairs)} 条** — 清洗前后内容对比')
    lines.append('')
    for cp in clean_pairs:
        lines.append(f'### #{cp["index"]} — {cp["file_title"][:35]}')
        lines.append('')
        lines.append('**清洗前:**')
        lines.append('```')
        lines.append(cp['before'][:500])
        if len(cp['before']) > 500:
            lines.append(f'... (truncated, 原长 {len(cp["before"])} 字)')
        lines.append('```')
        lines.append('')
        lines.append('**清洗后:**')
        lines.append('```')
        lines.append(cp['after'][:500])
        if len(cp['after']) > 500:
            lines.append(f'... (truncated, 现长 {len(cp["after"])} 字)')
        lines.append('```')
        lines.append('')
        lines.append(f'*删减字符数: {len(cp["before"]) - len(cp["after"])}*')
        lines.append('')

    # ─── C. 重复组处理 ───
    lines.append('---')
    lines.append('')
    lines.append('## C. 重复组处理清单')
    lines.append('')
    lines.append(f'**共 {len(group_decisions)} 组** — 仅删一字不差,略异全留')
    lines.append('')

    identical_groups = [g for g in group_decisions if g['identical']]
    slight_groups = [g for g in group_decisions if not g['identical']]

    lines.append(f'### C.1 一字不差(删X留Y)— {len(identical_groups)} 组')
    lines.append('')
    if not identical_groups:
        lines.append('*无*')
    for gi, g in enumerate(identical_groups, 1):
        lines.append(f'**组 {gi}** ({len(g["group"])} 条) — 留 #{g["keep"]},删 {", ".join(f"#{i}" for i in g["delete"])}')
        lines.append('')
        for idx in g['group']:
            d = decisions[idx]
            marker = '✓留' if idx == g['keep'] else '✗删'
            lines.append(f'  - **{marker} #{idx}** | {d["file_title"][:35]} | score=[{d["quality_score"]}] | wc={d["word_count"]}')
        lines.append('')

    lines.append(f'### C.2 略异(全留)— {len(slight_groups)} 组')
    lines.append('')
    if not slight_groups:
        lines.append('*无*')
    for gi, g in enumerate(slight_groups, 1):
        lines.append(f'**组 {gi}** ({len(g["group"])} 条) — 全留')
        lines.append('')
        for idx in g['group']:
            d = decisions[idx]
            lines.append(f'  - #{idx} | {d["file_title"][:35]} | type=[{d["paragraph_type"]}]')
        lines.append('')

    # ─── D. type 重判 ───
    lines.append('---')
    lines.append('')
    lines.append('## D. type 重判清单')
    lines.append('')
    lines.append(f'**共 {len(type_changes)} 条**')
    lines.append('')
    lines.append('| 序号 | 文件来源 | 原 type | 新 type | 判据 |')
    lines.append('|------|---------|---------|---------|------|')
    for t in type_changes:
        lines.append(f'| #{t["index"]} | {t["file_title"][:30]} | {t["original"]} | {t["new"]} | {t["reason"]} |')
    lines.append('')

    # ─── 等待确认 ───
    lines.append('---')
    lines.append('')
    lines.append('## 等待人工确认')
    lines.append('')
    lines.append('请回复以下之一:')
    lines.append('- **「批准重建」** — 按本表执行 Step 2(写 段落库_v2.yaml + 归档旧库)')
    lines.append('- **「批准 + 调整 #X #Y...」** — 调整指定条目的处置后再执行')
    lines.append('- **「不批准」** — 停止任务,保留所有原始文件')
    lines.append('')
    lines.append('在收到明确批准前,不会修改任何原始文件。')

    OUT.write_text('\n'.join(lines), encoding='utf-8')
    print(f'\n裁定表已生成: {OUT}')
    print(f'文件大小: {OUT.stat().st_size} 字节')
    print(f'总行数: {len(lines)}')

    # ──────── Step 2: 写新库(仅 EXECUTE_MODE 触发) ────────
    if EXECUTE_MODE:
        print('\n=== EXECUTE MODE: 写新库 段落库_v2.yaml ===')
        new_entries = []
        type_dist = defaultdict(int)
        for d in decisions:
            if d['action'].startswith('删除'):
                continue
            content_out = d.get('cleaned_content', d['content'])
            entry = {
                'file_title': d['file_title'],
                'paragraph_type': d['new_paragraph_type'],
                'quality_score': d['quality_score'],
                'content': content_out,
                'usage': d['usage'],
                'file_path': d['file_path'],
            }
            new_entries.append(entry)
            type_dist[d['new_paragraph_type']] += 1

        assert len(new_entries) == 200, f'保留数应为 200, 实际 {len(new_entries)}'

        with open(NEW_LIB, 'w', encoding='utf-8') as f:
            yaml.dump(new_entries, f, allow_unicode=True, sort_keys=False,
                      default_flow_style=False, width=1000)
        print(f'✓ 新库已写: {NEW_LIB} ({NEW_LIB.stat().st_size} 字节, {len(new_entries)} 条)')
        print(f'  type 分布: {dict(type_dist)}')


def _score_to_num(score):
    """A/B/C → 数字,用于排序"""
    if isinstance(score, (int, float)):
        return float(score)
    s = str(score).upper().strip()
    return {'A': 3, 'B': 2, 'C': 1}.get(s, 0)


if __name__ == '__main__':
    main()
