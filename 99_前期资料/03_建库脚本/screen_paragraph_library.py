#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""段落库筛查·第一阶段（只读，不改不删不重建）

输入: 04_corpus/段落库(P4).yaml
输出: 04_corpus/段落库筛查报告.md（供人工裁定）

按《段落库_合格标准_v1.0.md 第三条》打候选废标签:
  [封面残片] / [PDF残渣] / [残渣可清] / [语义残缺] / [合格候选]
再做近似重复检测、paragraph_type 重判建议。

铁律: 只读 + 只写报告 md, 不动 段落库(P4).yaml。
"""

import yaml
import re
from pathlib import Path
from collections import defaultdict
from difflib import SequenceMatcher

PROJECT_ROOT = Path(__file__).parent
SRC = PROJECT_ROOT / '04_corpus' / '段落库(P4).yaml'
OUT = PROJECT_ROOT / '04_corpus' / '段落库筛查报告.md'

# 必备字段
REQUIRED_FIELDS = {'file_title', 'category', 'file_path', 'paragraph_type',
                   'paragraph_index', 'content', 'word_count', 'quality_score'}

# ────────────────────────────────────────────────
# Step 1: 读取并校验
# ────────────────────────────────────────────────
def load_and_validate():
    with open(SRC, 'r', encoding='utf-8') as f:
        data = yaml.safe_load(f)
    if not isinstance(data, list):
        raise ValueError(f'根类型应为 list，实际为 {type(data).__name__}')
    n = len(data)
    if n != 330:
        raise ValueError(f'条目数应为 330，实际 {n}')
    # 抽查字段
    sample = data[0]
    missing = REQUIRED_FIELDS - set(sample.keys())
    if missing:
        raise ValueError(f'字段缺失: {missing}')
    return data


# ────────────────────────────────────────────────
# Step 2: 候选废标签
# ────────────────────────────────────────────────

# 封面残片关键词组合（出现 ≥2 个，或单独出现"申报单位/课题名称/项目结题/填报日期"等）
COVER_KEYWORDS_STRONG = [
    '课题名称', '申报单位', '填报日期', '项目结题', '完成时间',
    '项目负责人', '课题组成员', '项目组', '申请人', '编制单位',
]
COVER_KEYWORDS_WEAK = [
    '报告', '项目', '汇编', '诊断报告', '工作汇报', '项目建议书',
    '年', '月', '日',
]

def has_pua(text):
    """Private Use Area characters U+E000–U+F8FF"""
    return any(0xE000 <= ord(c) <= 0xF8FF for c in text)


def has_spaced_chars(text):
    """字间空格串: 如 '项 目 报 告' — 连续3个以上单字符+空格"""
    return bool(re.search(r'(?:[一-鿿]\s+){3,}[一-鿿]', text))


def has_isolated_page_no(text):
    """孤立页码: - 16 - / \\n28\\n / 第X页"""
    if re.search(r'-\s*\d+\s*-', text):
        return True
    if re.search(r'(?:^|\n)\s*\d{1,4}\s*(?:$|\n)', text):
        return True
    if re.search(r'第\s*\d+\s*页', text):
        return True
    return False


def has_table_fragment(text):
    """表格行碎片: |...|, 或连续无标点短句堆叠"""
    if re.search(r'\|[^\n]*\|', text):
        return True
    # 表格分隔行 |---|
    if re.search(r'\|[-\s:]+\|', text):
        return True
    return False


def has_dots_toc(text):
    """目录点线: 连续 6 个以上 . 或 …"""
    if re.search(r'\.{6,}', text):
        return True
    if re.search(r'…{3,}', text):
        return True
    return False


def is_cover_fragment(text):
    """封面残片判定"""
    # 短文本（<80 字）+ 命中强关键词 ≥1 个
    strong_hits = sum(1 for k in COVER_KEYWORDS_STRONG if k in text)
    if strong_hits >= 1 and len(text) < 200:
        return True
    # 含"XX烟草专卖局(公司)" + "项目组" + 年月日 → 封面
    has_unit = bool(re.search(r'烟草专卖局|烟草公司|中烟工业', text))
    has_year_month = bool(re.search(r'20\d{2}\s*年\s*\d{1,2}\s*月', text))
    has_team = '项目组' in text or '课题组' in text
    if has_unit and has_year_month and has_team and len(text) < 150:
        return True
    return False


def has_pdf_residue(text):
    """PDF 残渣综合判定"""
    return (has_spaced_chars(text) or has_isolated_page_no(text)
            or has_table_fragment(text) or has_pua(text) or has_dots_toc(text))


def is_residue_clearable(text):
    """残渣可清: 主体是完整论述，仅首尾带残渣
    判据: 残渣字符占比 < 15% 且主体长度 > 80 字"""
    if not has_pdf_residue(text):
        return False
    residue_chars = 0
    # 估算页码碎片字符
    for m in re.finditer(r'-\s*\d+\s*-|第\s*\d+\s*页|\d+\s*页', text):
        residue_chars += len(m.group(0))
    for m in re.finditer(r'\|[^\n]*\|', text):
        residue_chars += len(m.group(0))
    for m in re.finditer(r'\.{6,}', text):
        residue_chars += len(m.group(0))
    # 字间空格残渣较难精确切，用粗估
    for m in re.finditer(r'(?:[一-鿿]\s+){3,}[一-鿿]', text):
        residue_chars += len(m.group(0))
    ratio = residue_chars / max(len(text), 1)
    return ratio < 0.15 and len(text) > 80


def is_semantically_broken(text):
    """语义残缺: 首字即标点/连接词 / 结尾断半句"""
    stripped = text.strip()
    if not stripped:
        return True
    # 首字即标点
    if stripped[0] in '。，；：、,;:.?!?！）)】」』':
        return True
    # 首字即不成句的连接词
    leading_conjs = ['坚持', '限制', '但是', '然而', '因此', '所以', '而且', '并且', '或者']
    # 仅当文本极短或紧跟标点时算残缺
    for c in leading_conjs:
        if stripped.startswith(c + '。') or stripped.startswith('。' + c):
            return True
    # 结尾断半句: 以连词/动词残留收尾
    bad_endings = ['和', '与', '及', '为', '在', '由', '从', '对', '把', '将', '的']
    last_char = stripped[-1]
    if last_char in bad_endings:
        return True
    # 末尾以逗号/分号断尾（非完整句号收尾），且长度>50
    if stripped[-1] in '，,；;、' and len(stripped) > 30:
        return True
    return False


def detect_labels(text):
    """返回所有命中标签的列表"""
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


# ────────────────────────────────────────────────
# Step 3: 近似重复检测
# ────────────────────────────────────────────────
def normalize_for_dedup(text):
    """去除空白和标点用于比较"""
    return re.sub(r'[\s\W_]+', '', text, flags=re.UNICODE)


def find_duplicate_groups(data, threshold=0.85):
    """成组列出近似重复条目"""
    n = len(data)
    normalized = [normalize_for_dedup(item['content']) for item in data]

    visited = set()
    groups = []

    for i in range(n):
        if i in visited:
            continue
        if len(normalized[i]) < 30:  # 太短的不参与去重比对
            continue
        group = [i]
        for j in range(i + 1, n):
            if j in visited:
                continue
            if len(normalized[j]) < 30:
                continue
            # 长度差距过大跳过
            if abs(len(normalized[i]) - len(normalized[j])) > max(len(normalized[i]), len(normalized[j])) * 0.3:
                continue
            sim = SequenceMatcher(None, normalized[i], normalized[j]).ratio()
            if sim >= threshold:
                group.append(j)
                visited.add(j)
        if len(group) > 1:
            visited.add(i)
            groups.append(group)

    return groups, normalized


def group_similarity(indices, normalized):
    """计算组内最低相似度 + 是否全部一字不差"""
    if len(indices) < 2:
        return 1.0, True
    base = normalized[indices[0]]
    min_sim = 1.0
    all_identical = True
    for idx in indices[1:]:
        sim = SequenceMatcher(None, base, normalized[idx]).ratio()
        min_sim = min(min_sim, sim)
        if normalized[idx] != base:
            all_identical = False
    return min_sim, all_identical


# ────────────────────────────────────────────────
# Step 4: paragraph_type 重判建议
# ────────────────────────────────────────────────
def has_numeric_density(text):
    """是否含具体数字/指标/金额/百分比/日期"""
    # 数字（≥2位数）
    if re.search(r'\d{2,}', text):
        return True
    # 百分比
    if re.search(r'\d+(\.\d+)?\s*%', text):
        return True
    # 金额单位
    if re.search(r'\d+\s*[元万亿千百十]', text):
        return True
    # 日期
    if re.search(r'20\d{2}\s*年|\d+\s*月\s*\d+\s*日', text):
        return True
    return False


def suggest_paragraph_type(text, current_type):
    """重判建议"""
    has_num = has_numeric_density(text)
    if current_type == '数据段落' and not has_num:
        # 推断新类型
        if '总之' in text or '综上' in text or '展望' in text:
            return '收尾段', '无任何数字'
        if text.strip().startswith('为') or '目的' in text[:30]:
            return '开头段', '无任何数字'
        return '论述段', '无任何数字'
    if current_type != '数据段落' and has_num:
        # 数字密集但未标数据段
        nums = re.findall(r'\d+(?:\.\d+)?', text)
        if len(nums) >= 3:
            return '数据段落', f'含 {len(nums)} 个数字'
    return None, None


# ────────────────────────────────────────────────
# 主流程
# ────────────────────────────────────────────────
def main():
    print('Step 1: 读取段落库 ...')
    data = load_and_validate()
    print(f'  ✓ 330 条 + 字段齐全')

    print('Step 2: 候选筛查 ...')
    label_records = []
    label_counter = defaultdict(int)
    for i, item in enumerate(data):
        content = str(item.get('content', ''))
        labels = detect_labels(content)
        label_records.append({
            'index': i,
            'file_title': item.get('file_title', ''),
            'paragraph_type': item.get('paragraph_type', ''),
            'category': item.get('category', ''),
            'labels': labels,
            'content': content,
            'word_count': item.get('word_count', 0),
            'quality_score': item.get('quality_score', ''),
        })
        for lb in labels:
            label_counter[lb] += 1
    print(f'  ✓ 标签计数: {dict(label_counter)}')

    print('Step 3: 近似重复检测 ...')
    groups, normalized = find_duplicate_groups(data, threshold=0.85)
    print(f'  ✓ 找到 {len(groups)} 个相似组')

    print('Step 4: paragraph_type 重判建议 ...')
    type_suggestions = []
    for i, item in enumerate(data):
        content = str(item.get('content', ''))
        current = item.get('paragraph_type', '')
        new_type, reason = suggest_paragraph_type(content, current)
        if new_type:
            type_suggestions.append({
                'index': i,
                'file_title': item.get('file_title', ''),
                'current_type': current,
                'suggested_type': new_type,
                'reason': reason,
            })
    print(f'  ✓ 建议重判 {len(type_suggestions)} 条')

    print('Step 5: 生成报告 ...')
    lines = []
    lines.append('# 段落库筛查报告')
    lines.append('')
    lines.append('> **执行日期:** 2026-05-22')
    lines.append('> **执行模式:** 只读 — 未修改/删除/重建任何文件')
    lines.append('> **依据:** [段落库_合格标准_v1.0.md](段落库_合格标准_v1.0.md)')
    lines.append('> **数据源:** `04_corpus/段落库(P4).yaml`(330 条)')
    lines.append('')
    lines.append('---')
    lines.append('')

    # ─────── 1. 总览表 ───────
    lines.append('## 1. 总览表')
    lines.append('')
    lines.append('| 标签 | 条数 | 占比 |')
    lines.append('|------|------|------|')
    total = len(data)
    for lb in ['合格候选', '封面残片', 'PDF残渣', '残渣可清', '语义残缺']:
        cnt = label_counter.get(lb, 0)
        pct = cnt / total * 100
        lines.append(f'| [{lb}] | {cnt} | {pct:.1f}% |')
    lines.append('')
    lines.append('**说明:** 一条可同时命中多个标签(如「封面残片」+「PDF残渣」),所以列加总会大于 330。')
    lines.append('')

    # 重叠统计
    only_clean = sum(1 for r in label_records if r['labels'] == ['合格候选'])
    only_trash = sum(1 for r in label_records if '合格候选' not in r['labels'])
    lines.append(f'- **纯合格候选**(仅命中"合格候选"): **{only_clean}** 条({only_clean/total*100:.1f}%)')
    lines.append(f'- **命中任意废标签**: **{only_trash}** 条({only_trash/total*100:.1f}%)')
    lines.append('')

    # ─────── 2. 废候选清单 ───────
    lines.append('---')
    lines.append('')
    lines.append('## 2. 废候选清单(命中任意废标签)')
    lines.append('')
    trash_records = [r for r in label_records if '合格候选' not in r['labels']]
    lines.append(f'**共 {len(trash_records)} 条**')
    lines.append('')
    lines.append('| 序号 | 文件来源 | 类型 | 废标签 | 前60字 |')
    lines.append('|------|---------|------|--------|--------|')
    for r in trash_records:
        preview = r['content'].replace('\n', '⏎').replace('|', '·')[:60]
        labels_str = ' + '.join(r['labels'])
        title_short = r['file_title'][:25]
        lines.append(f'| #{r["index"]} | {title_short} | {r["paragraph_type"]} | [{labels_str}] | `{preview}` |')
    lines.append('')

    # 「残渣可清」专项
    clearable = [r for r in label_records if '残渣可清' in r['labels']]
    lines.append(f'### 2.1 「残渣可清」子集(主体完整,清残渣后保留)')
    lines.append('')
    lines.append(f'**共 {len(clearable)} 条** — 建议清残渣后保留,不整条删')
    lines.append('')
    for r in clearable:
        preview = r['content'].replace('\n', '⏎')[:100]
        lines.append(f'- **#{r["index"]}** [{r["paragraph_type"]}] {r["file_title"][:30]}')
        lines.append(f'   `{preview}`')
    lines.append('')

    # ─────── 3. 重复分组清单 ───────
    lines.append('---')
    lines.append('')
    lines.append('## 3. 重复分组清单(相似度 ≥ 0.85)')
    lines.append('')
    lines.append(f'**共 {len(groups)} 个相似组**')
    lines.append('')

    if not groups:
        lines.append('未发现相似度达 0.85 阈值的重复组。')
    else:
        for gi, indices in enumerate(groups, 1):
            min_sim, all_identical = group_similarity(indices, normalized)
            suggestion = '去重留一' if all_identical else '全留(措辞略异)'
            lines.append(f'### 组 {gi}: {len(indices)} 条 · 最低相似度 {min_sim:.3f} · {"完全一字不差" if all_identical else "措辞略异"} · 建议[{suggestion}]')
            lines.append('')
            for idx in indices:
                r = label_records[idx]
                preview = r['content'].replace('\n', '⏎')[:80]
                lines.append(f'- **#{idx}** {r["file_title"][:35]} | type=[{r["paragraph_type"]}] | `{preview}`')
            lines.append('')

    # ─────── 4. paragraph_type 重判建议 ───────
    lines.append('---')
    lines.append('')
    lines.append('## 4. paragraph_type 重判建议')
    lines.append('')
    lines.append(f'**共 {len(type_suggestions)} 条建议改判**')
    lines.append('')
    lines.append('| 序号 | 文件来源 | 原 type | 建议 type | 判据 |')
    lines.append('|------|---------|---------|-----------|------|')
    for s in type_suggestions:
        lines.append(f'| #{s["index"]} | {s["file_title"][:30]} | {s["current_type"]} | {s["suggested_type"]} | {s["reason"]} |')
    lines.append('')

    # ─────── 5. 小结 ───────
    lines.append('---')
    lines.append('')
    lines.append('## 5. 一句话小结')
    lines.append('')

    # 预估留存
    keep_clean = only_clean
    keep_clearable_unique = sum(1 for r in clearable if r['index'] not in [idx for g in groups for idx in g[1:]])
    rough_keep_low = only_clean
    rough_keep_high = only_clean + len(clearable)

    lines.append(f'**预估合格留存量级**: **{rough_keep_low}–{rough_keep_high} 条**')
    lines.append('')
    lines.append(f'- 纯合格候选 {only_clean} 条为留存下限;')
    lines.append(f'- 加上「残渣可清」{len(clearable)} 条(清残渣后可入库)为留存上限;')
    lines.append(f'- 重复组若按建议去重留一,可去除 {sum(len(g)-1 for g in groups)} 条;')
    lines.append(f'- 标准第六条预估"几十至百余条量级",本次估算{("基本相符" if rough_keep_high < 200 else "可能偏宽,需人工二审")}。')
    lines.append('')
    lines.append('---')
    lines.append('')
    lines.append('## 6. 等待人工裁定')
    lines.append('')
    lines.append('本报告仅供裁定参考。')
    lines.append('- ✋ 段落库(P4).yaml 未做任何修改')
    lines.append('- ✋ 未删除/重建任何文件')
    lines.append('- ✋ 等待你的具体清单指令再进入第二阶段')

    OUT.write_text('\n'.join(lines), encoding='utf-8')
    print(f'\n报告已生成: {OUT}')
    print(f'文件大小: {OUT.stat().st_size} 字节')
    print(f'总行数: {len(lines)}')


if __name__ == '__main__':
    main()
