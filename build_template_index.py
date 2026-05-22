#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Build a usage-scenario-based index for the template library.
Scans all 151 JSON templates and generates a searchable index organized by:
- 汇报类 (reports)
- 讲话类 (speeches)  
- 方案类 (plans)
- 报告类 (formal reports)
- 其他
"""

import json
import os
from pathlib import Path
from collections import defaultdict

BASE_DIR = Path("d:/projects/Public_Writing_KB")
TEMPLATES_DIR = BASE_DIR / "01_templates"
OUTPUT_FILE = TEMPLATES_DIR / "by_usage_index.json"

# Define scenario mapping based on doc_type and sub_type
SCENARIO_KEYWORDS = {
    "汇报类": {
        "keywords": ["汇报", "工作汇报", "情况汇报", "总体汇报"],
        "doc_types": ["汇报"]
    },
    "讲话类": {
        "keywords": ["讲话", "发言", "致辞", "开幕", "闭幕", "总结讲话", "主持词"],
        "doc_types": ["讲话", "发言", "主持词", "致辞"]
    },
    "方案类": {
        "keywords": ["方案", "实施方案", "工作方案", "推进方案"],
        "doc_types": ["方案", "工作方案"]
    },
    "报告类": {
        "keywords": ["报告", "调研报告", "总结报告", "工作报告"],
        "doc_types": ["报告", "调研报告"]
    },
    "计划类": {
        "keywords": ["计划", "工作计划", "年度计划"],
        "doc_types": ["计划", "工作计划"]
    },
}

def classify_template(template_meta):
    """
    Classify a template into a usage scenario based on its metadata.
    
    Returns:
        list: List of applicable scenarios
    """
    scenarios = []
    title = template_meta.get('title', '').lower()
    doc_type = template_meta.get('doc_type', '').lower()
    sub_type = template_meta.get('sub_type', '').lower()
    
    for scenario, config in SCENARIO_KEYWORDS.items():
        # Check keywords in title and doc_type
        for keyword in config['keywords']:
            if keyword.lower() in title or keyword.lower() in doc_type or keyword.lower() in sub_type:
                scenarios.append(scenario)
                break
        
        # Check doc_types
        for doc_type_check in config['doc_types']:
            if doc_type_check.lower() in doc_type or doc_type_check.lower() in sub_type:
                if scenario not in scenarios:
                    scenarios.append(scenario)
                break
    
    # Default to "其他" if no match
    if not scenarios:
        scenarios.append("其他")
    
    return scenarios

def scan_templates():
    """
    Scan all template files in the templates directory.
    
    Returns:
        dict: Mapping of template file paths to their metadata
    """
    all_templates = {}
    
    # Recursively scan for JSON files
    for template_path in TEMPLATES_DIR.rglob("*.json"):
        try:
            with open(template_path, 'r', encoding='utf-8') as f:
                template_meta = json.load(f)
            
            # Store relative path and metadata
            rel_path = str(template_path.relative_to(TEMPLATES_DIR)).replace('\\', '/')
            all_templates[rel_path] = template_meta
        except Exception as e:
            print(f"  [WARN] Failed to read {template_path}: {e}")
    
    return all_templates

def build_index():
    """
    Build and save the usage-scenario-based index.
    """
    print("Building template usage index...")
    
    # Scan all templates
    all_templates = scan_templates()
    print(f"Found {len(all_templates)} templates")
    
    # Organize by scenario
    index_by_scenario = defaultdict(list)
    
    for rel_path, metadata in all_templates.items():
        scenarios = classify_template(metadata)
        
        for scenario in scenarios:
            entry = {
                "file_path": rel_path,
                "template_id": metadata.get('template_id'),
                "title": metadata.get('title'),
                "doc_type": metadata.get('doc_type'),
                "sub_type": metadata.get('sub_type'),
            }
            index_by_scenario[scenario].append(entry)
    
    # Print summary
    print("\n=== 模板库场景化索引统计 ===")
    total = 0
    for scenario in sorted(index_by_scenario.keys()):
        count = len(index_by_scenario[scenario])
        total += count
        print(f"  {scenario}: {count} 个模板")
    print(f"  总计: {total} 个模板")
    
    # Create the final index structure
    index = {
        "metadata": {
            "name": "Public Writing KB - Template Usage Index",
            "version": "1.0",
            "generated_at": "2026-03-16",
            "total_templates": total
        },
        "scenarios": {}
    }
    
    for scenario, templates in sorted(index_by_scenario.items()):
        index["scenarios"][scenario] = {
            "count": len(templates),
            "templates": templates
        }
    
    # Save to JSON file
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(index, f, ensure_ascii=False, indent=2)
    
    print(f"\n✅ Index saved to: {OUTPUT_FILE}")
    return index

if __name__ == "__main__":
    build_index()
