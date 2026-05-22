#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
prepare_dictionary.py - 转换词典库为JSONL格式（Dify导入格式）

功能：
- 读取03_dictionary目录下的所有YAML文件
- 解析禁用词、搭配规范、套话替换、行业术语等
- 转换为标准的JSONLines格式
- 输出到data_prep/dictionary_unified.jsonl
"""

import json
import os
from pathlib import Path
from typing import List, Dict, Any, Tuple
import re

class DictionaryProcessor:
    def __init__(self, base_path: str):
        self.base_path = Path(base_path)
        self.entries = []
        self.error_log = []
        self.stats = {
            'total_processed': 0,
            'successful': 0,
            'failed': 0,
            'by_category': {}
        }
        # 词典模块代码映射
        self.category_code_map = {
            '禁用词': 'PW',      # Prohibited Words
            '搭配规范': 'MM',    # Matching Management
            '套话替换': 'CP',    # Common Phrases
            '行业术语': 'TT',    # Tobacco Terminology
            '口语转换': 'OC',    # Oral to Colloquial
            '高频易错': 'HEF',   # High-Frequency Errors
            '常用公文用语': 'COU' # Common Official Usages
        }
    
    def parse_yaml_table(self, text: str, category_name: str) -> List[Dict[str, Any]]:
        """解析YAML中的表格格式数据"""
        entries = []
        category_code = self.category_code_map.get(category_name, 'OTHER')
        
        # 简单的表格行解析
        lines = text.split('\n')
        in_table = False
        headers = []
        entry_id = 0
        
        for line in lines:
            line_stripped = line.strip()
            
            if line_stripped.startswith('|'):
                if not in_table:
                    in_table = True
                    # 解析表头
                    headers = [h.strip().lower() for h in line_stripped.split('|')[1:-1]]
                    continue
                
                # 跳过分隔符行
                if all(c in '-|:' for c in line_stripped):
                    continue
                
                # 解析数据行
                cols = [c.strip() for c in line_stripped.split('|')[1:-1]]
                if len(cols) >= 1 and cols[0]:  # 至少有一列非空
                    entry = {
                        'id': f"{category_code}_{entry_id:06d}",
                        'category': category_name,
                        'category_code': category_code
                    }
                    
                    # 根据表头建立映射
                    for i, header in enumerate(headers):
                        if i < len(cols):
                            value = cols[i]
                            entry[header] = value
                    
                    # 确保有term字段（用于词典检索）- 转换中文字段名
                    if 'term' not in entry:
                        for key in ['用语', '禁用词', '搭配', '术语', '词']:
                            if key in entry:
                                entry['term'] = entry[key]
                                break
                        if 'term' not in entry and cols and cols[0]:
                            entry['term'] = cols[0]  # 使用第一列作为term
                        else:
                            entry['term'] = ''  # 确保有term字段
                    
                    entries.append(entry)
                    entry_id += 1
        
        return entries
    
    def parse_dictionary_file(self, file_path: Path, category_name: str) -> List[Dict]:
        """解析词典文件"""
        entries = []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 使用表格解析
            entries = self.parse_yaml_table(content, category_name)
            
            # 如果是金句库，需要特殊处理格式
            if '金句' in file_path.name or '金句库' in content[:200]:
                entries = self._parse_golden_sentences(content)
            
            # 如果没有找到表格，尝试解析列表格式
            if not entries:
                entries = self._parse_list_format(content, category_name)
        
        except Exception as e:
            self.error_log.append(f"解析文件 {file_path.name} 失败: {e}")
        
        return entries
    
    def _parse_golden_sentences(self, content: str) -> List[Dict]:
        """解析金句库格式"""
        entries = []
        
        # 尝试识别金句条目（通常以- 开头）
        lines = content.split('\n')
        for line in lines:
            line = line.strip()
            
            # 金句通常较长，包含有意义的内容
            if line.startswith('-') and len(line) > 20:
                sentence_text = line[1:].strip()
                
                entry = {
                    'id': f"golden_{len(entries):06d}",
                    'content': sentence_text,
                    'type': 'golden_sentence',
                    'category': '金句库',
                    'category_code': 'GS',
                    'word_count': len(sentence_text),
                    'tags': self._extract_tags(sentence_text)
                }
                entries.append(entry)
        
        return entries
    
    def _parse_list_format(self, content: str, category_name: str) -> List[Dict]:
        """解析列表格式的条目"""
        entries = []
        category_code = self.category_code_map.get(category_name, 'OTHER')
        
        # 匹配模式：- 主条目（说明）或 - 主条目: 替代表述
        pattern = r'^\s*-\s*([^：:]+)[：:\s]*(.*)$'
        
        entry_counter = 0
        for line in content.split('\n'):
            match = re.match(pattern, line)
            if match:
                term = match.group(1).strip()
                description = match.group(2).strip()
                
                if term and len(term) <= 100 and term not in ['', ' ']:  # 过滤过长的条目
                    entry = {
                        'id': f"{category_code}_{entry_counter:06d}",
                        'term': term,
                        'category': category_name,
                        'category_code': category_code,
                        'description': description if description else term,
                        'tags': self._extract_tags(term + ' ' + description)
                    }
                    entries.append(entry)
                    entry_counter += 1
        
        return entries
    
    def _extract_tags(self, text: str) -> List[str]:
        """从文本中提取潜在的标签"""
        tags = []
        
        # 提取括号内的内容作为标签
        tag_pattern = r'[（(]([^）)]+)[）)]'
        for match in re.finditer(tag_pattern, text):
            tag = match.group(1).strip()
            if 3 <= len(tag) <= 20:
                tags.append(tag)
        
        return list(set(tags))[:5]  # 最多5个标签
    
    def load_all_dictionaries(self):
        """加载所有词典文件"""
        dict_dir = self.base_path / '03_dictionary'
        
        if not dict_dir.exists():
            self.error_log.append(f"词典目录不存在: {dict_dir}")
            return
        
        # 支持的文件类型
        supported_files = {
            'official_terms.yaml': '官方用语',
            'official_terms_v2.yaml': '官方用语',
            '金句库(P4).yaml': '金句库',
            '.yaml': '默认YAML'
        }
        
        entry_id_counter = 1
        
        for file_path in dict_dir.glob('*.yaml'):
            file_name = file_path.name
            
            # 确定分类
            category_name = None
            for pattern, name in supported_files.items():
                if file_name.endswith(pattern) or pattern in file_name:
                    category_name = name
                    break
            
            if not category_name:
                category_name = '其他'
            
            # 解析文件
            entries = self.parse_dictionary_file(file_path, category_name)
            
            # 更新统计
            for entry in entries:
                self.stats['total_processed'] += 1
                if entry:
                    # 确保id字段存在
                    if 'id' not in entry:
                        category_code = self.category_code_map.get(category_name, 'OTHER')
                        entry['id'] = f"{category_code}_{entry_id_counter:06d}"
                    
                    self.stats['successful'] += 1
                    self.entries.append(entry)
                    entry_id_counter += 1
                    
                    # 统计分类
                    cat = entry.get('category', 'unknown')
                    if cat not in self.stats['by_category']:
                        self.stats['by_category'][cat] = 0
                    self.stats['by_category'][cat] += 1
    
    def save_to_jsonl(self, output_path: str):
        """保存为JSONL格式"""
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                for entry in self.entries:
                    f.write(json.dumps(entry, ensure_ascii=False) + '\n')
            print(f"✓ 成功导出 {len(self.entries)} 条词典条目到 {output_path}")
        except Exception as e:
            self.error_log.append(f"保存JSONL文件失败: {e}")
    
    def save_stats(self, output_path: str):
        """保存处理统计信息"""
        stats = {
            **self.stats,
            'error_count': len(self.error_log),
            'errors': self.error_log[:50]
        }
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(stats, f, ensure_ascii=False, indent=2)
            print(f"✓ 统计信息已保存: {output_path}")
        except Exception as e:
            print(f"✗ 保存统计信息失败: {e}")
    
    def run(self, output_dir: str):
        """执行数据处理流程"""
        print("=" * 60)
        print("开始处理词典库...")
        print("=" * 60)
        
        self.load_all_dictionaries()
        
        output_file = os.path.join(output_dir, 'dictionary_unified.jsonl')
        stats_file = os.path.join(output_dir, 'dictionary_stats.json')
        
        self.save_to_jsonl(output_file)
        self.save_stats(stats_file)
        
        print("\n处理统计:")
        print(f"  总处理数: {self.stats['total_processed']}")
        print(f"  成功: {self.stats['successful']}")
        
        if self.stats['by_category']:
            print("\n分类统计:")
            for cat, count in self.stats['by_category'].items():
                print(f"  {cat}: {count}")
        
        if self.error_log:
            print(f"\n前5条错误:")
            for err in self.error_log[:5]:
                print(f"  - {err}")
        
        return output_file


if __name__ == "__main__":
    project_root = Path(__file__).parent
    output_dir = project_root / 'data_prep'
    
    processor = DictionaryProcessor(str(project_root))
    processor.run(str(output_dir))
