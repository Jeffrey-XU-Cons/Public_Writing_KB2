"""Build de-identified batch r11 from r10 by applying ONLY the rules added on 2026-10-07.

Why: while annotating multi-genre exemplars (B-20261007-AR-02) four annotators read r10 sources and
reported leaks: member-list rows with spaced or bracket-annotated real names, an 11-digit mobile number,
consulting/local company names, county/town/station names and features that reveal the province,
cigarette spec names inside 〔品牌〕(…), document-number year+sequence, unmasked scale numbers (cases,
headcount, turnover, land area), plus tool defects: placeholder letters overflowing past Z into
〔[中烟〕〔\\厂〕〔c公司〕, “及时处置” mangled into “及〔姓名〕处置”, “17项处于” into “17〔姓名〕处于”.
deidentify.py now carries general rules for these (r11_rules, unit_letters, the SHORT_NAME_RE fix).
Re-running the whole pipeline on r10 output would re-process placeholders and numbers, so this script
applies just the new rules to r10 text and writes r11 next to it. r10 is left untouched.

Line structure is preserved: every rule substitutes inside a line, cross-line OCR splits keep their
newlines, CRLF stays CRLF. Exemplar records (articles.jsonl) cite r10/r11 by line number, so the script
aborts if any file's line count changes.

Inputs besides r10:
  <r11>/names_supplement_r11.txt  manual additions (names outside the surname table, typed entries such as
                                  “〔某企业〕Name”) — local only, gitignored with the batch.
Outputs in <r11>: the de-identified .md files, names_confirmed.txt (r10 list + supplement + person names
the new list/table rules found), deid_changes.jsonl (contains ORIGINAL strings — local only), scan_report.txt.

Re-runnable: overwrites what it wrote last time; never deletes. A stale .md from an earlier run that this
run no longer produces is reported, not removed.

Usage: python 30_engine/tools/migrations/20261007_deid_r10_to_r11.py
Then:  python 30_engine/tools/deid_scan.py <r11> --names <r11>/names_confirmed.txt   (hard leaks must be 0)
"""

import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import common  # noqa: E402
import deidentify as d  # noqa: E402
import deid_scan  # noqa: E402

BATCHES = common.project_root() / "30_engine" / "batches"
SRC = BATCHES / "B-20261004-deid-个人历史交付物-r10"
DST = BATCHES / "B-20261007-deid-个人历史交付物-r11"
SUPPLEMENT = DST / "names_supplement_r11.txt"

# r10 的两种误伤形态，按 r9 改动日志核实过原文（r9 deid_changes.jsonl：“时处”10 处、“项处”1 处）
MISFIRE_FIXES = [
    (re.compile(r"及〔姓名〕处(?=[置理])"), "及时处", "误伤复原（及时处置/处理）"),
    (re.compile(r"(?<=\d)〔姓名〕处(?=于)"), "项处", "误伤复原（N项处于）"),
]
_TITLE_PREFIX = re.compile(r"^(?:副)?(?:局长|经理|厂长|主任|书记|处长|科长|部长|总监)(?:（[^）]*）)?")


def read(p):
    raw = p.read_bytes().decode("utf-8")  # 按字节读，保留 CRLF（read_text 会把 \r\n 折成 \n）
    return raw.replace("\r\n", "\n"), "\r\n" in raw


def write(p, text, crlf):
    p.write_bytes((text.replace("\n", "\r\n") if crlf else text).encode("utf-8"))


def fix_misfires(text):
    changes = []
    for rx, new, tag in MISFIRE_FIXES:
        for m in rx.finditer(text):
            changes.append({"type": tag, "orig": m.group(0), "new": new})
        text = rx.sub(new, text)
    return text, changes


def patch(text, known, specs):
    text, ch1 = d.apply_known_names(text, known)
    text, ch2 = fix_misfires(text)
    text, ch3 = d.r11_rules(text, specs)
    return text, ch1 + ch2 + ch3


