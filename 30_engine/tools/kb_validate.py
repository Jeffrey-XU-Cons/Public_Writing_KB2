"""QA schema validator (ADR-001/002/014/015).

validate_record() is the single validation function reused by
kb_ingest.py (batch entry) and the future kb_editor.py (save gate).
CLI: python tools/kb_validate.py [file.jsonl ...]  — no args = whole library.
Exit code 0 only if every record passes.
"""

import hashlib
import json
import re
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import common
import vocab

ID_RE = re.compile(r"^QA-C[1-6]-\d{5}$")
BATCH_RE = re.compile(r"^B-\d{8}-\d{2}$")
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")

REQUIRED_FIELDS = [
    "id", "question", "answer", "answer_type", "tags", "scenarios",
    "question_keywords", "category_l1", "category_l2", "doc_types",
    "source_path", "source_anchor", "extract_method",
    "quality_grade", "quality_checked", "batch_id", "status",
    "created", "updated", "answer_hash",
]


def answer_hash(answer: str) -> str:
    return hashlib.sha1(answer.encode("utf-8")).hexdigest()[:12]


def validate_record(rec: dict) -> list:
    """Return a list of error strings; empty list means the record is valid."""
    errors = []

    for field in REQUIRED_FIELDS:
        if field not in rec or rec[field] in (None, "", []):
            errors.append(f"缺失必填字段: {field}")
    if errors:
        return errors  # missing fields make further checks meaningless

    if not ID_RE.match(rec["id"]):
        errors.append(f"id 格式错误: {rec['id']}（应为 QA-C{{1-6}}-{{5位}}）")

    questions = [q.strip() for q in rec["question"].split(" / ") if q.strip()]
    lo, hi = vocab.QUESTION_COUNT
    if not (lo <= len(questions) <= hi):
        errors.append(f"问法数量 {len(questions)} 不在 {lo}-{hi} 范围")

    atype = rec["answer_type"]
    if atype not in vocab.ANSWER_TYPES:
        errors.append(f"answer_type 非法: {atype}")
    else:
        min_chars = vocab.ANSWER_MIN_CHARS[atype]
        alen = len(rec["answer"])
        if alen < min_chars:
            errors.append(f"答案 {alen} 字 < {atype}下限 {min_chars} 字")
        if alen > vocab.ANSWER_MAX_CHARS:
            errors.append(f"答案 {alen} 字 > 上限 {vocab.ANSWER_MAX_CHARS} 字（拆成多条或精简）")
        if atype in ("方法型", "拆解型"):
            if not any(re.search(vocab.REVERSE_QUESTION_PATTERN, q) for q in questions):
                errors.append("方法型/拆解型至少需 1 个反向问法（踩坑/误区/失败类）")

    if '"' in rec["answer"] or "'" in rec["answer"]:
        errors.append("答案含英文直引号（须用中文弯引号「」“”）")

    if not isinstance(rec["tags"], list) or not (
            vocab.TAGS_COUNT[0] <= len(rec["tags"]) <= vocab.TAGS_COUNT[1]):
        errors.append(f"tags 数量应为 {vocab.TAGS_COUNT[0]}-{vocab.TAGS_COUNT[1]} 个")

    if not isinstance(rec["question_keywords"], list) or not (
            vocab.KEYWORDS_COUNT[0] <= len(rec["question_keywords"]) <= vocab.KEYWORDS_COUNT[1]):
        errors.append(f"question_keywords 数量应为 {vocab.KEYWORDS_COUNT[0]}-{vocab.KEYWORDS_COUNT[1]} 个")

    for marker in vocab.SCENARIO_MARKERS:
        if marker not in rec["scenarios"]:
            errors.append(f"scenarios 缺少标记 {marker}")

    l1 = rec["category_l1"]
    if l1 not in vocab.CATEGORY_L2:
        errors.append(f"category_l1 非法: {l1}")
    elif rec["category_l2"] not in vocab.CATEGORY_L2[l1]:
        errors.append(f"category_l2「{rec['category_l2']}」不在 C{l1} 受控词表")

    if not isinstance(rec["doc_types"], list) or not rec["doc_types"]:
        errors.append("doc_types 须为非空数组")
    else:
        for dt in rec["doc_types"]:
            if dt not in vocab.DOC_TYPES:
                errors.append(f"doc_types 含非受控值: {dt}")

    src = Path(rec["source_path"])
    if not src.is_absolute():
        src = common.project_root() / src
    if not src.exists():
        errors.append(f"source_path 断链: {rec['source_path']}")

    if rec["extract_method"] not in vocab.EXTRACT_METHODS:
        errors.append(f"extract_method 非法: {rec['extract_method']}")
    if rec["status"] not in vocab.STATUS_VALUES:
        errors.append(f"status 非法: {rec['status']}")
    if rec["quality_grade"] not in vocab.QUALITY_GRADES:
        errors.append(f"quality_grade 非法: {rec['quality_grade']}")
    if not isinstance(rec["quality_checked"], bool):
        errors.append("quality_checked 须为布尔值")
    if not BATCH_RE.match(rec["batch_id"]):
        errors.append(f"batch_id 格式错误: {rec['batch_id']}")
    for field in ("created", "updated"):
        if not DATE_RE.match(str(rec[field])):
            errors.append(f"{field} 须为 YYYY-MM-DD")

    if rec["answer_hash"] != answer_hash(rec["answer"]):
        errors.append("answer_hash 与答案内容不符")

    return errors


def validate_file(path: Path) -> list:
    """Return [(line_no, record_id_or_None, [errors])] for every bad line."""
    problems = []
    for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            rec = json.loads(line)
        except json.JSONDecodeError as exc:
            problems.append((line_no, None, [f"JSON 解析失败: {exc}"]))
            continue
        errs = validate_record(rec)
        if errs:
            problems.append((line_no, rec.get("id"), errs))
    return problems


def main(argv):
    files = [Path(a) for a in argv] or sorted(common.qa_dir().glob("c[1-6]_*.jsonl"))
    total_bad = 0
    for f in files:
        if not f.exists():
            continue
        for line_no, rid, errs in validate_file(f):
            total_bad += 1
            head = f"{f.name}:{line_no}" + (f" [{rid}]" if rid else "")
            for e in errs:
                print(f"ERROR {head} {e}")
    if total_bad:
        print(f"校验失败：{total_bad} 条记录不合格")
        return 1
    print("校验通过：全部记录合格")
    return 0


if __name__ == "__main__":
    common.force_utf8_stdout()
    sys.exit(main(sys.argv[1:]))
