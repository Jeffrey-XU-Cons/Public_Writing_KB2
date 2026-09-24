"""Single entry point for putting QA data into the library (ADR-015 SOP step ④-⑨).

Pipeline:  batches/B-xxx/raw_output.md  →  parse header + 10-column MD table
           →  build full records (auto id / answer_hash / dates)
           →  ADR-016: route each row to knowledge/qa/c{its own l1}_*.jsonl,
              so ONE batch (e.g. a whole book chapter) can span 六大类
           →  validate every record (kb_validate)
           →  exact-dup check (answer_hash vs library)
           →  atomic multi-file write; audit failure = roll back ALL files
           →  full audit;  nothing enters the library unless clean

Index build is skipped until the retrieval slice exists (printed as a notice).

CLI:  python tools/kb_ingest.py --batch batches/B-20260706-01 [--dry-run]
"""

import argparse
import json
import re
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import common
import vocab
import kb_audit
from kb_validate import answer_hash, validate_record

CELL_BR = re.compile(r"<br\s*/?>")


def parse_header(text: str) -> dict:
    """Parse the leading ``--- key: value ---`` block of raw_output.md.

    ADR-016: category_l1 is no longer a header field — it is a per-row column,
    because one batch may span multiple 六大类.
    """
    m = re.match(r"^---\s*\n(.*?)\n---\s*\n", text, re.S)
    if not m:
        raise ValueError("raw_output.md 缺少头部元数据块（--- 包围的 key: value 区）")
    meta = {}
    for line in m.group(1).splitlines():
        if ":" in line:
            k, v = line.split(":", 1)
            meta[k.strip()] = v.strip()
    for key in ("batch_id", "source_path", "extract_method"):
        if key not in meta:
            raise ValueError(f"头部元数据缺少 {key}")
    return meta


def split_row(line: str) -> list:
    """Split a MD table row on unescaped pipes; unescape ``\\|`` and ``<br>``."""
    cells, buf, i = [], [], 0
    while i < len(line):
        ch = line[i]
        if ch == "\\" and i + 1 < len(line) and line[i + 1] == "|":
            buf.append("|")
            i += 2
            continue
        if ch == "|":
            cells.append("".join(buf).strip())
            buf = []
        else:
            buf.append(ch)
        i += 1
    cells.append("".join(buf).strip())
    # leading/trailing pipe produce empty edge cells
    if cells and cells[0] == "":
        cells = cells[1:]
    if cells and cells[-1] == "":
        cells = cells[:-1]
    return [CELL_BR.sub("\n", c) for c in cells]


# ADR-016: category_l1 is now the first data column (10 columns total)
COLUMNS = ["category_l1", "question", "answer", "answer_type", "tags",
           "scenarios", "question_keywords", "category_l2", "doc_types", "source_anchor"]


def parse_table(text: str) -> list:
    """Return list of dicts for each data row of the 10-column table."""
    rows = []
    in_table = False
    for line in text.splitlines():
        s = line.strip()
        if not s.startswith("|"):
            in_table = False
            continue
        cells = split_row(s)
        if not in_table:
            # header row must contain 大类 (category_l1 header) and 问题
            if cells and "问题" in " ".join(cells) and len(cells) >= 10:
                in_table = "header"
            continue
        if in_table == "header":          # separator row |---|---|
            in_table = True
            continue
        if len(cells) != len(COLUMNS):
            raise ValueError(f"表格行列数 {len(cells)} ≠ {len(COLUMNS)}: {s[:60]}…")
        rows.append(dict(zip(COLUMNS, cells)))
    return rows


def next_seq(category_l1: int) -> int:
    """Highest existing sequence number in that category's JSONL file."""
    qa_file = common.qa_dir() / vocab.QA_FILENAMES[category_l1]
    seq = 0
    if qa_file.exists():
        for line in qa_file.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            rid = json.loads(line).get("id", "")
            m = re.match(rf"QA-C{category_l1}-(\d{{5}})$", rid)
            if m:
                seq = max(seq, int(m.group(1)))
    return seq


def build_records(meta: dict, rows: list) -> list:
    """Assign per-category ids (each 六大类 keeps its own running sequence)."""
    today = date.today().isoformat()
    seq_by_cat = {}
    records = []
    for i, row in enumerate(rows, 1):
        try:
            l1 = int(row["category_l1"])
        except (ValueError, TypeError):
            raise ValueError(f"第 {i} 行 category_l1 非整数: {row['category_l1']!r}")
        if l1 not in vocab.QA_FILENAMES:
            raise ValueError(f"第 {i} 行 category_l1 非法: {l1}（应为 1-6）")
        if l1 not in seq_by_cat:
            seq_by_cat[l1] = next_seq(l1)
        seq_by_cat[l1] += 1
        rec = {
            "id": f"QA-C{l1}-{seq_by_cat[l1]:05d}",
            "question": row["question"],
            "answer": row["answer"],
            "answer_type": row["answer_type"],
            "tags": [t for t in re.split("[；;]", row["tags"]) if t.strip()],
            "scenarios": row["scenarios"],
            "question_keywords": [k for k in re.split("[；;]", row["question_keywords"]) if k.strip()],
            "category_l1": l1,
            "category_l2": row["category_l2"],
            "doc_types": [d for d in re.split("[；;]", row["doc_types"]) if d.strip()],
            "source_path": meta["source_path"],
            "source_anchor": row["source_anchor"],
            "extract_method": meta["extract_method"],
            "quality_grade": "B",
            "quality_checked": False,
            "batch_id": meta["batch_id"],
            "status": "active",
            "created": today,
            "updated": today,
            "answer_hash": answer_hash(row["answer"]),
        }
        records.append(rec)
    return records


