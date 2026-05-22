"""
Convert source data to Dify-supported formats (TXT/MD).
Run: python data_prep/convert_to_dify.py
Output files go to data_prep/dify_upload/

Fixes applied vs original:
- Templates: read directly from 01_templates/*.json (not the shallow JSONL index)
  so that prompt_template, variables, output_structure, quality_checklist are included
- Dictionary: filter out placeholder rows (用语=="用语") and 金句库 category entries
"""

import json
import os
import re
import glob

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "dify_upload")
os.makedirs(OUTPUT_DIR, exist_ok=True)

DATA_DIR = os.path.dirname(__file__)
PROJECT_DIR = os.path.dirname(DATA_DIR)


def read_jsonl(filename):
    path = os.path.join(DATA_DIR, filename)
    with open(path, encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def clean_prompt(text):
    """Remove PDF extraction artifacts from prompt_template."""
    lines = text.splitlines()
    cleaned = []
    for line in lines:
        # Skip page number artifacts like "第2页,共52页"
        if re.match(r"^第\d+页[，,]共\d+页$", line.strip()):
            continue
        # Skip lone markdown header artifacts and page markers
        stripped = line.strip()
        if re.match(r"^#{1,3}\s*(第\s*\d+\s*页[，,]?.*)?$", stripped):
            continue
        # Skip bare page references like "第2页" or "第18页,共"
        if re.match(r"^第\s*\d+\s*页", stripped):
            continue
        cleaned.append(line)
    # Remove trailing blank lines
    while cleaned and not cleaned[-1].strip():
        cleaned.pop()
    return "\n".join(cleaned)


# 1. 模板库 → templates.md
# Source: 01_templates/**/*.json (151 files with full prompt content)
# NOT from templates_import.jsonl which has empty system_prompt and no prompt_template
print("Converting templates...")
template_files = sorted(glob.glob(
    os.path.join(PROJECT_DIR, "01_templates", "**", "*.json"),
    recursive=True
))
# Exclude the index file
template_files = [f for f in template_files if "index" not in os.path.basename(f).lower()]

lines = ["# 公文写作模板库\n"]
for fpath in template_files:
    with open(fpath, encoding="utf-8") as f:
        t = json.load(f)

    title = t.get("title", "").strip()
    doc_type = t.get("doc_type", "")
    scenario = t.get("scenario", "")
    prompt_template = clean_prompt(t.get("prompt_template", ""))
    variables = t.get("variables", [])
    output_structure = t.get("output_structure", "")
    quality_checklist = t.get("quality_checklist", [])

    if not title:
        continue

    lines.append(f"## {title}")
    lines.append(f"- 文体类型：{doc_type}")
    if scenario and scenario != "通用":
        lines.append(f"- 适用场景：{scenario}")

    if prompt_template:
        lines.append("- Prompt指令：")
        for pl in prompt_template.splitlines():
            lines.append(f"  {pl}")

    if variables:
        var_names = []
        for v in variables:
            if isinstance(v, dict):
                var_names.append(v.get("name", ""))
            else:
                var_names.append(str(v))
        var_names = [n for n in var_names if n]
        if var_names:
            lines.append(f"- 必填变量：{' / '.join(var_names)}")

    if output_structure and output_structure != "按照标准公文结构":
        lines.append(f"- 输出结构：{output_structure}")

    if quality_checklist:
        lines.append(f"- 质量要求：{' | '.join(quality_checklist)}")

    lines.append("")

with open(os.path.join(OUTPUT_DIR, "templates.md"), "w", encoding="utf-8") as f:
    f.write("\n".join(lines))
print(f"  → templates.md ({len(template_files)} 条，来自01_templates/)")


# 2. 词典库 → dictionary.txt
# Fix: filter out placeholder rows (用语=="用语") and 金句库 category (wrong category)
print("Converting dictionary...")
dictionary = read_jsonl("dictionary_unified.jsonl")
lines = []
count = 0
skipped_placeholder = 0
skipped_wrong_cat = 0
for d in dictionary:
    category = d.get("category", "")

    # Skip 金句库 entries mixed into dictionary — they have no 用语 field
    if category == "金句库":
        skipped_wrong_cat += 1
        continue

    term = d.get("用语") or d.get("term", "")
    scene = d.get("适用场景", "")
    note = d.get("说明", "")

    # Skip placeholder/header rows where term is literally the field name
    if not term or term in ("用语", "term"):
        skipped_placeholder += 1
        continue

    # Skip rows where scene/note are placeholder values
    if scene == "示例" and note == "说明":
        skipped_placeholder += 1
        continue

    parts = [f"【{category}】{term}"]
    if scene:
        parts.append(f"适用场景：{scene}")
    if note:
        parts.append(f"说明：{note}")
    lines.append("  ".join(parts))
    lines.append("")
    count += 1

with open(os.path.join(OUTPUT_DIR, "dictionary.txt"), "w", encoding="utf-8") as f:
    f.write("\n".join(lines))
print(f"  → dictionary.txt ({count} 条有效，跳过占位行{skipped_placeholder}条、错误分类{skipped_wrong_cat}条)")


# 3. 语料段落 → corpus_paragraphs.txt
print("Converting corpus paragraphs...")
paragraphs = read_jsonl("corpus_paragraphs.jsonl")
lines = []
seen = set()
count = 0
for p in paragraphs:
    content = p.get("content", "").strip()
    if not content or content in seen:
        continue
    seen.add(content)
    source = p.get("source_file", "")
    position = p.get("position", "")
    category = p.get("category", "")
    header = f"[{category} | {source} | {position}]" if source else ""
    if header:
        lines.append(header)
    lines.append(content)
    lines.append("")
    count += 1

with open(os.path.join(OUTPUT_DIR, "corpus_paragraphs.txt"), "w", encoding="utf-8") as f:
    f.write("\n".join(lines))
print(f"  → corpus_paragraphs.txt ({count} 条，去重后)")


# 4. 金句库 → corpus_golden_sentences.txt
print("Converting golden sentences...")
golden = read_jsonl("corpus_golden_sentences.jsonl")
lines = []
seen = set()
count = 0
for g in golden:
    content = g.get("content", "").strip()
    if not content or content in seen:
        continue
    seen.add(content)
    quality = g.get("quality_score", "")
    category = g.get("category", "")
    tag_parts = []
    if category:
        tag_parts.append(category)
    if quality:
        tag_parts.append(f"质量{quality}")
    tag = f"[{' | '.join(tag_parts)}]" if tag_parts else ""
    if tag:
        lines.append(tag)
    lines.append(content)
    lines.append("")
    count += 1

with open(os.path.join(OUTPUT_DIR, "corpus_golden_sentences.txt"), "w", encoding="utf-8") as f:
    f.write("\n".join(lines))
print(f"  → corpus_golden_sentences.txt ({count} 条，去重后)")


# 5. 语料文档索引 → corpus_documents.txt
# Note: content field contains only filenames, not actual document text.
# This knowledge base serves as a document catalog only.
print("Converting corpus documents...")
documents = read_jsonl("corpus_documents.jsonl")
lines = ["语料库文档索引\n"]
by_category = {}
for d in documents:
    cat = d.get("category", "待分类")
    raw = d.get("content", "").strip()
    # content is "标题 标题.md" format — extract clean title
    name = raw.replace(".md", "").strip()
    parts = name.split("  ")
    name = parts[0].strip() if parts else name
    if not name:
        continue
    by_category.setdefault(cat, []).append(name)

for cat, names in sorted(by_category.items()):
    lines.append(f"【{cat}】")
    for name in names:
        lines.append(f"  - {name}")
    lines.append("")

with open(os.path.join(OUTPUT_DIR, "corpus_documents.txt"), "w", encoding="utf-8") as f:
    f.write("\n".join(lines))
print(f"  → corpus_documents.txt ({len(documents)} 条，仅文档目录索引，无正文)")


print(f"\n完成！文件已输出到 {OUTPUT_DIR}/")
print("上传顺序建议：")
print("  1. templates.md           → 知识库「模板库」")
print("  2. dictionary.txt         → 知识库「词典库」")
print("  3. corpus_documents.txt   → 知识库「语料文档索引」")
print("  4. corpus_paragraphs.txt  → 知识库「语料段落库」")
print("  5. corpus_golden_sentences.txt → 知识库「金句库」")
