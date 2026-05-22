#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
行业文档精选脚本 v1.1
用途：从3402个MD文件中筛选高质量文档，输出候选清单供人工确认
修订：年份放宽至2017年以后均可，不做年份降权
用法：python select_industry_docs.py
输出：selection_candidates.md（候选清单）
"""

import os
import re
from pathlib import Path
from datetime import datetime
from collections import defaultdict

# ── 配置 ─────────────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).parent
RAW_DIR = PROJECT_ROOT / "00_raw_materials"
OUTPUT_FILE = PROJECT_ROOT / "selection_candidates.md"

# 目标分类（参考资料不在其中）
TARGET_CATEGORIES = [
    "汇报材料",
    "工作总结",
    "实施方案",
    "发展规划",
    "调研报告",
    "现场会讲话",
]

# 每个分类的目标精选数量
CATEGORY_TARGETS = {
    "汇报材料": 50,
    "工作总结": 40,
    "实施方案": 50,
    "发展规划": 30,
    "调研报告": 20,
    "现场会讲话": 50,
}

# 最低字数要求
MIN_CHARS = 800

# 有效年份范围（2017年以后均可）
VALID_YEAR_START = 2017

# 优先关键词（出现得分+2）
PRIORITY_KEYWORDS = [
    "国家局", "省局", "总公司",
    "工业企业", "中烟", "烟草工业",
    "高质量发展", "现代化建设",
    "管理提升", "效能攻坚", "精益管理",
    "品牌", "营销", "市场",
    "规划", "战略", "部署",
    "行业", "烟草商业", "烟草工商",
]

# 降权关键词（出现得分-2，这类文档质量低或不相关）
DEPRIORITY_KEYWORDS = [
    "签到", "酒店菜单", "费用报销",
    "接待方案", "餐饮安排", "会务手册",
    "差旅费", "住宿标准",
]

# 排除关键词（出现直接跳过）
EXCLUDE_KEYWORDS = [
    "签到表", "座位表", "日程安排表",
]


def extract_year(text: str, filename: str) -> int:
    """从文本或文件名中提取年份，返回整数，找不到返回0"""
    # 先从文件名找
    year_match = re.search(r"(201[7-9]|202[0-9])", filename)
    if year_match:
        return int(year_match.group(1))
    # 再从文本前300字找
    year_match = re.search(r"(201[7-9]|202[0-9])", text[:300])
    if year_match:
        return int(year_match.group(1))
    return 0


def score_document(content: str, filename: str) -> tuple:
    """
    给文档打分，返回（总分，评分明细字典）
    返回 -1 表示直接排除
    """
    score = 0
    details = {}

    # ── 排除检查 ──────────────────────────────────────────────
    # 排除关键词检查（直接跳过）
    for kw in EXCLUDE_KEYWORDS:
        if kw in content[:200]:
            return -1, {"排除原因": f"含排除词「{kw}」"}

    # ── 字数检查 ──────────────────────────────────────────────
    char_count = len(content.replace(" ", "").replace("\n", ""))
    if char_count < MIN_CHARS:
        return -1, {"排除原因": f"字数不足（{char_count}字，最低{MIN_CHARS}字）"}

    if char_count >= 5000:
        score += 4
        details["字数"] = f"{char_count}字（+4）"
    elif char_count >= 3000:
        score += 3
        details["字数"] = f"{char_count}字（+3）"
    elif char_count >= 1500:
        score += 2
        details["字数"] = f"{char_count}字（+2）"
    else:
        score += 1
        details["字数"] = f"{char_count}字（+1）"

    # ── 年份检查 ──────────────────────────────────────────────
    year = extract_year(content, filename)
    if year > 0 and year < VALID_YEAR_START:
        return -1, {"排除原因": f"年份过早（{year}年，最早{VALID_YEAR_START}年）"}
    if year > 0:
        details["年份"] = f"{year}年"
    else:
        details["年份"] = "年份未识别"

    # ── 优先关键词得分 ─────────────────────────────────────────
    priority_hits = [kw for kw in PRIORITY_KEYWORDS if kw in content[:3000]]
    if priority_hits:
        kw_score = min(len(priority_hits) * 2, 8)  # 最多+8
        score += kw_score
        details["优先词"] = f"{priority_hits[:6]}（+{kw_score}）"
    else:
        details["优先词"] = "无"

    # ── 降权关键词 ─────────────────────────────────────────────
    depriority_hits = [kw for kw in DEPRIORITY_KEYWORDS if kw in content[:500]]
    if depriority_hits:
        deduct = len(depriority_hits) * 2
        score -= deduct
        details["降权词"] = f"{depriority_hits}（-{deduct}）"

    # ── 结构完整性 ─────────────────────────────────────────────
    # 有层级标题（Markdown #号 或 中文数字标题）
    has_md_section = bool(re.search(r"^#{1,3}\s+\S", content, re.MULTILINE))
    has_cn_section = bool(re.search(r"^[一二三四五六七八九十]+[、．.]\s*\S", content, re.MULTILINE))
    if has_md_section or has_cn_section:
        score += 2
        details["结构"] = "有层级标题（+2）"
    else:
        details["结构"] = "无层级标题（+0）"

    # 有「一是/二是/三是」分条表述（烟草行业典型格式）
    has_yi_er = bool(re.search(r"一是.{5,30}[，。].*二是", content, re.DOTALL))
    if has_yi_er:
        score += 2
        details["分条"] = "有「一是/二是」格式（+2）"

    # 有数据（含数字+单位或百分号）
    has_data = bool(re.search(r"\d+[\.，,]\d*[%％万亿箱担元]|\d+个百分点", content))
    if has_data:
        score += 1
        details["数据"] = "含数据（+1）"

    # ── 文档级别判断 ───────────────────────────────────────────
    # 省局级及以上得分更高
    high_level_kws = ["国家局", "省局党组", "总公司党组", "行业工作会议", "全国烟草"]
    if any(kw in content[:1000] for kw in high_level_kws):
        score += 3
        details["级别"] = "省局级及以上（+3）"

    return score, details


def get_title(content: str, filename: str) -> str:
    """提取文档标题"""
    # 从YAML frontmatter提取
    fm_match = re.search(r"^title:\s*['\"]?(.+?)['\"]?\s*$", content[:500], re.MULTILINE)
    if fm_match:
        title = fm_match.group(1).strip()
        if len(title) > 3:
            return title

    # 从第一个#标题提取
    h1_match = re.search(r"^#\s+(.+)$", content, re.MULTILINE)
    if h1_match:
        title = h1_match.group(1).strip()
        if len(title) > 3:
            return title

    # 从第一个##标题提取
    h2_match = re.search(r"^##\s+(.+)$", content, re.MULTILINE)
    if h2_match:
        return h2_match.group(1).strip()

    # 用文件名（去掉扩展名和日期）
    stem = Path(filename).stem
    stem = re.sub(r"\d{4}[-./]\d{1,2}[-./]\d{1,2}", "", stem).strip()
    return stem[:50] if stem else filename


def scan_category(category: str) -> list:
    """扫描一个分类目录，返回所有有效文档的评分结果"""
    cat_dir = RAW_DIR / category
    if not cat_dir.exists():
        print(f"  ⚠️ 目录不存在：{cat_dir}")
        return []

    results = []
    excluded_count = 0
    md_files = list(cat_dir.rglob("*.md"))
    print(f"  扫描 {category}：{len(md_files)} 个文件")

    for md_file in md_files:
        try:
            content = md_file.read_text(encoding="utf-8", errors="ignore")
            score, details = score_document(content, md_file.name)

            if score < 0:
                excluded_count += 1
                continue

            title = get_title(content, md_file.name)
            char_count = len(content.replace(" ", "").replace("\n", ""))
            year = extract_year(content, md_file.name)

            results.append({
                "score": score,
                "title": title[:60],
                "filename": md_file.name,
                "path": str(md_file.relative_to(PROJECT_ROOT)),
                "chars": char_count,
                "year": year if year > 0 else "未知",
                "details": details,
            })

        except Exception as e:
            excluded_count += 1

    print(f"    有效：{len(results)} 篇，排除：{excluded_count} 篇")
    results.sort(key=lambda x: x["score"], reverse=True)
    return results


def generate_report(all_results: dict) -> str:
    """生成Markdown格式的候选清单"""
    lines = []
    lines.append("# 行业文档精选候选清单")
    lines.append(f"**生成时间：** {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    lines.append("")
    lines.append("## 使用说明")
    lines.append("")
    lines.append("每个分类按得分排序（得分越高质量越好）。")
    lines.append("操作方式：")
    lines.append("- 确认保留：在文件旁标注 ✅")
    lines.append("- 排除：在文件旁标注 ❌")
    lines.append("- 不确定：保持空白，后续再决定")
    lines.append("")
    lines.append("确认完成后，回到 Claude Project 告知，我来生成批量复制脚本。")
    lines.append("")
    lines.append("---")
    lines.append("")

    total_candidates = 0

    for category in TARGET_CATEGORIES:
        results = all_results.get(category, [])
        target = CATEGORY_TARGETS.get(category, 40)
        candidates = results[:target]  # 取前N名作为候选
        total_candidates += len(candidates)

        lines.append(f"## {category}")
        lines.append(f"**扫描总数：** {len(results)} 篇有效文档 | **候选数：** {len(candidates)} 篇 | **目标精选：** {target} 篇")
        lines.append("")

        if not candidates:
            lines.append("_未找到符合条件的文档_")
            lines.append("")
            continue

        lines.append("| 序号 | 得分 | 年份 | 字数 | 文档标题 | 文件路径 | 确认 |")
        lines.append("|------|------|------|------|---------|---------|------|")

        for i, doc in enumerate(candidates, 1):
            title = doc["title"].replace("|", "｜")
            path = doc["path"].replace("|", "｜")
            lines.append(
                f"| {i} | {doc['score']} | {doc['year']} | "
                f"{doc['chars']} | {title} | `{path}` |  |"
            )

        lines.append("")
        lines.append("<details>")
        lines.append("<summary>查看评分明细（点击展开）</summary>")
        lines.append("")
        for i, doc in enumerate(candidates[:10], 1):  # 只显示前10的明细
            lines.append(f"**{i}. {doc['title']}**")
            for k, v in doc["details"].items():
                lines.append(f"- {k}：{v}")
            lines.append("")
        lines.append("</details>")
        lines.append("")
        lines.append("---")
        lines.append("")

    # 汇总
    lines.insert(10, f"**候选文档总数：** {total_candidates} 篇（需人工确认后精选）")
    lines.insert(11, "")

    return "\n".join(lines)


# ════════════════════════════════════
# 主程序
# ════════════════════════════════════

if __name__ == "__main__":
    print("=" * 55)
    print("行业文档精选脚本 v1.1")
    print(f"年份范围：{VALID_YEAR_START}年至今")
    print(f"最低字数：{MIN_CHARS}字")
    print("=" * 55)
    print()

    all_results = {}

    for category in TARGET_CATEGORIES:
        all_results[category] = scan_category(category)

    print()
    print("正在生成候选清单...")
    report = generate_report(all_results)

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(report)

    print(f"✅ 候选清单已生成：{OUTPUT_FILE}")
    print()
    print("各分类候选数量：")
    for category in TARGET_CATEGORIES:
        results = all_results.get(category, [])
        target = CATEGORY_TARGETS.get(category, 40)
        candidates = min(len(results), target)
        print(f"  {category}：{candidates} 篇候选（共 {len(results)} 篇有效）")
    print()
    print("请将 selection_candidates.md 打开，逐条确认后回到 Claude Project。")
