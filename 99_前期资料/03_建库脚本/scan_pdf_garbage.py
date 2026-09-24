#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
统一清洗排查 · 第二+三步：定义垃圾特征 + 分库扫描分类（只读）

输入：
  - 03_dictionary/金句库(P4).yaml
  - 04_corpus/段落库(P4).yaml
  - 01_templates/ 下全部 .json
输出：
  - 控制台 + 内部数据结构（供第四步生成清单报告）

不修改任何原文件，仅读取。
"""

import json
import yaml
import re
from pathlib import Path
from collections import defaultdict

PROJECT_ROOT = Path(__file__).parent

# ─────────────────────────────────────────────
# 第二步：垃圾特征定义
# ─────────────────────────────────────────────

# 页码类
PAGE_PATTERNS = [
    (r'第\s*\d+\s*页\s*[,，]\s*共\s*\d+\s*页', '页码组合'),
    (r'第\s*\d+\s*页(?!\d)', '第X页'),
    (r'共\s*\d+\s*页', '共Y页'),
    (r'^[\s]*\d+\s*$', '纯数字行'),
]

# Markdown 残片类
MD_PATTERNS = [
    (r'##\s*第\s*\d+\s*页', '## 第X页'),
    (r'^[\s]*#{1,6}\s+[^\n]+$', '孤立 # 标题行'),
    (r'^---+\s*$', '--- 分隔符'),
]

# 表格残片类
TABLE_PATTERNS = [
    (r'\|[-\s]*\|', '表格分隔行 |---|'),
    (r'^\s*\|[^|]+\|[^|]+\|', '表格行（多列竖线）'),
]

# 截断类
CUTOFF_PATTERNS = [
    (r'[，。；,;]\s*$', '以标点中途结束'),  # 文本末尾被标点截断（且没有后续）
]

ALL_PATTERNS = {
    'page': PAGE_PATTERNS,
    'md': MD_PATTERNS,
    'table': TABLE_PATTERNS,
    # cutoff 单独处理，因为依赖完整性判断
}


def detect_garbage(text):
    """识别一段文本中的垃圾特征，返回特征列表（[(类型, 描述, 命中文本)]）"""
    if not text:
        return []
    hits = []
    for category, patterns in ALL_PATTERNS.items():
        for pat, name in patterns:
            for m in re.finditer(pat, text, re.MULTILINE):
                hits.append((category, name, m.group(0).strip()[:30]))
    return hits


def calc_garbage_ratio(text, hits):
    """估算垃圾内容占整条比例（用命中片段的总字符 / 文本总字符）"""
    if not text or not hits:
        return 0.0
    garbage_chars = sum(len(h[2]) for h in hits)
    return garbage_chars / len(text)


# ─────────────────────────────────────────────
# 库 1：金句库 P4
# ─────────────────────────────────────────────
def scan_golden_sentences():
    path = PROJECT_ROOT / '03_dictionary' / '金句库(P4).yaml'
    with open(path, 'r', encoding='utf-8') as f:
        data = yaml.safe_load(f)

    THRESHOLD_MIN_LEN = 8

    clean, suspect, trash = [], [], []

    for i, item in enumerate(data):
        sentence = str(item.get('sentence', ''))
        length = len(sentence.strip())
        hits = detect_garbage(sentence)
        garbage_ratio = calc_garbage_ratio(sentence, hits)

        record = {
            'index': i,
            'sentence': sentence,
            'length': length,
            'category': item.get('category', ''),
            'file_title': item.get('file_title', ''),
            'hits': hits,
            'garbage_ratio': garbage_ratio,
        }

        # 分类逻辑（保守版：宁可放可疑，不要误杀）
        if not hits and length >= THRESHOLD_MIN_LEN:
            clean.append(record)
        elif length < THRESHOLD_MIN_LEN:
            # 太短 → 不成句，可疑
            suspect.append(record)
        elif _is_mostly_garbage(sentence, hits):
            # 去垃圾后剩余 <10 字才算主体是垃圾
            trash.append(record)
        else:
            # 含垃圾但去掉后仍有内容 → 可疑（默认保留）
            suspect.append(record)

    return {'total': len(data), 'clean': clean, 'suspect': suspect, 'trash': trash}


def _is_mostly_garbage(text, hits):
    """严格判定：仅当去除垃圾后剩余有意义内容极少（<10 字）才算"主体是垃圾"。
    按任务规则「模棱两可一律保留」，宁可宽松也不要误杀。"""
    if not text or not hits:
        return False
    cleaned = text
    # 移除每个命中的垃圾片段
    for _, _, frag in hits:
        cleaned = cleaned.replace(frag, '')
    # 用更宽的正则再清理一次（防止命中片段未完全匹配）
    cleaned = re.sub(r'第\s*\d+\s*页\s*[,，]\s*共\s*\d+\s*页', '', cleaned)
    cleaned = re.sub(r'第\s*\d+\s*页', '', cleaned)
    cleaned = re.sub(r'共\s*\d+\s*页', '', cleaned)
    cleaned = re.sub(r'##\s*第\s*\d+\s*页', '', cleaned)
    cleaned = re.sub(r'^#{1,6}\s+.*$', '', cleaned, flags=re.MULTILINE)
    cleaned = re.sub(r'^\|[^\n]*\|[^\n]*$', '', cleaned, flags=re.MULTILINE)
    cleaned = re.sub(r'^---+$', '', cleaned, flags=re.MULTILINE)
    # 去标点/空白/孤立符号
    meaningful = re.sub(r'[#\-*|\s\n（）()【】[\]]+', '', cleaned)
    # 严格阈值：剩余 < 10 个有意义字符 才算主体是垃圾
    return len(meaningful) < 10


# ─────────────────────────────────────────────
# 库 2：段落库 P4
# ─────────────────────────────────────────────
def scan_paragraphs():
    path = PROJECT_ROOT / '04_corpus' / '段落库(P4).yaml'
    with open(path, 'r', encoding='utf-8') as f:
        data = yaml.safe_load(f)

    THRESHOLD_MIN_LEN = 50

    clean, suspect, trash = [], [], []

    for i, item in enumerate(data):
        content = str(item.get('content', ''))
        length = len(content.strip())
        hits = detect_garbage(content)
        garbage_ratio = calc_garbage_ratio(content, hits)

        record = {
            'index': i,
            'content': content,
            'length': length,
            'category': item.get('category', ''),
            'paragraph_type': item.get('paragraph_type', ''),
            'file_title': item.get('file_title', ''),
            'hits': hits,
            'garbage_ratio': garbage_ratio,
        }

        if not hits and length >= THRESHOLD_MIN_LEN:
            clean.append(record)
        elif length < THRESHOLD_MIN_LEN:
            suspect.append(record)
        elif _is_mostly_garbage(content, hits):
            trash.append(record)
        else:
            suspect.append(record)

    return {'total': len(data), 'clean': clean, 'suspect': suspect, 'trash': trash}


# ─────────────────────────────────────────────
# 库 3：模板库 — 检查 prompt_template 字段
# ─────────────────────────────────────────────
def scan_templates():
    tpl_dir = PROJECT_ROOT / '01_templates'
    json_files = sorted([f for f in tpl_dir.rglob('*.json')
                         if f.name != 'by_usage_index.json'])

    # 模板库不删除整个模板（业务价值高），只标记 prompt_template 字段是否含 PDF 垃圾
    # 分类标准：
    #   ✅ 干净：prompt_template 不含任何 PDF 页码/标题碎片
    #   ⚠️ 可疑：prompt_template 含碎片，但模板整体仍可用（保留待人工裁决）
    #   🔴 垃圾：整个 prompt_template 主体就是垃圾（不会发生在模板库，因为前面已确认每个模板都有完整骨架）

    clean, suspect, trash = [], [], []

    for jf in json_files:
        with open(jf, 'r', encoding='utf-8') as f:
            data = json.load(f)
        ps = str(data.get('prompt_system', ''))
        pt = str(data.get('prompt_template', ''))

        # 只扫描 prompt_template 和 prompt_system 字段中的 PDF 垃圾
        # 不扫描 structure_skeleton 等骨架字段（前面已确认 100% 良好）
        ps_hits = detect_garbage(ps)
        pt_hits = detect_garbage(pt)

        rel = jf.relative_to(tpl_dir).as_posix()
        all_hits = [('prompt_system', h) for h in ps_hits] + \
                   [('prompt_template', h) for h in pt_hits]

        record = {
            'path': rel,
            'doc_type': data.get('doc_type', ''),
            'title': data.get('title', ''),
            'all_hits': all_hits,
            'ps_garbage_count': len(ps_hits),
            'pt_garbage_count': len(pt_hits),
        }

        # 模板库的"垃圾"定义不同于前两库 —— 模板整体不会是垃圾，
        # 只标记字段级污染
        if not all_hits:
            clean.append(record)
        else:
            suspect.append(record)
        # trash 永远为空（模板不整删）

    return {'total': len(json_files), 'clean': clean, 'suspect': suspect, 'trash': trash}


# ─────────────────────────────────────────────
# 主流程
# ─────────────────────────────────────────────
def main():
    print('=== 第三步：分库扫描（只读） ===\n')

    print('扫描金句库 P4 ...')
    gs_result = scan_golden_sentences()
    print(f'  总条目: {gs_result["total"]}')
    print(f'  ✅ 干净: {len(gs_result["clean"])}')
    print(f'  ⚠️ 可疑: {len(gs_result["suspect"])}')
    print(f'  🔴 垃圾: {len(gs_result["trash"])}')

    print('\n扫描段落库 P4 ...')
    pg_result = scan_paragraphs()
    print(f'  总条目: {pg_result["total"]}')
    print(f'  ✅ 干净: {len(pg_result["clean"])}')
    print(f'  ⚠️ 可疑: {len(pg_result["suspect"])}')
    print(f'  🔴 垃圾: {len(pg_result["trash"])}')

    print('\n扫描模板库 ...')
    tpl_result = scan_templates()
    print(f'  总条目: {tpl_result["total"]}')
    print(f'  ✅ 干净: {len(tpl_result["clean"])}')
    print(f'  ⚠️ 可疑: {len(tpl_result["suspect"])}（字段级污染）')
    print(f'  🔴 垃圾: {len(tpl_result["trash"])}（模板库不整删）')

    # 写入 pickle 供第四步使用
    import pickle
    out_path = PROJECT_ROOT / '.scan_result.pkl'
    with open(out_path, 'wb') as f:
        pickle.dump({'gs': gs_result, 'pg': pg_result, 'tpl': tpl_result}, f)
    print(f'\n扫描结果暂存于: {out_path}')


if __name__ == '__main__':
    main()
