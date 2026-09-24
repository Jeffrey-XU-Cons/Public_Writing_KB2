#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
行业文档批量复制脚本 v1.0
用途：将精选文档从 00_raw_materials/ 复制到 knowledge/industry/
自动排除规则：
  1. 标题含「服务方案」「咨询方案」「技术方案」的咨询公司文件
  2. 标题含英文字母（行业外文件）
  3. 字数超过10万字的汇编文件
  4. 年份识别为2026但文件名含2015/2016特征的文件
用法：python copy_industry_docs.py
输出：
  - knowledge/industry/ 目录下按分类存放的精选文档
  - copy_report.md（复制结果报告）
"""

import re
import shutil
from pathlib import Path
from datetime import datetime
from collections import defaultdict

# ── 配置 ─────────────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).parent
RAW_DIR = PROJECT_ROOT / "00_raw_materials"
OUTPUT_DIR = PROJECT_ROOT / "knowledge" / "industry"
REPORT_FILE = PROJECT_ROOT / "copy_report.md"

# 目标分类
TARGET_CATEGORIES = [
    "汇报材料",
    "工作总结",
    "实施方案",
    "发展规划",
    "调研报告",
    "现场会讲话",
]

# 每个分类的最大数量上限
CATEGORY_LIMITS = {
    "汇报材料": 50,
    "工作总结": 40,
    "实施方案": 50,
    "发展规划": 30,
    "调研报告": 20,
    "现场会讲话": 50,
}

# 最低字数
MIN_CHARS = 800

# 最大字数（超过此值视为汇编文件）
MAX_CHARS = 100000

# 有效年份下限
VALID_YEAR_START = 2017

# ── 自动排除规则 ───────────────────────────────────────────────

# 规则1：标题含这些词的排除（咨询公司文件）
EXCLUDE_TITLE_KEYWORDS = [
    "服务方案", "咨询方案", "咨询服务", "技术方案",
    "项目服务方案", "答辩方案",
]

# 规则2：标题含英文字母比例过高的排除
def is_english_heavy(filename: str) -> bool:
    """文件名中英文字母超过30%且含有完整英文单词，判定为行业外文件"""
    stem = Path(filename).stem
    english_chars = sum(1 for c in stem if c.isalpha() and c.isascii())
    total_chars = len(stem.replace(" ", ""))
    if total_chars == 0:
        return False
    # 含完整英文单词（2个以上连续英文字母）且比例超过40%
    has_english_word = bool(re.search(r'[a-zA-Z]{3,}', stem))
    ratio = english_chars / total_chars
    return has_english_word and ratio > 0.4

# 规则3：字数超过10万字排除
# 在score_document里处理

# 规则4：文件名含有15xx/16xx特征（2015/2016年文件被误识别为2026年）
def is_misidentified_old_file(filename: str, content: str) -> bool:
    """文件名含150xxx/160xxx/161xxx等格式，说明是2015/2016年文件"""
    stem = Path(filename).stem
    # 匹配 1507xx, 1508xx, 1601xx, 1611xx 等格式（年月日缩写）
    if re.match(r'^1[456]\d{4}', stem):
        return True
    # 文件名前4字符是15xx或16xx（年份缩写）
    if re.match(r'^1[56]\d{2}', stem):
        return True
    return False

# ── 评分函数（同精选脚本）────────────────────────────────────

PRIORITY_KEYWORDS = [
    "国家局", "省局", "总公司",
    "工业企业", "中烟", "烟草工业",
    "高质量发展", "现代化建设",
    "管理提升", "效能攻坚", "精益管理",
    "品牌", "营销", "市场",
    "规划", "战略", "部署",
    "行业", "烟草商业", "烟草工商",
]

DEPRIORITY_KEYWORDS = [
    "签到", "酒店菜单", "费用报销",
    "接待方案", "餐饮安排", "会务手册",
]

EXCLUDE_KEYWORDS = ["签到表", "座位表", "日程安排表"]


def extract_year(text: str, filename: str) -> int:
    year_match = re.search(r"(201[7-9]|202[0-9])", filename)
    if year_match:
        return int(year_match.group(1))
    year_match = re.search(r"(201[7-9]|202[0-9])", text[:300])
    if year_match:
        return int(year_match.group(1))
    return 0


def score_document(content: str, filename: str) -> tuple:
    score = 0

    for kw in EXCLUDE_KEYWORDS:
        if kw in content[:200]:
            return -1, f"含排除词「{kw}」"

    char_count = len(content.replace(" ", "").replace("\n", ""))
    if char_count < MIN_CHARS:
        return -1, f"字数不足（{char_count}字）"
    if char_count > MAX_CHARS:
        return -1, f"字数超过10万（{char_count}字，疑为汇编文件）"

    year = extract_year(content, filename)
    if year > 0 and year < VALID_YEAR_START:
        return -1, f"年份过早（{year}年）"

    if char_count >= 5000:
        score += 4
    elif char_count >= 3000:
        score += 3
    elif char_count >= 1500:
        score += 2
    else:
        score += 1

    priority_hits = [kw for kw in PRIORITY_KEYWORDS if kw in content[:3000]]
    score += min(len(priority_hits) * 2, 8)

    depriority_hits = [kw for kw in DEPRIORITY_KEYWORDS if kw in content[:500]]
    score -= len(depriority_hits) * 2

    has_md_section = bool(re.search(r"^#{1,3}\s+\S", content, re.MULTILINE))
    has_cn_section = bool(re.search(r"^[一二三四五六七八九十]+[、．.]\s*\S", content, re.MULTILINE))
    if has_md_section or has_cn_section:
        score += 2

    has_yi_er = bool(re.search(r"一是.{5,30}[，。].*二是", content, re.DOTALL))
    if has_yi_er:
        score += 2

    has_data = bool(re.search(r"\d+[\.，,]\d*[%％万亿箱担元]|\d+个百分点", content))
    if has_data:
        score += 1

    high_level_kws = ["国家局", "省局党组", "总公司党组", "行业工作会议", "全国烟草"]
    if any(kw in content[:1000] for kw in high_level_kws):
        score += 3

    return score, "通过"


def should_exclude(filename: str, content: str) -> tuple:
    """
    返回 (是否排除, 排除原因)
    """
    stem = Path(filename).stem

    # 规则1：标题含咨询类关键词
    for kw in EXCLUDE_TITLE_KEYWORDS:
        if kw in stem or kw in content[:100]:
            return True, f"标题含咨询词「{kw}」"

    # 规则2：英文比例过高
    if is_english_heavy(filename):
        return True, "文件名英文比例过高（行业外文件）"

    # 规则4：文件名含2015/2016年格式特征
    if is_misidentified_old_file(filename, content):
        return True, "文件名含2015/2016年特征（年份误识别）"

    return False, ""


def scan_and_copy_category(category: str) -> dict:
    """扫描分类目录，筛选后复制到目标目录"""
    cat_src = RAW_DIR / category
    cat_dst = OUTPUT_DIR / category
    cat_dst.mkdir(parents=True, exist_ok=True)

    if not cat_src.exists():
        return {"category": category, "scanned": 0, "copied": 0,
                "excluded": [], "failed": [], "candidates": 0,
                "excluded_count": 0, "excluded_samples": [], "copied_list": []}

    limit = CATEGORY_LIMITS.get(category, 40)
    md_files = list(cat_src.rglob("*.md"))
    print(f"\n  [{category}] 扫描 {len(md_files)} 个文件，目标上限 {limit} 篇")

    # 收集有效文件并评分
    candidates = []
    excluded = []

    for md_file in md_files:
        try:
            content = md_file.read_text(encoding="utf-8", errors="ignore")

            # 先检查自动排除规则
            excluded_flag, reason = should_exclude(md_file.name, content)
            if excluded_flag:
                excluded.append({"file": md_file.name, "reason": reason})
                continue

            # 评分
            score, msg = score_document(content, md_file.name)
            if score < 0:
                excluded.append({"file": md_file.name, "reason": msg})
                continue

            char_count = len(content.replace(" ", "").replace("\n", ""))
            candidates.append({
                "score": score,
                "file": md_file,
                "name": md_file.name,
                "chars": char_count,
            })

        except Exception as e:
            excluded.append({"file": md_file.name, "reason": f"读取失败：{e}"})

    # 按得分排序，取前N名
    candidates.sort(key=lambda x: x["score"], reverse=True)
    selected = candidates[:limit]

    # 执行复制
    copied = []
    failed = []
    for item in selected:
        try:
            dst = cat_dst / item["name"]
            shutil.copy2(item["file"], dst)
            copied.append({"file": item["name"], "score": item["score"],
                          "chars": item["chars"]})
        except Exception as e:
            failed.append({"file": item["name"], "reason": str(e)})

    print(f"    排除：{len(excluded)} 篇 | 候选：{len(candidates)} 篇 | "
          f"复制：{len(copied)} 篇")

    return {
        "category": category,
        "scanned": len(md_files),
        "candidates": len(candidates),
        "copied": len(copied),
        "excluded_count": len(excluded),
        "excluded_samples": excluded[:10],
        "copied_list": copied,
        "failed": failed,
    }


def generate_report(results: list) -> str:
    lines = []
    lines.append("# 行业文档复制结果报告")
    lines.append(f"**执行时间：** {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    lines.append(f"**目标目录：** `knowledge/industry/`")
    lines.append("")

    total_copied = sum(r["copied"] for r in results)
    total_excluded = sum(r["excluded_count"] for r in results)
    lines.append(f"**总计复制：** {total_copied} 篇")
    lines.append(f"**总计排除：** {total_excluded} 篇")
    lines.append("")
    lines.append("---")
    lines.append("")

    for r in results:
        lines.append(f"## {r['category']}")
        lines.append(f"扫描：{r['scanned']} 篇 | 有效候选：{r['candidates']} 篇 | "
                    f"已复制：{r['copied']} 篇 | 排除：{r['excluded_count']} 篇")
        lines.append("")

        if r["copied_list"]:
            lines.append("**已复制文件（按得分排序）：**")
            lines.append("")
            lines.append("| 得分 | 字数 | 文件名 |")
            lines.append("|------|------|--------|")
            for item in r["copied_list"]:
                name = item["file"][:60]
                lines.append(f"| {item['score']} | {item['chars']} | {name} |")
            lines.append("")

        if r["excluded_samples"]:
            lines.append("<details>")
            lines.append("<summary>排除样本（前10条，点击展开）</summary>")
            lines.append("")
            for item in r["excluded_samples"]:
                lines.append(f"- `{item['file'][:50]}` → {item['reason']}")
            lines.append("")
            lines.append("</details>")
            lines.append("")

        if r["failed"]:
            lines.append(f"**复制失败：{len(r['failed'])} 篇**")
            for item in r["failed"]:
                lines.append(f"- {item['file']}：{item['reason']}")
            lines.append("")

        lines.append("---")
        lines.append("")

    lines.append("## 下一步")
    lines.append("")
    lines.append("1. 检查 `knowledge/industry/` 目录确认文件已就位")
    lines.append("2. 更新 `CLAUDE.md` 的知识库读取路径，加入 `knowledge/industry/` 分类目录")
    lines.append("3. 将两份提纲文件手动放入 `knowledge/outlines/` 目录")
    lines.append("4. 回到 Claude Project 告知完成，继续推进知识库集成")

    return "\n".join(lines)


# ════════════════════════════════════
# 主程序
# ════════════════════════════════════

if __name__ == "__main__":
    print("=" * 55)
    print("行业文档批量复制脚本 v1.0")
    print(f"来源：{RAW_DIR}")
    print(f"目标：{OUTPUT_DIR}")
    print("=" * 55)
    print()
    print("自动排除规则：")
    print("  1. 标题含「服务方案」「咨询方案」等咨询公司文件")
    print("  2. 文件名英文比例过高（行业外文件）")
    print("  3. 字数超过10万字（汇编文件）")
    print("  4. 文件名含2015/2016年格式特征（年份误识别）")
    print()

    # 创建输出目录
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # 同时创建提纲文件目录
    outlines_dir = PROJECT_ROOT / "knowledge" / "outlines"
    outlines_dir.mkdir(parents=True, exist_ok=True)

    all_results = []
    for category in TARGET_CATEGORIES:
        result = scan_and_copy_category(category)
        all_results.append(result)

    print("\n" + "=" * 55)
    print("复制完成汇总：")
    total = 0
    for r in all_results:
        print(f"  {r['category']}：{r['copied']} 篇")
        total += r["copied"]
    print(f"  合计：{total} 篇")

    print("\n生成报告...")
    report = generate_report(all_results)
    with open(REPORT_FILE, "w", encoding="utf-8") as f:
        f.write(report)

    print(f"✅ 报告已生成：{REPORT_FILE}")
    print()
    print("下一步：")
    print("  1. 检查 knowledge/industry/ 目录")
    print("  2. 将两份提纲文件手动放入 knowledge/outlines/")
    print("  3. 把 copy_report.md 粘贴回 Claude Project")
