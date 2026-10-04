"""Knowledge-base audit gate (heir of the old project's audit_kb_sources.py).

Checks (slice version — index checks join when the retrieval slice lands):
  A  every qa/*.jsonl and articles/articles.jsonl line parses as JSON
  B  every record passes kb_validate.validate_record   (skipped with --fast)
  C  global id uniqueness + answer_hash uniqueness
  D  hygiene: banned file names, root .md whitelist,
     skills referencing index/ directly                (skipped with --fast)

Exit 0 = clean (warnings allowed, listed); exit 1 = any error.
Wired in: kb_ingest.py runs this before keeping data; pre-commit runs --fast.
"""

import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import common
import vocab
from kb_validate import validate_article, validate_record

ROOT_MD_WHITELIST = {"CLAUDE.md", "ARCHITECTURE.md", "STATUS.md", "README.md",
                     "PROJECT_STRUCTURE.md"}  # CLAUDE.md 末行引用的目录说明

# 命名检查只管本项目产出的文件。原始素材（客户交付物原件，版本号本身是信息）、
# 前期归档与 legacy 存档保留原名，不在检查范围（2026-09-29 Jeffrey 裁定）。
NAMING_EXEMPT_TOP = {"10_source", "99_前期资料"}
NAMING_EXEMPT_ANY = {"legacy"}
# 外部迁入的原始语料同理：20_knowledge/corpus/（2026-10-03 Jeffrey 裁定；tobacco_kb 迁入件带 _v3 等原名）
NAMING_EXEMPT_PREFIXES = {("20_knowledge", "corpus")}


def audit(fast: bool = False):
    """Return (errors, warnings) as lists of strings."""
    errors, warnings = [], []
    root = common.project_root()

    seen_ids, seen_hashes = {}, {}
    for f in sorted(common.qa_dir().glob("c[1-6]_*.jsonl")):
        for line_no, line in enumerate(f.read_text(encoding="utf-8").splitlines(), 1):
            if not line.strip():
                continue
            try:
                rec = json.loads(line)
            except json.JSONDecodeError as exc:
                errors.append(f"[A] {f.name}:{line_no} JSON 解析失败: {exc}")
                continue

            rid = rec.get("id", f"{f.name}:{line_no}")
            if rid in seen_ids:
                errors.append(f"[C] id 重复: {rid}（{seen_ids[rid]} 与 {f.name}:{line_no}）")
            else:
                seen_ids[rid] = f"{f.name}:{line_no}"

            h = rec.get("answer_hash")
            if h:
                if h in seen_hashes and rec.get("status") == "active":
                    errors.append(f"[C] answer_hash 重复: {rid} 与 {seen_hashes[h]}")
                elif rec.get("status") == "active":
                    seen_hashes[h] = rid

            if not fast:
                for e in validate_record(rec):
                    errors.append(f"[B] {f.name}:{line_no} [{rid}] {e}")

    # 范文库：JSON 可解析、id 唯一、字段与 source_path 合格；linked_qa 必须指向存在的 QA
    art = common.articles_dir() / vocab.ARTICLE_FILENAME
    if art.exists():
        art_ids = set()
        for line_no, line in enumerate(art.read_text(encoding="utf-8").splitlines(), 1):
            if not line.strip():
                continue
            try:
                rec = json.loads(line)
            except json.JSONDecodeError as exc:
                errors.append(f"[A] {art.name}:{line_no} JSON 解析失败: {exc}")
                continue
            rid = rec.get("id", f"{art.name}:{line_no}")
            if rid in art_ids:
                errors.append(f"[C] 范文 id 重复: {rid}")
            art_ids.add(rid)
            if not fast:
                for e in validate_article(rec):
                    errors.append(f"[B] {art.name}:{line_no} [{rid}] {e}")
                for q in rec.get("linked_qa") or []:
                    if q not in seen_ids:
                        errors.append(f"[B] {art.name}:{line_no} [{rid}] linked_qa 指向不存在的 QA: {q}")

    if not fast:
        for p in root.rglob("*"):
            rel_parts = p.relative_to(root).parts
            if any(part.startswith(".") for part in rel_parts):
                continue  # 整个点号目录子树都跳过（.git/.venv/.claude…），不止顶层
            if (rel_parts[0] in NAMING_EXEMPT_TOP or NAMING_EXEMPT_ANY & set(rel_parts[:-1])
                    or any(rel_parts[:len(px)] == px for px in NAMING_EXEMPT_PREFIXES)):
                continue
            if re.search(vocab.BANNED_NAME_PATTERN, p.name):
                errors.append(f"[D] 禁用命名: {p.relative_to(root)}")

        for p in root.glob("*.md"):
            if p.name not in ROOT_MD_WHITELIST:
                errors.append(f"[D] 根目录出现白名单外文档: {p.name}（防文档增殖）")

        skills_dir = root / ".claude" / "skills"
        if skills_dir.exists():
            for p in skills_dir.rglob("*.md"):
                text = p.read_text(encoding="utf-8")
                if re.search(r"index[/\\](chroma|bm25)", text):
                    warnings.append(f"[D] skill 直接引用 index/ 路径: {p.relative_to(root)}")

    return errors, warnings


def main(argv):
    fast = "--fast" in argv
    errors, warnings = audit(fast=fast)
    for w in warnings:
        print(f"WARNING {w}")
    for e in errors:
        print(f"ERROR {e}")
    mode = "fast" if fast else "full"
    print(f"audit({mode}): {len(errors)} error / {len(warnings)} warning")
    return 1 if errors else 0


if __name__ == "__main__":
    common.force_utf8_stdout()
    sys.exit(main(sys.argv[1:]))
