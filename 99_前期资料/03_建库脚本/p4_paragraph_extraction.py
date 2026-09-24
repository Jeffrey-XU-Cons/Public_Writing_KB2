#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
P4 段落与金句抽取工作
从90个范文中提取开头段落、结尾段落、关键转折和金句库
"""

import yaml
import json
import re
from pathlib import Path
from collections import defaultdict
from typing import List, Dict, Tuple, Any


# 配置
CORPUS_FILE = '04_corpus/优质范文库(P3).yaml'
RAW_MATERIALS_DIR = '00_raw_materials'
PARAGRAPH_OUTPUT = '04_corpus/段落库(P4).yaml'
GOLDEN_SENTENCES_OUTPUT = '03_dictionary/金句库(P4).yaml'
EXTRACTION_STATS = '04_corpus/段落抽取统计.json'


def load_corpus():
    """加载优质范文库"""
    with open(CORPUS_FILE, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)


def read_file_content(file_path: str) -> str:
    """读取文件内容"""
    try:
        full_path = Path(file_path)
        if full_path.exists():
            with open(full_path, 'r', encoding='utf-8') as f:
                return f.read()
    except Exception as e:
        print(f"  ⚠️ 读取文件失败: {file_path} - {e}")
    return ""


def split_into_paragraphs(text: str) -> List[str]:
    """将文本分割为段落"""
    # 按多个换行符分割
    paragraphs = re.split(r'\n\n+', text.strip())
    # 过滤空段落和过短段落
    return [p.strip() for p in paragraphs if len(p.strip()) > 20]


def extract_opening_paragraph(paragraphs: List[str], min_length: int = 50) -> Tuple[str, int]:
    """提取开头段落（第1或第2段）"""
    for idx in range(min(2, len(paragraphs))):
        para = paragraphs[idx]
        if len(para) >= min_length:
            return para, idx
    return "", -1


def extract_closing_paragraph(paragraphs: List[str], min_length: int = 50) -> Tuple[str, int]:
    """提取结尾段落（最后1或2段）"""
    for idx in range(max(0, len(paragraphs) - 2), len(paragraphs)):
        para = paragraphs[idx]
        if len(para) >= min_length:
            return para, idx
    return "", -1


def extract_key_paragraphs(paragraphs: List[str]) -> List[Tuple[str, int, str]]:
    """
    提取关键段落（含转折词或数据）
    返回：(段落文本, 段落索引, 段落类型)
    """
    key_paragraphs = []
    
    # 关键词：转折、总结、核心
    key_keywords = [
        '但是', '然而', '因此', '所以', '总之', '总结',
        '核心', '关键', '重点', '要求', '必须', '明确',
        '指出', '强调', '发现', '问题', '原因', '对策'
    ]
    
    # 数据/成就关键词
    data_keywords = ['%', '万元', '人', '倍', '年', '项', '条']
    
    for idx, para in enumerate(paragraphs):
        para_type = None
        
        # 检查转折和总结词
        for keyword in key_keywords:
            if keyword in para:
                para_type = '关键词段落'
                break
        
        # 检查数据段落
        if not para_type:
            for keyword in data_keywords:
                if keyword in para:
                    para_type = '数据段落'
                    break
        
        # 检查长度适度的段落
        if para_type and 60 <= len(para) <= 300:
            key_paragraphs.append((para, idx, para_type))
    
    return key_paragraphs


def extract_golden_sentences(text: str) -> List[Dict[str, str]]:
    """
    提取金句库
    金句特征：短（50-150字）、精炼、有观点、可单独成立
    """
    sentences = []
    
    # 按句号分割（中文和英文）
    sentence_pattern = r'[。！？；，]'
    sents = re.split(sentence_pattern, text)
    
    for sent in sents:
        sent = sent.strip()
        sent_len = len(sent)
        
        # 长度过滤
        if not (50 <= sent_len <= 180):
            continue
        
        # 金句特征：含有观点词、数据、或关键概念
        golden_keywords = [
            '应该', '必须', '要', '需要', '目标', '方向',
            '坚持', '强化', '加强', '深化', '推进',
            '实现', '促进', '提升', '完善', '建立',
            '创新', '转型', '升级', '改革', '发展',
            '质量', '效率', '效益', '竞争', '优势'
        ]
        
        has_golden_keyword = any(keyword in sent for keyword in golden_keywords)
        
        # 检查是否是完整表述
        is_complete = (
            sent.endswith(('项', '等', '等工作', '等措施')) or
            any(keyword in sent for keyword in ['的', '在', '以', '为']) and len(sent) > 40
        )
        
        if has_golden_keyword or is_complete:
            # 检查是否已添加
            sent_text = sent[:50]  # 用前50字作为唯一键
            if not any(s['sentence'][:50] == sent_text for s in sentences):
                sentences.append({
                    'sentence': sent,
                    'length': sent_len,
                    'type': 'golden_sentence'
                })
    
    return sentences


def calculate_quality_level(text: str) -> str:
    """根据内容质量级别判断"""
    length = len(text)
    has_data = any(char.isdigit() for char in text)
    has_key_word = any(word in text for word in ['建议', '对策', '措施', '方案', '战略'])
    
    if length >= 100 and (has_data or has_key_word):
        return 'A级'
    elif length >= 80:
        return 'B级'
    else:
        return 'C级'


def process_corpus():
    """处理语料库，提取段落和金句"""
    corpus = load_corpus()
    
    all_paragraphs = []
    all_golden_sentences = []
    stats = {
        'total_files': 0,
        'success_files': 0,
        'failed_files': 0,
        'total_paragraphs_extracted': 0,
        'total_golden_sentences_extracted': 0,
        'by_category': defaultdict(lambda: {
            'files': 0,
            'paragraphs': 0,
            'sentences': 0
        })
    }
    
    print(f"\n🔍 开始处理 {len(corpus)} 个范文文件...")
    print("=" * 70)
    
    for idx, item in enumerate(corpus, 1):
        file_path = item.get('file_path', '')
        category = item.get('category', '待分类')
        title = item.get('title', '')
        
        # 读取文件内容
        content = read_file_content(file_path)
        
        if not content:
            stats['failed_files'] += 1
            if idx % 10 == 0:
                print(f"  [{idx}/{len(corpus)}] ❌ 读取失败")
            continue
        
        stats['total_files'] += 1
        stats['success_files'] += 1
        
        # 分割段落
        paragraphs = split_into_paragraphs(content)
        
        if len(paragraphs) < 2:
            continue
        
        # 提取开头段落
        opening, opening_idx = extract_opening_paragraph(paragraphs)
        if opening:
            all_paragraphs.append({
                'file_title': title,
                'category': category,
                'file_path': file_path,
                'paragraph_type': '开头段落',
                'paragraph_index': opening_idx,
                'content': opening,
                'word_count': len(opening),
                'quality_score': calculate_quality_level(opening)
            })
            stats['total_paragraphs_extracted'] += 1
            stats['by_category'][category]['paragraphs'] += 1
        
        # 提取结尾段落
        closing, closing_idx = extract_closing_paragraph(paragraphs)
        if closing and closing != opening:  # 避免重复
            all_paragraphs.append({
                'file_title': title,
                'category': category,
                'file_path': file_path,
                'paragraph_type': '结尾段落',
                'paragraph_index': closing_idx,
                'content': closing,
                'word_count': len(closing),
                'quality_score': calculate_quality_level(closing)
            })
            stats['total_paragraphs_extracted'] += 1
            stats['by_category'][category]['paragraphs'] += 1
        
        # 提取关键段落（最多2个）
        key_paras = extract_key_paragraphs(paragraphs)[:2]
        for key_para, key_idx, para_type in key_paras:
            all_paragraphs.append({
                'file_title': title,
                'category': category,
                'file_path': file_path,
                'paragraph_type': f'关键段落({para_type})',
                'paragraph_index': key_idx,
                'content': key_para,
                'word_count': len(key_para),
                'quality_score': calculate_quality_level(key_para)
            })
            stats['total_paragraphs_extracted'] += 1
            stats['by_category'][category]['paragraphs'] += 1
        
        # 提取金句（最多5个）
        golden_sents = extract_golden_sentences(content)[:5]
        for sent_obj in golden_sents:
            all_golden_sentences.append({
                'file_title': title,
                'category': category,
                'file_path': file_path,
                'sentence': sent_obj['sentence'],
                'length': sent_obj['length'],
                'quality_score': calculate_quality_level(sent_obj['sentence'])
            })
            stats['total_golden_sentences_extracted'] += 1
            stats['by_category'][category]['sentences'] += 1
        
        stats['by_category'][category]['files'] += 1
        
        if idx % 10 == 0:
            print(f"  [{idx}/{len(corpus)}] ✓ 已处理 {idx} 个文件")
    
    print(f"\n✅ 处理完成！成功: {stats['success_files']}/{len(corpus)}")
    
    return all_paragraphs, all_golden_sentences, stats


def save_results(paragraphs: List[Dict], sentences: List[Dict], stats: Dict):
    """保存结果"""
    
    # 按类别排序段落
    paragraphs_by_category = defaultdict(list)
    for para in paragraphs:
        paragraphs_by_category[para['category']].append(para)
    
    # 保存段落库
    with open(PARAGRAPH_OUTPUT, 'w', encoding='utf-8') as f:
        yaml.dump(
            paragraphs,
            f,
            allow_unicode=True,
            default_flow_style=False,
            sort_keys=False
        )
    print(f"\n✅ 段落库已保存: {PARAGRAPH_OUTPUT}")
    print(f"   包含 {len(paragraphs)} 个段落")
    
    # 保存金句库
    with open(GOLDEN_SENTENCES_OUTPUT, 'w', encoding='utf-8') as f:
        yaml.dump(
            sentences,
            f,
            allow_unicode=True,
            default_flow_style=False,
            sort_keys=False
        )
    print(f"✅ 金句库已保存: {GOLDEN_SENTENCES_OUTPUT}")
    print(f"   包含 {len(sentences)} 个金句")
    
    # 保存统计信息
    stats['by_category'] = dict(stats['by_category'])
    with open(EXTRACTION_STATS, 'w', encoding='utf-8') as f:
        json.dump(stats, f, indent=2, ensure_ascii=False)
    print(f"✅ 统计数据已保存: {EXTRACTION_STATS}")


def display_statistics(paragraphs: List[Dict], sentences: List[Dict], stats: Dict):
    """显示统计信息"""
    print("\n" + "=" * 70)
    print("段落与金句抽取统计")
    print("=" * 70)
    
    print(f"\n📊 整体统计:")
    print(f"  • 处理文件: {stats['success_files']}/{stats['total_files']} 个")
    print(f"  • 提取段落: {stats['total_paragraphs_extracted']} 个")
    print(f"  • 提取金句: {stats['total_golden_sentences_extracted']} 个")
    
    print(f"\n📂 按文种统计:")
    for category in sorted(stats['by_category'].keys(), reverse=True):
        cat_stats = stats['by_category'][category]
        print(f"  【{category}】")
        print(f"    - 文件: {cat_stats['files']} 个")
        print(f"    - 段落: {cat_stats['paragraphs']} 个")
        print(f"    - 金句: {cat_stats['sentences']} 个")
    
    # 段落类型分布
    para_types = defaultdict(int)
    for para in paragraphs:
        para_types[para['paragraph_type']] += 1
    
    print(f"\n📝 段落类型分布:")
    for ptype, count in sorted(para_types.items(), key=lambda x: x[1], reverse=True):
        pct = round(count / len(paragraphs) * 100, 1)
        print(f"  • {ptype}: {count} 个 ({pct}%)")
    
    # 段落长度统计
    para_lengths = [p['word_count'] for p in paragraphs]
    if para_lengths:
        print(f"\n📏 段落长度统计:")
        print(f"  • 最短: {min(para_lengths)} 字")
        print(f"  • 最长: {max(para_lengths)} 字")
        print(f"  • 平均: {round(sum(para_lengths)/len(para_lengths), 0):.0f} 字")
    
    # 金句长度统计
    sent_lengths = [s['length'] for s in sentences]
    if sent_lengths:
        print(f"\n✨ 金句长度统计:")
        print(f"  • 最短: {min(sent_lengths)} 字")
        print(f"  • 最长: {max(sent_lengths)} 字")
        print(f"  • 平均: {round(sum(sent_lengths)/len(sent_lengths), 0):.0f} 字")
    
    print("\n" + "=" * 70)


def main():
    print("=" * 70)
    print("P4 段落与金句抽取工作")
    print("=" * 70)
    
    # 处理语料
    paragraphs, sentences, stats = process_corpus()
    
    # 保存结果
    print("\n💾 保存结果...")
    save_results(paragraphs, sentences, stats)
    
    # 显示统计
    display_statistics(paragraphs, sentences, stats)
    
    print("\n✨ P4 段落与金句抽取工作完成！")
    print("=" * 70)


if __name__ == '__main__':
    main()