def person_names(changes):
    """新规则（名单行、人员表、括注、工作室、职务在前）认出的人名，补进 names_confirmed。"""
    found = set()
    for c in changes:
        if not c["type"].startswith("人名") or c["type"] == "人名(姓+职务)":
            continue
        name = re.sub(r"[ 　]", "", _TITLE_PREFIX.sub("", c["orig"]))
        if re.fullmatch(r"[一-龥]{2,3}", name) and d._is_name(name):
            found.add(name)
    return found


def main():
    DST.mkdir(exist_ok=True)
    sources = sorted(SRC.glob("*.md"))
    texts = {p: read(p) for p in sources}

    known = d.load_names_file(SRC / "names_confirmed.txt")
    if SUPPLEMENT.exists():
        known += d.load_names_file(SUPPLEMENT)
    specs = set()
    for text, _ in texts.values():
        specs |= d.harvest_specs(text)

    # 第一遍：收集新规则认出的人名
    harvested = set()
    for text, _ in texts.values():
        harvested |= person_names(patch(text, known, specs)[1])
    known_terms = {k for k, _ in known}
    new_names = sorted(harvested - known_terms)
    known += [(n, None) for n in new_names]

    lines = (SRC / "names_confirmed.txt").read_text(encoding="utf-8").rstrip("\n").split("\n")
    lines.append("# ---- 2026-10-07 r11 新增：人工补充（names_supplement_r11.txt）----")
    if SUPPLEMENT.exists():
        lines += [s for s in SUPPLEMENT.read_text(encoding="utf-8").splitlines() if s.strip() and not s.startswith("#")]
    lines.append("# ---- 2026-10-07 r11 新增：名单行/人员表/括注/工作室/职务在前规则认出的人名 ----")
    lines += new_names
    (DST / "names_confirmed.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")

    # 第二遍：出 r11
    total, produced, renamed = 0, set(), []
    with (DST / "deid_changes.jsonl").open("w", encoding="utf-8") as log:
        for p in sources:
            text, crlf = texts[p]
            new_stem, name_changes = patch(p.stem, known, specs)
            new_text, changes = patch(text, known, specs)
            if new_text.count("\n") != text.count("\n"):
                raise SystemExit(f"行数变了，中止：{p.name} {text.count(chr(10))} -> {new_text.count(chr(10))}")
            out = DST / (new_stem + p.suffix)
            if out.name in produced:
                raise SystemExit(f"改名后重名，中止：{out.name}")
            produced.add(out.name)
            write(out, new_text, crlf)
            for c in name_changes + changes:
                log.write(json.dumps({"file": out.name, **c}, ensure_ascii=False) + "\n")
            total += len(name_changes) + len(changes)
            if new_stem != p.stem:
                renamed.append((p.name, out.name))
    for old, new in renamed:
        print(f"改名：{old} -> {new}")
    stale = sorted(f.name for f in DST.glob("*.md") if f.name not in produced)
    for name in stale:
        print(f"注意：{name} 不是本次产出（旧版本残留？），未删除，请人工处理")

    hard, cands, ex = deid_scan.scan(DST, d.load_names_file(DST / "names_confirmed.txt"))
    report = [f"== 硬泄露 {len(hard)} 处"] + [f"  [{h['type']}] {h['file'][:30]} | {h['hit']}" for h in hard]
    for kind, c in cands.items():
        report.append(f"== 候选·{kind} {len(c)} 个")
        for w, n in c.most_common():
            f, ctx = ex[(kind, w)]
            report.append(f"  {n:3d} {w} | {f[:20]} | {ctx.replace(chr(10), ' ')[:50]}")
    (DST / "scan_report.txt").write_text("\n".join(report) + "\n", encoding="utf-8")
    print(f"r11 写出 {len(produced)} 份，新增替换 {total} 处，名单新增人名 {len(new_names)} 个 -> {DST}")
    print(f"deid_scan：硬泄露 {len(hard)} 处（报告 {DST / 'scan_report.txt'}）")
    return 1 if hard else 0


if __name__ == "__main__":
    common.force_utf8_stdout()
    sys.exit(main())
