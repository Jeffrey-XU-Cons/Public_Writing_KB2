#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
validate_data_integrity.py - 验证导出的JSONL数据完整性和质量

功能：
- 检查JSONL文件格式正确性
- 验证必填字段完整性
- 检查文本编码（UTF-8）
- 检查数据质量指标
- 生成详细的验证报告
"""

import json
import os
from pathlib import Path
from typing import List, Dict, Any, Tuple

class DataValidator:
    def __init__(self, data_dir: str):
        self.data_dir = Path(data_dir)
        self.validation_results = {
            'files_checked': 0,
            'total_records': 0,
            'valid_records': 0,
            'invalid_records': 0,
            'errors': [],
            'warnings': [],
            'file_details': {}
        }
    
    def validate_jsonl_file(self, file_path: Path) -> Tuple[int, List[Dict], List[str]]:
        """验证单个JSONL文件"""
        valid_count = 0
        records = []
        errors = []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                line_num = 0
                for line in f:
                    line_num += 1
                    line = line.strip()
                    
                    if not line:
                        continue
                    
                    try:
                        record = json.loads(line)
                        records.append(record)
                        
                        # 验证记录
                        is_valid, error_msg = self._validate_record(record)
                        if is_valid:
                            valid_count += 1
                        else:
                            errors.append(f"行 {line_num}: {error_msg}")
                    
                    except json.JSONDecodeError as e:
                        errors.append(f"行 {line_num}: JSON解析失败 - {e}")
        
        except UnicodeDecodeError as e:
            errors.append(f"文件编码错误: {e}")
        except Exception as e:
            errors.append(f"文件读取失败: {e}")
        
        return valid_count, records, errors
    
    def _validate_record(self, record: Dict) -> Tuple[bool, str]:
        """验证单条记录"""
        # 检查基本字段
        if not isinstance(record, dict):
            return False, "记录不是字典类型"
        
        if not record:
            return False, "记录为空"
        
        # 根据记录类型定制验证规则
        # ID字段是通用必填
        if 'id' not in record:
            return False, "缺少必填字段: id"
        
        record_id = record['id']
        if not isinstance(record_id, str) or not record_id.strip():
            return False, "ID字段无效"
        
        # 对于不同类型的数据有不同的必填字段要求
        # 模板类
        if 'template_id' in record or 'name' in record:
            if 'name' not in record:
                return False, "缺少必填字段: name"
        
        # 语料库类
        elif 'type' in record:
            if 'content' not in record or not record['content']:
                return False, "缺少或为空: content字段"
        
        # 词典类 - 根据category判断必填字段
        elif 'category_code' in record or 'category' in record:
            # 词典条目应该有term或其他标识字段
            # 但不是所有类型都有term（金句库etc.）
            has_identifier = any(k in record for k in ['term', 'content', 'text', 'word', '用语', 'key'])
            if not has_identifier:
                return False, "缺少词条标识字段"
        
        return True, ""
    
    def validate_file_structure(self, file_path: Path) -> Dict[str, Any]:
        """验证文件的完整性和一致性"""
        valid_count, records, errors = self.validate_jsonl_file(file_path)
        
        file_info = {
            'file_name': file_path.name,
            'file_size_kb': file_path.stat().st_size / 1024,
            'total_records': len(records),
            'valid_records': valid_count,
            'invalid_records': len(records) - valid_count,
            'error_count': len(errors),
            'validity_rate': (valid_count / len(records) * 100) if records else 0,
            'errors': errors[:10]  # 仅保存前10条错误
        }
        
        # 如果有完全有效的记录，进行内容统计
        if valid_count > 0:
            valid_records = records[:valid_count]
            file_info['statistics'] = self._analyze_records(valid_records)
        
        return file_info
    
    def _analyze_records(self, records: List[Dict]) -> Dict[str, Any]:
        """分析记录的统计信息"""
        stats = {
            'total': len(records),
            'by_type': {},
            'by_category': {},
            'avg_word_count': 0,
            'avg_quality_score': 0
        }
        
        total_words = 0
        total_quality = 0
        quality_count = 0
        
        for record in records:
            # 统计类型
            if 'type' in record:
                type_val = record['type']
                stats['by_type'][type_val] = stats['by_type'].get(type_val, 0) + 1
            
            # 统计分类
            if 'category' in record:
                cat_val = record['category']
                stats['by_category'][cat_val] = stats['by_category'].get(cat_val, 0) + 1
            
            # 统计字数
            if 'word_count' in record:
                total_words += record['word_count']
            
            # 统计质量评分
            if 'quality_score' in record:
                score = record['quality_score']
                if isinstance(score, (int, float)) and 0 <= score <= 10:
                    total_quality += score
                    quality_count += 1
        
        if len(records) > 0:
            stats['avg_word_count'] = total_words / len(records)
        
        if quality_count > 0:
            stats['avg_quality_score'] = total_quality / quality_count
        
        return stats
    
    def run_validation(self) -> bool:
        """执行完整的验证流程"""
        print("=" * 60)
        print("开始验证数据完整性...")
        print("=" * 60)
        
        if not self.data_dir.exists():
            print(f"✗ 数据目录不存在: {self.data_dir}")
            return False
        
        # 查找所有JSONL文件
        jsonl_files = list(self.data_dir.glob('*.jsonl'))
        
        if not jsonl_files:
            print(f"✗ 在 {self.data_dir} 中没有找到JSONL文件")
            return False
        
        print(f"找到 {len(jsonl_files)} 个JSONL文件\n")
        
        # 验证每个文件
        all_valid = True
        for jsonl_file in sorted(jsonl_files):
            print(f"验证: {jsonl_file.name}")
            
            try:
                file_info = self.validate_file_structure(jsonl_file)
                self.validation_results['files_checked'] += 1
                self.validation_results['total_records'] += file_info['total_records']
                self.validation_results['valid_records'] += file_info['valid_records']
                self.validation_results['invalid_records'] += file_info['invalid_records']
                self.validation_results['file_details'][jsonl_file.name] = file_info
                
                # 输出检查结果
                validity_rate = file_info['validity_rate']
                status = "✓" if validity_rate >= 90 else "✗" if validity_rate < 70 else "△"
                
                print(f"  {status} 总记录: {file_info['total_records']}, " +
                      f"有效: {file_info['valid_records']}, " +
                      f"有效率: {validity_rate:.1f}%")
                
                if file_info['error_count'] > 0:
                    print(f"  ⚠ 错误: {file_info['error_count']}")
                    all_valid = False
                    for err in file_info['errors'][:3]:
                        print(f"      {err}")
                
                if 'statistics' in file_info:
                    stats = file_info['statistics']
                    if stats['avg_word_count'] > 0:
                        print(f"  📊 平均字数: {stats['avg_word_count']:.0f}")
                    if stats['avg_quality_score'] > 0:
                        print(f"  ⭐ 平均评分: {stats['avg_quality_score']:.2f}/10")
                
                print()
            
            except Exception as e:
                print(f"  ✗ 验证失败: {e}\n")
                all_valid = False
        
        return all_valid
    
    def generate_report(self, output_file: str):
        """生成验证报告"""
        report = {
            'validation_summary': {
                'files_checked': self.validation_results['files_checked'],
                'total_records': self.validation_results['total_records'],
                'valid_records': self.validation_results['valid_records'],
                'invalid_records': self.validation_results['invalid_records'],
                'overall_validity_rate': (
                    self.validation_results['valid_records'] / 
                    self.validation_results['total_records'] * 100
                ) if self.validation_results['total_records'] > 0 else 0
            },
            'file_details': self.validation_results['file_details'],
            'errors': self.validation_results['errors'][:20],
            'warnings': self.validation_results['warnings'][:20]
        }
        
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(report, f, ensure_ascii=False, indent=2)
            print(f"\n✓ 验证报告已保存到: {output_file}")
        except Exception as e:
            print(f"✗ 保存验证报告失败: {e}")
    
    def print_summary(self):
        """打印验证摘要"""
        print("\n" + "=" * 60)
        print("验证摘要")
        print("=" * 60)
        
        print(f"检查的文件数: {self.validation_results['files_checked']}")
        print(f"总记录数: {self.validation_results['total_records']}")
        print(f"有效记录: {self.validation_results['valid_records']}")
        print(f"无效记录: {self.validation_results['invalid_records']}")
        
        if self.validation_results['total_records'] > 0:
            validity_rate = (
                self.validation_results['valid_records'] / 
                self.validation_results['total_records'] * 100
            )
            status = "✓ 通过" if validity_rate >= 95 else "△ 警告" if validity_rate >= 80 else "✗ 失败"
            print(f"\n总体有效率: {validity_rate:.1f}% [{status}]")
        
        # 按文件输出详情
        if self.validation_results['file_details']:
            print("\n文件详情:")
            for filename, info in self.validation_results['file_details'].items():
                rate = info['validity_rate']
                print(f"  • {filename}: {info['valid_records']}/{info['total_records']} ({rate:.1f}%)")
    
    def run(self):
        """执行完整的验证流程"""
        success = self.run_validation()
        self.print_summary()
        
        # 生成报告
        report_file = self.data_dir / 'validation_report.json'
        self.generate_report(str(report_file))
        
        return success


if __name__ == "__main__":
    import sys
    
    project_root = Path(__file__).parent
    data_dir = project_root / 'data_prep'
    
    validator = DataValidator(str(data_dir))
    validator.run()
