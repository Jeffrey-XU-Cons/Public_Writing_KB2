"""Mark a batch's QA records as human-reviewed (SOP step ⑦ completion).

Sets quality_checked=true (optionally quality_grade) for every record whose
batch_id matches, across all category files, then re-validates + audits.
This is the interim path until kb_editor.py exists; it honours the ADR-015
rule "any JSONL edit must be immediately followed by kb_validate".

CLI:  python tools/kb_mark_checked.py --batch B-20260706-01 [--grade A]
"""

import argparse
import json
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import common
import vocab
import kb_audit
from kb_validate import validate_record


def mark_batch(batch_id: str, grade: str | None = None) -> int:
    today = date.today().isoformat()
    touched = 0
    changed_files = {}  # path -> new text (staged before atomic write)

    for f in sorted(common.qa_dir().glob("c[1-6]_*.jsonl")):
        lines = f.read_text(encoding="utf-8").splitlines()
        out, hit = [], False
        for line in lines:
            if not line.strip():
                continue
            rec = json.loads(line)
            if rec.get("batch_id") == batch_id:
                rec["quality_checked"] = True
                if grade:
                    rec["quality_grade"] = grade
                rec["updated"] = today
                errs = validate_record(rec)      # gate: never write an invalid record
                if errs:
                    print(f"ERROR [{rec['id']}] 标记后校验失败: {errs}")
                    return 1
                hit = True
                touched += 1
            out.append(json.dumps(rec, ensure_ascii=False))
        if hit:
            changed_files[f] = "\n".join(out) + "\n"

    if not touched:
        print(f"未找到 batch_id={batch_id} 的记录")
        return 1

    for f, text in changed_files.items():          # atomic write per file
        tmp = f.with_suffix(".jsonl.tmp")
        tmp.write_text(text, encoding="utf-8")
        tmp.replace(f)

    errors, warnings = kb_audit.audit(fast=False)
    if errors:
        print(f"ERROR 标记后全量 audit {len(errors)} 个错误：")
        for e in errors:
            print(f"  {e}")
        return 1

    g = f"，grade→{grade}" if grade else ""
    print(f"已标记 {touched} 条为已抽检（batch={batch_id}{g}）；audit 0E/{len(warnings)}W")
    return 0


def main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument("--batch", required=True)
    ap.add_argument("--grade", choices=vocab.QUALITY_GRADES)
    args = ap.parse_args(argv)
    return mark_batch(args.batch, args.grade)


if __name__ == "__main__":
    common.force_utf8_stdout()
    sys.exit(main(sys.argv[1:]))
