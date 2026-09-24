#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
P3 语料筛选工作 - 从90个文件中筛选50-100个优质范文
目标：建立按文种分类的优质范文库
"""

import yaml
import json
from pathlib import Path
from collections import defaultdict
from typing import List, Dict, Any

# 配置
METADATA_FILE = '04_corpus/个人历史交付物元数据索引_评分版.yaml'
HIGH_VALUE_FILE = '04_corpus/高价值文件清单.yaml'
OUTPUT_DIR = '04_corpus'
OUTPUT_FILE = '04_corpus/优质范文库(P3).yaml'
CATEGORY_DISTRIBUTION_FILE = '04_corpus/范文库统计.json'


def load_metadata():
    """加载元数据索引"""
    with open(METADATA_FILE, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)


def load_high_value_files():
    """加载高价值文件清单"""
    with open(HIGH_VALUE_FILE, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)


def create_file_path_set(high_value_files):
    """创建高价值文件路径集合"""
    return {item['file_path'] for item in high_value_files}


def calculate_comprehensive_score(item: Dict[str, Any]) -> float:
    """
    计算综合评分，用于扩展范文选择范围
    因素：质量分 + 字数均衡度 + 类别多样性
    """
    base_score = item.get('quality_score', 5)
    
    # 字数因素：8000-20000字的文件得分最高
    word_count = item.get('word_count', 0)
    if 8000 <= word_count <= 20000:
        word_bonus = 1.0
    elif 5000 <= word_count < 8000 or 20000 < word_count <= 40000:
        word_bonus = 0.8
    elif 40000 < word_count:
        word_bonus = 0.6
    else:
        word_bonus = 0.4
    
    # 类别多样性：某些类别更稀缺
    category = item.get('category', '待分类')
    category_bonus = {
        '讲话类': 0.3,
        '方案类': 0.2,
        '规划类': 0.2,
        '汇报类': 0.25,
        '报告类': 0.1,
        '待分类': 0,
    }.get(category, 0)
    
    return round(base_score + word_bonus + category_bonus, 2)


def categorize_by_type(metadata: List[Dict]) -> Dict[str, List[Dict]]:
    """按文种分类"""
    categories = defaultdict(list)
    
    for item in metadata:
        category = item.get('category', '待分类')
        categories[category].append(item)
    
    return dict(categories)


def select_corpus(
    metadata: List[Dict],
    high_value_set: set,
    min_count: int = 50,
    max_count: int = 100
) -> List[Dict]:
    """
    筛选范文语料
    
    策略：
    1. 优先选择高价值文件 (质量评分8分)
    2. 扩展选择评分7分的文件
    3. 基于综合评分继续扩展
    4. 保持文种分布均衡
    """
    
    selected = []
    category_counts = defaultdict(int)
    
    # 第一层：所有高价值文件 (评分8分)
    tier_1 = [item for item in metadata if item['file_path'] in high_value_set]
    selected.extend(tier_1)
    
    print(f"✓ Tier 1 (评分8分高价值文件): {len(tier_1)}个")
    for item in tier_1:
        category_counts[item['category']] += 1
    
    # 第二层：评分7分的文件
    tier_2_candidates = [
        item for item in metadata
        if item['file_path'] not in high_value_set and item.get('quality_score') == 7
    ]
    tier_2_selected = tier_2_candidates[:15]  # 选择前15个7分文件
    selected.extend(tier_2_selected)
    
    print(f"✓ Tier 2 (评分7分文件): {len(tier_2_selected)}个")
    for item in tier_2_selected:
        category_counts[item['category']] += 1
    
    # 第三层：基于综合评分的文件
    if len(selected) < max_count:
        tier_3_candidates = [
            item for item in metadata
            if item['file_path'] not in high_value_set and item.get('quality_score') in [6, 7]
        ]
        
        # 计算综合评分并排序
        tier_3_candidates.sort(
            key=lambda x: (calculate_comprehensive_score(x), x.get('word_count', 0)),
            reverse=True
        )
        
        # 按文种均衡分配
        needed = max_count - len(selected)
        category_distribution = defaultdict(int)
        
        for item in tier_3_candidates:
            if len(selected) >= max_count:
                break
            
            category = item['category']
            
            # 优先补充稀缺类别
            current_category_ratio = category_distribution[category] / (len(selected) + 1)
            if current_category_ratio < 0.35:  # 单个类别不超过35%
                selected.append(item)
                category_distribution[category] += 1
                category_counts[category] += 1
        
        tier_3_count = len(selected) - len(tier_1) - len(tier_2_selected)
        print(f"✓ Tier 3 (综合评分文件): {tier_3_count}个")
    
    print(f"\n📊 最终筛选结果: {len(selected)}个文件")
    print(f"目标范围: {min_count}-{max_count}个")
    
    # 计算文种分布
    print(f"\n文种分布统计:")
    for category, count in sorted(category_counts.items(), key=lambda x: x[1], reverse=True):
        percentage = round(count / len(selected) * 100, 1)
        print(f"  {category}: {count}个 ({percentage}%)")
    
    return selected


def add_metadata_to_selected(selected: List[Dict]) -> List[Dict]:
    """为选中的文件添加额外元数据"""
    for idx, item in enumerate(selected, 1):
        item['rank'] = idx
        item['comprehensive_score'] = calculate_comprehensive_score(item)
    
    return sorted(
        selected,
        key=lambda x: (
            x['category'],
            -x.get('quality_score', 5),
            -x.get('comprehensive_score', 0)
        )
    )


def generate_statistics(selected: List[Dict], original_count: int = 90) -> Dict:
    """生成统计信息"""
    category_counts = defaultdict(int)
    score_distribution = defaultdict(int)
    word_count_stats = {
        'min': float('inf'),
        'max': 0,
        'total': 0,
        'avg': 0,
        'by_category': {}
    }
    
    for item in selected:
        category = item['category']
        category_counts[category] += 1
        score_distribution[item.get('quality_score', 5)] += 1
        
        word_count = item.get('word_count', 0)
        word_count_stats['total'] += word_count
        word_count_stats['min'] = min(word_count_stats['min'], word_count)
        word_count_stats['max'] = max(word_count_stats['max'], word_count)
        
        if category not in word_count_stats['by_category']:
            word_count_stats['by_category'][category] = {
                'count': 0,
                'total_words': 0,
                'avg_words': 0
            }
        word_count_stats['by_category'][category]['count'] += 1
        word_count_stats['by_category'][category]['total_words'] += word_count
    
    # 计算平均值
    word_count_stats['avg'] = round(word_count_stats['total'] / len(selected), 0)
    for category_stats in word_count_stats['by_category'].values():
        if category_stats['count'] > 0:
            category_stats['avg_words'] = round(
                category_stats['total_words'] / category_stats['count'], 0
            )
    
    return {
        'selection_summary': {
            'total_selected': len(selected),
            'original_total': original_count,
            'selection_ratio': round(len(selected) / original_count * 100, 1),
            'categories_covered': len(category_counts)
        },
        'category_distribution': dict(category_counts),
        'quality_score_distribution': dict(score_distribution),
        'word_count_statistics': word_count_stats
    }


def save_results(selected: List[Dict], statistics: Dict):
    """保存结果到文件"""
    # 保存范文库YAML
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        yaml.dump(
            selected,
            f,
            allow_unicode=True,
            default_flow_style=False,
            sort_keys=False
        )
    print(f"\n✅ 范文库已保存: {OUTPUT_FILE}")
    print(f"   包含 {len(selected)} 个范文")
    
    # 保存统计JSON
    with open(CATEGORY_DISTRIBUTION_FILE, 'w', encoding='utf-8') as f:
        json.dump(statistics, f, indent=2, ensure_ascii=False)
    print(f"✅ 统计数据已保存: {CATEGORY_DISTRIBUTION_FILE}")


def main():
    print("=" * 70)
    print("P3 语料筛选工作 - 构建优质范文库")
    print("=" * 70)
    
    # 加载数据
    print("\n📖 加载元数据...")
    metadata = load_metadata()
    print(f"   共 {len(metadata)} 条元数据")
    
    print("📖 加载高价值文件...")
    high_value_files = load_high_value_files()
    high_value_set = create_file_path_set(high_value_files)
    print(f"   共 {len(high_value_files)} 个高价值文件")
    
    # 筛选范文语料
    print("\n🔍 执行语料筛选...")
    selected = select_corpus(metadata, high_value_set, min_count=50, max_count=100)
    
    # 添加元数据
    print("\n📝 处理选中文件的元数据...")
    selected = add_metadata_to_selected(selected)
    
    # 生成统计
    print("\n📊 生成统计信息...")
    statistics = generate_statistics(selected, len(metadata))
    
    # 保存结果
    print("\n💾 保存结果...")
    save_results(selected, statistics)
    
    # 打印最终统计
    print("\n" + "=" * 70)
    print("筛选完成统计")
    print("=" * 70)
    print(f"✅ 总计筛选: {statistics['selection_summary']['total_selected']} 个文件")
    print(f"✅ 原始库存: {statistics['selection_summary']['original_total']} 个文件")
    print(f"✅ 筛选比例: {statistics['selection_summary']['selection_ratio']}%")
    print(f"✅ 覆盖文种: {statistics['selection_summary']['categories_covered']} 个")
    
    print("\n文种分布:")
    for category, count in sorted(
        statistics['category_distribution'].items(),
        key=lambda x: x[1],
        reverse=True
    ):
        pct = round(count / statistics['selection_summary']['total_selected'] * 100, 1)
        print(f"  • {category}: {count} 个 ({pct}%)")
    
    print("\n品质分布:")
    for score in sorted(statistics['quality_score_distribution'].keys(), reverse=True):
        count = statistics['quality_score_distribution'][score]
        pct = round(count / statistics['selection_summary']['total_selected'] * 100, 1)
        print(f"  • {score}分: {count} 个 ({pct}%)")
    
    word_stats = statistics['word_count_statistics']
    print(f"\n字数统计:")
    print(f"  • 最小值: {word_stats['min']} 字")
    print(f"  • 最大值: {word_stats['max']} 字")
    print(f"  • 平均值: {word_stats['avg']:.0f} 字")
    print(f"  • 总计: {word_stats['total']} 字")
    
    print("\n" + "=" * 70)
    print("✨ P3 语料筛选工作完成！")
    print("=" * 70)


if __name__ == '__main__':
    main()