def library_hashes() -> set:
    """All answer_hash values across every category file (cross-category dedup)."""
    hashes = set()
    for f in common.qa_dir().glob("c[1-6]_*.jsonl"):
        for line in f.read_text(encoding="utf-8").splitlines():
            if line.strip():
                hashes.add(json.loads(line).get("answer_hash"))
    return hashes


def ingest_batch(batch_dir: Path, dry_run: bool = False) -> int:
    report_lines = []
    text = (batch_dir / "raw_output.md").read_text(encoding="utf-8")
    meta = parse_header(text)
    rows = parse_table(text)
    if not rows:
        print("ERROR raw_output.md 未解析到任何数据行")
        return 1

    records = build_records(meta, rows)

    # gate 1: schema validation
    bad = 0
    for rec in records:
        for e in validate_record(rec):
            report_lines.append(f"ERROR [{rec['id']}] {e}")
            bad += 1
    # gate 2: exact duplicates against the whole library (any category)
    lib_hashes = library_hashes()
    seen_in_batch = set()
    for rec in records:
        h = rec["answer_hash"]
        if h in lib_hashes:
            report_lines.append(f"ERROR [{rec['id']}] answer_hash 与库内已有记录重复")
            bad += 1
        if h in seen_in_batch:
            report_lines.append(f"ERROR [{rec['id']}] answer_hash 与本批另一条重复")
            bad += 1
        seen_in_batch.add(h)

    report = batch_dir / "check_report.md"
    if bad:
        report.write_text("# 批次校验报告（未通过）\n\n" + "\n".join(report_lines) + "\n",
                          encoding="utf-8")
        print(f"入库失败：{bad} 个错误，详见 {report}")
        return 1

    # group records by category → which JSONL files this batch touches
    by_cat = {}
    for rec in records:
        by_cat.setdefault(rec["category_l1"], []).append(rec)

    if dry_run:
        spread = "，".join(f"c{c}:{len(rs)}条" for c, rs in sorted(by_cat.items()))
        print(f"dry-run 通过：{len(records)} 条待入库（{spread}；未写入）")
        return 0

    # atomic multi-file write with all-or-nothing rollback
    common.qa_dir().mkdir(parents=True, exist_ok=True)
    originals = {}  # cat -> prior file text (None if new)
    for cat, recs in sorted(by_cat.items()):
        qa_file = common.qa_dir() / vocab.QA_FILENAMES[cat]
        originals[cat] = qa_file.read_text(encoding="utf-8") if qa_file.exists() else None
        lines = ([] if originals[cat] is None else originals[cat].splitlines())
        lines += [json.dumps(r, ensure_ascii=False) for r in recs]
        tmp = qa_file.with_suffix(".jsonl.tmp")
        tmp.write_text("\n".join(lines) + "\n", encoding="utf-8")
        tmp.replace(qa_file)

    errors, warnings = kb_audit.audit(fast=False)
    if errors:
        for cat, original in originals.items():          # roll back every touched file
            qa_file = common.qa_dir() / vocab.QA_FILENAMES[cat]
            if original is None:
                qa_file.unlink()
            else:
                qa_file.write_text(original, encoding="utf-8")
        report.write_text("# 批次校验报告（audit 未通过，已整批回滚）\n\n"
                          + "\n".join(errors) + "\n", encoding="utf-8")
        print(f"入库失败：audit {len(errors)} 个错误，本批已整体回滚，详见 {report}")
        return 1

    spread = "，".join(f"c{c}:{len(rs)}条" for c, rs in sorted(by_cat.items()))
    report.write_text(
        f"# 批次校验报告（通过）\n\n- 批次：{meta['batch_id']}\n"
        f"- 入库：{len(records)} 条，自动路由：{spread}\n"
        f"- audit：0 error / {len(warnings)} warning\n"
        f"- 提醒：索引层未建（切片阶段），检索切片就绪后重建索引\n", encoding="utf-8")
    print(f"入库成功：{len(records)} 条，自动路由 {spread}；audit 0E/{len(warnings)}W")
    print("提醒：索引层未建（切片阶段跳过 build）")
    return 0


def main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument("--batch", required=True, help="批次目录，如 batches/B-20260705-01")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args(argv)
    return ingest_batch(Path(args.batch), dry_run=args.dry_run)


if __name__ == "__main__":
    common.force_utf8_stdout()
    sys.exit(main(sys.argv[1:]))
