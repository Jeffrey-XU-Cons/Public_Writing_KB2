#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
prepare_templates.py - 转换公文写作模板为JSONL格式（Dify导入格式）

功能：
- 读取01_templates目录下的所有JSON模板
- 转换为标准的JSONLines格式
- 输出到data_prep/templates_import.jsonl
"""

import json
import os
from pathlib import Path
from typing import List, Dict, Any

class TemplateProcessor:
    def __init__(self, base_path: str):
        self.base_path = Path(base_path)
        self.templates = []
        self.error_log = []
        self.stats = {
            'total_processed': 0,
            'successful': 0,
            'failed': 0
        }
    
    def load_index(self) -> Dict[str, Any]:
        """加载模板索引文件"""
        index_path = self.base_path / '01_templates' / 'by_usage_index.json'
        try:
            with open(index_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            self.error_log.append(f"读取索引文件失败: {e}")
            return {}
    
    def load_template_file(self, file_path: str) -> Dict[str, Any]:
        """加载单个模板文件"""
        full_path = self.base_path / '01_templates' / file_path
        try:
            with open(full_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            self.error_log.append(f"读取模板文件 {file_path} 失败: {e}")
            return None
    
    def extract_template_content(self, template_data: Dict) -> str:
        """从模板对象中提取提示词内容"""
        if isinstance(template_data, dict):
            # 尝试多个可能的字段名
            for field in ['prompt', 'content', 'template', 'system_prompt', 'text']:
                if field in template_data:
                    return str(template_data[field])
        return ""
    
    def process_index(self):
        """处理模板索引，转换为标准格式"""
        index = self.load_index()
        
        if not index:
            self.error_log.append("无法加载模板索引")
            return
        
        scenarios = index.get('scenarios', {})
        template_id_counter = 1
        
        for scenario_name, scenario_data in scenarios.items():
            templates = scenario_data.get('templates', [])
            
            for template_meta in templates:
                self.stats['total_processed'] += 1
                
                try:
                    file_path = template_meta.get('file_path')
                    if not file_path:
                        self.error_log.append(f"模板缺少file_path字段")
                        self.stats['failed'] += 1
                        continue
                    
                    # 加载完整的模板文件
                    template_content = self.load_template_file(file_path)
                    if not template_content:
                        self.stats['failed'] += 1
                        continue
                    
                    # 构建标准格式
                    template_record = {
                        "id": f"template_{template_id_counter:06d}",
                        "name": template_meta.get('title', ''),
                        "usage": scenario_name,
                        "doc_type": template_meta.get('doc_type', ''),
                        "sub_type": template_meta.get('sub_type', ''),
                        "template_id": template_meta.get('template_id', ''),
                        "system_prompt": self.extract_template_content(template_content),
                        "file_path": file_path,
                        "variables": self._extract_variables(template_content),
                        "example": self._extract_example(template_content)
                    }
                    
                    self.templates.append(template_record)
                    self.stats['successful'] += 1
                    template_id_counter += 1
                    
                except Exception as e:
                    self.error_log.append(f"处理模板 {file_path} 异常: {e}")
                    self.stats['failed'] += 1
    
    def _extract_variables(self, template_content: Dict) -> List[str]:
        """从模板中提取变量名"""
        variables = []
        
        # 尝试从模板中提取inputs/variables信息
        for field in ['inputs', 'variables', 'params', 'fields']:
            if field in template_content:
                items = template_content[field]
                if isinstance(items, dict):
                    variables.extend(items.keys())
                elif isinstance(items, list):
                    for item in items:
                        if isinstance(item, dict) and 'name' in item:
                            variables.append(item['name'])
        
        return list(set(variables))  # 去重
    
    def _extract_example(self, template_content: Dict) -> str:
        """从模板中提取示例"""
        for field in ['example', 'demo', 'sample', 'output_example']:
            if field in template_content:
                return str(template_content[field])[:500]  # 限制长度
        return ""
    
    def save_to_jsonl(self, output_path: str):
        """保存为JSONL格式"""
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                for template in self.templates:
                    f.write(json.dumps(template, ensure_ascii=False) + '\n')
            print(f"✓ 成功导出 {len(self.templates)} 个模板到 {output_path}")
        except Exception as e:
            self.error_log.append(f"保存JSONL文件失败: {e}")
    
    def save_stats(self, output_path: str):
        """保存处理统计信息"""
        stats = {
            **self.stats,
            'error_count': len(self.error_log),
            'errors': self.error_log[:50]  # 仅保留前50条错误
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
        print("开始处理模板库...")
        print("=" * 60)
        
        self.process_index()
        
        output_file = os.path.join(output_dir, 'templates_import.jsonl')
        stats_file = os.path.join(output_dir, 'templates_stats.json')
        
        self.save_to_jsonl(output_file)
        self.save_stats(stats_file)
        
        print("\n处理统计:")
        print(f"  总处理数: {self.stats['total_processed']}")
        print(f"  成功: {self.stats['successful']}")
        print(f"  失败: {self.stats['failed']}")
        
        if self.error_log:
            print(f"\n前5条错误:")
            for err in self.error_log[:5]:
                print(f"  - {err}")
        
        return output_file


if __name__ == "__main__":
    import sys
    
    # 项目根目录
    project_root = Path(__file__).parent
    output_dir = project_root / 'data_prep'
    
    processor = TemplateProcessor(str(project_root))
    processor.run(str(output_dir))
