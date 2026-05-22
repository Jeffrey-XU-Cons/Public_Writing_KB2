#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Day 2 上午：元数据质量优化与评分
- 对历史交付物进行人工抽查
- 补充质量评分 (quality_score: 1-10)
- 标记高价值文件
"""

import yaml
import random
from pathlib import Path

BASE_DIR = Path("d:/projects/Public_Writing_KB")
INPUT_FILE = BASE_DIR / "04_corpus" / "个人历史交付物元数据索引.yaml"
OUTPUT_FILE = BASE_DIR / "04_corpus" / "个人历史交付物元数据索引_评分版.yaml"

# 质量评分规则
# 字数 > 5000: 基础分 5分
# 字数 5000-10000: 基础分 6分
# 字数 > 10000: 基础分 7分
# 根据分类调整：
#   报告类/讲话类 +1分
#   方案类/规划类 +0分
#   规划类高质量 +1分
#   待分类 -1分

def calculate_quality_score(item):
    """根据规则计算质量评分"""
    score = 5  # 基础分
    
    # 字数影响
    word_count = item.get('word_count', 0)
    if word_count > 10000:
        score = 7
    elif word_count > 5000:
        score = 6
    
    # 分类影响
    category = item.get('category', '')
    if category in ['报告类', '讲话类']:
        score += 1
    elif category == '待分类':
        score -= 1
    
    # 边界处理
    score = max(1, min(10, score))
    
    return score

def load_and_score():
    """加载数据并补充评分"""
    print(f"Loading metadata from {INPUT_FILE}...")
    
    with open(INPUT_FILE, 'r', encoding='utf-8') as f:
        data = yaml.safe_load(f)
    
    print(f"Total records: {len(data)}")
    
    # 为所有记录补充质量评分
    for item in data:
        if item.get('quality_score', 0) == 0:  # 仅为未评分的补充评分
            item['quality_score'] = calculate_quality_score(item)
    
    # 按评分排序，找出高价值文件
    sorted_data = sorted(data, key=lambda x: x.get('quality_score', 0), reverse=True)
    
    # 统计评分分布
    print("\n【评分分布统计】")
    score_distribution = {}
    for item in data:
        score = item.get('quality_score', 0)
        score_distribution[score] = score_distribution.get(score, 0) + 1
    
    for score in sorted(score_distribution.keys(), reverse=True):
        count = score_distribution[score]
        print(f"  {score}分: {count}条 {'█' * (count // 2)}")
    
    # 列出高价值文件（评分 >= 8分）
    high_value = [item for item in sorted_data if item.get('quality_score', 0) >= 8]
    print(f"\n【高价值文件】(评分 >= 8分): {len(high_value)}条")
    for i, item in enumerate(high_value[:10], 1):
        score = item.get('quality_score', 0)
        print(f"  [{score}分] {item['source_file_name'][:50]}")
    
    # 保存到新文件
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        yaml.dump(data, f, allow_unicode=True, indent=2, sort_keys=False)
    
    print(f"\n✅ Quality-scored metadata saved to: {OUTPUT_FILE}")
    
    # 生成高价值文件清单
    high_value_list = sorted_data[:30]  # 取评分最高的30条
    with open(BASE_DIR / "04_corpus" / "高价值文件清单.yaml", 'w', encoding='utf-8') as f:
        yaml.dump(high_value_list, f, allow_unicode=True, indent=2, sort_keys=False)
    
    print(f"✅ High-value file list saved to: 04_corpus/高价值文件清单.yaml")
    
    return data, high_value

if __name__ == "__main__":
    load_and_score()
