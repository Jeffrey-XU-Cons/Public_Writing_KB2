#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
把萃取的中间格式（|||分隔）转成标准 CSV
用法: python3 scripts/to_csv.py output/萃取结果_中间格式.txt output/知识库.csv
验证: 检查列数、字段完整性、CSV可读性
"""
import csv
import sys
import os

def convert(input_file, output_file):
    with open(input_file, 'r', encoding='utf-8') as f:
        lines = [l.rstrip('\n') for l in f if l.strip()]

    if not lines:
        print("❌ 输入文件为空")
        return False

    # 解析
    rows = []
    errors = []
    for i, line in enumerate(lines):
        parts = line.split('|||')
        if len(parts) != 5:
            errors.append(f"  第{i+1}行：应有5列，实际{len(parts)}列")
            continue
        rows.append([p.strip() for p in parts])

    if errors:
        print("⚠️ 发现格式问题：")
        for e in errors:
            print(e)
        print("  （这些行会被跳过）\n")

    # 写 CSV（用 utf-8-sig，Excel 打开不乱码）
    with open(output_file, 'w', encoding='utf-8-sig', newline='') as f:
        writer = csv.writer(f)
        writer.writerows(rows)

    # 验证
    header = rows[0]
    data_rows = rows[1:]
    print(f"✅ 转换完成：{output_file}")
    print(f"   表头：{' | '.join(header)}")
    print(f"   数据行：{len(data_rows)} 条问答对")

    # 字段完整性检查
    bad = []
    for i, row in enumerate(data_rows):
        if not row[0] or not row[1]:  # 问题、答案不能空
            bad.append(i+1)
    if bad:
        print(f"   ⚠️ 第 {bad} 条的问题或答案为空")
    else:
        print(f"   ✅ 所有问答对的问题/答案字段完整")

    # 关键词口语检查（提醒）
    print(f"\n   字段长度统计：")
    avg_a = sum(len(r[1]) for r in data_rows) / len(data_rows)
    avg_k = sum(len(r[2].split(',')) for r in data_rows) / len(data_rows)
    print(f"   - 答案平均 {avg_a:.0f} 字")
    print(f"   - 关键词平均 {avg_k:.1f} 个/条")

    return True

if __name__ == '__main__':
    if len(sys.argv) < 3:
        # 默认路径
        here = os.path.dirname(os.path.abspath(__file__))
        root = os.path.dirname(here)
        inp = os.path.join(root, 'output', '萃取结果_中间格式.txt')
        out = os.path.join(root, 'output', '知识库.csv')
    else:
        inp, out = sys.argv[1], sys.argv[2]
    convert(inp, out)
