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

    # 07 章 v2 §1.1/1.2/1.3、09 章§4.1（11 章 P1.3）：depth/enforce/w_layer + 最小挂钩链。
    # 现有库尚未打标（P1.4 才回填），所以不进 REQUIRED_FIELDS——只要字段出现就校验取值，
    # 不出现不算错，避免还没回填就把全库判不合格。
    if "depth" in rec:
        depth = rec["depth"]
        if depth not in vocab.DEPTH_VALUES:
            errors.append(f"depth 非法: {depth}（应为 {vocab.DEPTH_VALUES} 之一）")
        else:
            if depth == "axiom":
                governs = rec.get("governs")
                if not isinstance(governs, list) or not governs:
                    errors.append("depth=axiom 必须填 governs（管辖的大类数组，如 [1,3,4]）")
                elif any(g not in vocab.CATEGORY_NAMES for g in governs):
                    errors.append(f"governs 含非法大类: {governs}")
            elif depth == "technique":
                implements = rec.get("implements")
                if not isinstance(implements, list) or not implements:
                    errors.append("depth=technique 必须填 implements（挂靠的 method id 数组）")
                elif any(not ID_RE.match(i) for i in implements):
                    errors.append(f"implements 含非法 id 格式: {implements}")
            elif depth in ("method", "principle"):
                derives = rec.get("derives_from")
                if not isinstance(derives, list) or not derives:
                    errors.append(f"depth={depth} 必须填 derives_from（挂靠上一级 id 数组）")
                elif any(not ID_RE.match(d) for d in derives):
                    errors.append(f"derives_from 含非法 id 格式: {derives}")

    if "enforce" in rec and rec["enforce"] not in vocab.ENFORCE_VALUES:
        errors.append(f"enforce 非法: {rec['enforce']}（应为 {vocab.ENFORCE_VALUES} 之一）")

    if "w_layer" in rec:
        wl = rec["w_layer"]
        if not isinstance(wl, list) or not wl or any(w not in vocab.W_LAYER_VALUES for w in wl):
            errors.append(f"w_layer 须为 {vocab.W_LAYER_VALUES} 的非空子集: {wl}")

    return errors


def validate_article(rec: dict) -> list:
    """范文库 articles.jsonl 单条校验（04 章§4.1 字段 + 讲话类 subtype/skeleton/must_haves）。"""
    errors = []
    for f in vocab.ARTICLE_REQUIRED:
        empty = (None, "") if f == "linked_qa" else (None, "", [])  # linked_qa 允许空列表
        if f not in rec or rec[f] in empty:
            errors.append(f"缺字段或为空: {f}")
    if errors:
        return errors
    if not re.match(vocab.ARTICLE_ID_PATTERN, rec["id"]):
        errors.append(f"id 须为 AR-NNNN: {rec['id']}")
    if rec["doc_type"] not in vocab.DOC_TYPES:
        errors.append(f"doc_type 不在受控词表: {rec['doc_type']}")
    if rec["doc_type"] == "讲话稿" and rec["subtype"] not in vocab.SPEECH_SUBTYPES:
        errors.append(f"讲话稿 subtype 须为 {vocab.SPEECH_SUBTYPES}: {rec['subtype']}")
    if rec["org_level"] not in vocab.ORG_LEVELS:
        errors.append(f"org_level 须为 {vocab.ORG_LEVELS}: {rec['org_level']}")
    if rec["grade"] not in vocab.ARTICLE_GRADES:
        errors.append(f"grade 须为 {vocab.ARTICLE_GRADES}（C 级不入库）: {rec['grade']}")
    if rec["grade"] == "B" and not rec.get("caveat"):
        errors.append("grade=B 须写 caveat（短板）")
    for f, (lo, hi) in (("why_good", vocab.ARTICLE_WHY_GOOD_COUNT), ("must_haves", vocab.ARTICLE_MUST_HAVES_COUNT)):
        v = rec[f]
        if not isinstance(v, list) or not lo <= len(v) <= hi:
            errors.append(f"{f} 须为 {lo}—{hi} 条的列表")
    if not isinstance(rec["skeleton"], list) or len(rec["skeleton"]) < 2:
        errors.append("skeleton 须为至少 2 个一级标题的列表")
    if not isinstance(rec["linked_qa"], list) or any(not ID_RE.match(q) for q in rec["linked_qa"]):
        errors.append(f"linked_qa 须为 QA id 列表: {rec['linked_qa']}")
    if not (common.project_root() / rec["source_path"]).exists():
        errors.append(f"source_path 不存在: {rec['source_path']}")
    text = json.dumps(rec, ensure_ascii=False)
    if re.search(r"[「」『』]", text):
        errors.append("含「」『』，中文引号须用弯引号")
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
        errs = validate_article(rec) if path.name == vocab.ARTICLE_FILENAME else validate_record(rec)
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
