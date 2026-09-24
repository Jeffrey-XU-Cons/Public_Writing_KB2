#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
prepare_corpus.py - 处理语料库（范文、段落、金句）为JSONL格式

功能：
- 读取04_corpus目录下的所有YAML文件
- 分离范文、段落、金句三类语料
- 转换为标准的JSONLines格式
- 输出为三个分离的JSONL文件（便于不同场景检索）
"""

import json
import os
import re
from pathlib import Path
from typing import List, Dict, Any

class CorpusProcessor:
    def __init__(self, base_path: str):
        self.base_path = Path(base_path)
        self.corpus_data = {
            'documents': [],     # 范文库
            'paragraphs': [],    # 段落库
            'golden_sentences': []  # 金句库
        }
        self.error_log = []
        self.stats = {
            'total_items': 0,
            'documents': 0,
            'paragraphs': 0,
            'golden_sentences': 0,
            'failed': 0,
            'files_processed': 0
        }
    
    def parse_yaml_corpus(self, file_path: Path) -> List[Dict[str, Any]]:
        """解析YAML格式的语料库文件"""
        items = []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 简单的YAML到Python对象转换（处理基本格式）
            items = self._parse_yaml_lines(content, file_path.name)
        
        except Exception as e:
            self.error_log.append(f"解析文件 {file_path.name} 失败: {e}")
        
        return items
    
    def _parse_yaml_lines(self, content: str, filename: str) -> List[Dict]:
        """逐行解析YAML列表格式"""
        items = []
        current_item = {}
        indent_level = 0
        
        lines = content.split('\n')
        
        for line in lines:
            if not line.strip() or line.strip().startswith('#'):
                continue
            
            # 检查是否是新的列表项
            if line.startswith('- '):
                # 保存前一个item
                if current_item:
                    if self._is_valid_item(current_item):
                        current_item['source_file'] = filename
                        items.append(current_item)
                current_item = {}
                
                # 解析第一个字段
                first_field = line[2:].strip()
                if ':' in first_field:
                    key, val = first_field.split(':', 1)
                    current_item[key.strip()] = val.strip()
            
            elif line.startswith('  ') and ':' in line:
                # 解析嵌入的键值对
                line = line.strip()
                if ':' in line:
                    key, val = line.split(':', 1)
                    current_item[key.strip()] = val.strip()
        
        # 保存最后一个item
        if current_item and self._is_valid_item(current_item):
            current_item['source_file'] = filename
            items.append(current_item)
        
        return items
    
    def _is_valid_item(self, item: Dict) -> bool:
        """检查item是否有效"""
        return bool(item.get('content') or item.get('paragraph_content') or 
                   len(item) > 2)  # 至少有有意义的内容
    
    def classify_corpus_items(self, items: List[Dict], filename: str) -> None:
        """根据源文件或内容特征分类语料"""
        for item in items:
            self.stats['total_items'] += 1
            
            try:
                # 确定item类型
                item_type = self._determine_item_type(item, filename)
                
                # 标准化item格式
                normalized_item = self._normalize_item(item, item_type, filename)
                
                if item_type == 'document':
                    self.corpus_data['documents'].append(normalized_item)
                    self.stats['documents'] += 1
                
                elif item_type == 'paragraph':
                    self.corpus_data['paragraphs'].append(normalized_item)
                    self.stats['paragraphs'] += 1
                
                elif item_type == 'golden_sentence':
                    self.corpus_data['golden_sentences'].append(normalized_item)
                    self.stats['golden_sentences'] += 1
            
            except Exception as e:
                self.error_log.append(f"分类item异常: {e}")
                self.stats['failed'] += 1
    
    def _determine_item_type(self, item: Dict, filename: str) -> str:
        """判断item的类型"""
        # 根据字段名判断
        if 'paragraph_type' in item or 'paragraph_index' in item:
            return 'paragraph'
        
        if '段落' in filename:
            return 'paragraph'
        
        if '金句' in filename or 'golden' in filename.lower():
            return 'golden_sentence'
        
        if '范文' in filename or '优质' in filename:
            return 'document'
        
        # 根据word_count判断
        word_count = item.get('word_count', 0)
        if isinstance(word_count, str):
            try:
                word_count = int(word_count)
            except:
                word_count = len(item.get('content', ''))
        
        if word_count > 500:
            return 'document'
        elif word_count > 50:
            return 'paragraph'
        else:
            return 'golden_sentence'
    
    def _normalize_item(self, item: Dict, item_type: str, filename: str) -> Dict:
        """规范化item格式"""
        # 尝试多个可能的content字段名
        content = (item.get('content') or 
                  item.get('paragraph_content') or 
                  item.get('text') or
                  str(item.get('内容', '')) or
                  '')
        
        # 如果content仍为空，尝试从其他字段拼接
        if not content and len(item) > 1:
            # 将所有非特殊字段连接起来
            parts = []
            for k, v in item.items():
                if k not in ['file_title', 'category', 'file_path', 'source_file', 
                            'paragraph_type', 'paragraph_index', 'word_count', 'quality_score']:
                    if isinstance(v, str) and v.strip():
                        parts.append(v)
            content = ' '.join(parts)
        
        # 计算字数（只计汉字）
        word_count = len(re.findall(r'[\u4e00-\u9fff]', content))
        
        normalized = {
            'id': f"{item_type[0]}_{self.stats[item_type + 's']:06d}",
            'content': content[:5000],  # 限制长度
            'type': item_type,
            'category': item.get('category', item.get('doc_type', '未分类')),
            'word_count': word_count,
            'quality_score': self._parse_quality_score(item.get('quality_score', 'B')),
            'tags': self._extract_tags(item, filename)
        }
        
        # 添加类型特定字段
        if item_type == 'paragraph':
            normalized['position'] = item.get('paragraph_type', 'middle')
            normalized['position_index'] = item.get('paragraph_index', 0)
            normalized['section'] = item.get('section', '')
        
        if item_type in ['paragraph', 'golden_sentence']:
            normalized['source_file'] = item.get('file_title', item.get('source_file', ''))
        
        return normalized
    
    def _parse_quality_score(self, score: str) -> float:
        """解析质量评分"""
        if isinstance(score, (int, float)):
            return float(score)
        
        score_str = str(score).strip().upper()
        
        # 字母评分转换为数字
        score_map = {'A': 9.0, 'B': 7.5, 'C': 6.0, 'D': 4.0, 'F': 2.0}
        
        for letter, value in score_map.items():
            if letter in score_str:
                return value
        
        try:
            return float(score_str)
        except:
            return 5.0  # 默认评分
    
    def _extract_tags(self, item: Dict, filename: str) -> List[str]:
        """提取标签"""
        tags = []
        
        # 从category字段提取
        if 'category' in item:
            tags.append(str(item['category']))
        
        # 从doc_type字段提取
        if 'doc_type' in item:
            tags.append(str(item['doc_type']))
        
        # 从文件名提取
        if '讲话' in filename:
            tags.append('讲话')
        if '报告' in filename:
            tags.append('报告')
        if '方案' in filename:
            tags.append('方案')
        
        return list(set(tags))[:5]
    
    def load_corpus_files(self):
        """加载所有语料库文件"""
        corpus_dir = self.base_path / '04_corpus'
        
        if not corpus_dir.exists():
            self.error_log.append(f"语料库目录不存在: {corpus_dir}")
            return
        
        # 处理YAML文件
        for yaml_file in corpus_dir.glob('*.yaml'):
            items = self.parse_yaml_corpus(yaml_file)
            self.classify_corpus_items(items, yaml_file.name)
            self.stats['files_processed'] += 1
        
        # 处理子目录中的YAML文件
        for subdir in corpus_dir.iterdir():
            if subdir.is_dir():
                for yaml_file in subdir.glob('*.yaml'):
                    items = self.parse_yaml_corpus(yaml_file)
                    self.classify_corpus_items(items, f"{subdir.name}/{yaml_file.name}")
                    self.stats['files_processed'] += 1
    
    def save_corpus_jsonl(self, output_dir: str):
        """保存语料为JSONL格式"""
        output_files = {}
        
        # 保存每种语料类型为单独的文件
        for corpus_type, items in self.corpus_data.items():
            output_file = os.path.join(output_dir, f'corpus_{corpus_type}.jsonl')
            
            try:
                with open(output_file, 'w', encoding='utf-8') as f:
                    for item in items:
                        f.write(json.dumps(item, ensure_ascii=False) + '\n')
                
                output_files[corpus_type] = output_file
                print(f"✓ 导出 {len(items)} 条{corpus_type}到 {output_file}")
            
            except Exception as e:
                self.error_log.append(f"保存{corpus_type}失败: {e}")
        
        # 同时保存统一文件
        unified_file = os.path.join(output_dir, 'corpus_segments.jsonl')
        try:
            with open(unified_file, 'w', encoding='utf-8') as f:
                for items in self.corpus_data.values():
                    for item in items:
                        f.write(json.dumps(item, ensure_ascii=False) + '\n')
            
            output_files['unified'] = unified_file
            total = sum(len(items) for items in self.corpus_data.values())
            print(f"✓ 导出 {total} 条统一语料库到 {unified_file}")
        
        except Exception as e:
            self.error_log.append(f"保存统一文件失败: {e}")
        
        return output_files
    
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
        print("开始处理语料库...")
        print("=" * 60)
        
        self.load_corpus_files()
        output_files = self.save_corpus_jsonl(output_dir)
        stats_file = os.path.join(output_dir, 'corpus_stats.json')
        self.save_stats(stats_file)
        
        print("\n处理统计:")
        print(f"  总项数: {self.stats['total_items']}")
        print(f"  范文数: {self.stats['documents']}")
        print(f"  段落数: {self.stats['paragraphs']}")
        print(f"  金句数: {self.stats['golden_sentences']}")
        print(f"  失败数: {self.stats['failed']}")
        print(f"  处理文件: {self.stats['files_processed']}")
        
        if self.error_log:
            print(f"\n前5条错误:")
            for err in self.error_log[:5]:
                print(f"  - {err}")
        
        return output_files


if __name__ == "__main__":
    project_root = Path(__file__).parent
    output_dir = project_root / 'data_prep'
    
    processor = CorpusProcessor(str(project_root))
    processor.run(str(output_dir))
