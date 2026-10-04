"""Build de-identified batch r10 from r9 by applying ONLY the rules added on 2026-10-04.

Why: while annotating speech exemplars (B-20261004-AR-01) the annotators found leaks in r9 —
a national-bureau deputy director's name written with a private-use-area glyph (body + file name),
a provincial governor's name, cigarette brands that identify the client (黄金叶 etc.), county/town
names, companies without a place prefix, a 中烟 name split by spaces/line breaks, and “确保定额”
mangled into “确〔丁地〕额”. deidentify.py now has rules for the general cases; re-running the whole
pipeline on r9 output would re-process numbers and placeholders, so this script applies just the
new rules to r9 text and writes r10 next to it. r9 is left untouched (deletion is Jeffrey's call).

Usage: python 30_engine/tools/migrations/20261004_deid_r9_to_r10.py
Then:  python 30_engine/tools/deid_scan.py <r10> --names <r10>/names_confirmed.txt   (hard leaks must be 0)
"""

import json
import re
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import common  # noqa: E402
import deidentify as d  # noqa: E402

BATCHES = common.project_root() / "30_engine" / "batches"
SRC = BATCHES / "B-20261003-deid-个人历史交付物-r9"
DST = BATCHES / "B-20261004-deid-个人历史交付物-r10"

NEW_PLACES_RE = re.compile("湘阴(?!县)|衡山|平坝|常张")  # 本批新增的县镇名（“湘阴县”r9 已处理）
# 只在 r9 出现一次的个别漏网，不值得做成通用规则
SPECIFIC = [
    (re.compile(r"确〔丁地〕额"), "确保定额", "误伤复原（保定额）"),
    (re.compile(r"谌贻琴"), "〔姓名〕", "人名(省领导)"),
    (re.compile(r"春节[\s　]*同[\s　]*志"), "〔姓名〕同志", "人名(名+同志，跨行)"),
    (re.compile(r"河[\s　]*南[\s　]*中[\s　]*烟"), "〔A中烟〕", "单位名(跨行拆字)"),  # 该文件已有的 1 处〔A中烟〕即同一单位
]


def patch(text):
    changes = []
    rules = [(d.PUA_NAME_RE, "〔姓名〕", "人名(生僻字)"), (d.EXTRA_UNIT_RE, "〔某企业〕", "企业名(无地名)"),
             (d.BANK_RE, "〔某银行〕", "银行名"), (d.BRAND_RE, "〔品牌〕", "品牌"), (d.BRAND_CTX_RE, "〔品牌〕", "品牌"),
             (NEW_PLACES_RE, "〔某地〕", "地名(县级/地标)")] + [(rx, new, tag) for rx, new, tag in SPECIFIC]
    for rx, new, tag in rules:
        for m in rx.finditer(text):
            changes.append({"type": tag, "orig": m.group(0), "new": new})
        text = rx.sub(new, text)
    return text, changes


def main():
    if DST.exists():
        print(f"{DST.name} 已存在，不覆盖")
        return 1
    DST.mkdir()
    for name in ("names_confirmed.txt",):
        shutil.copy2(SRC / name, DST / name)
    with (DST / "names_confirmed.txt").open("a", encoding="utf-8") as f:
        f.write("谌贻琴\n")
    total = 0
    with (DST / "deid_changes.jsonl").open("w", encoding="utf-8") as log:
        for p in sorted(SRC.glob("*.md")):
            new_stem, name_changes = patch(p.stem)
            new_text, changes = patch(p.read_text(encoding="utf-8"))
            (DST / (new_stem + p.suffix)).write_text(new_text, encoding="utf-8")
            for c in name_changes + changes:
                log.write(json.dumps({"file": new_stem + p.suffix, **c}, ensure_ascii=False) + "\n")
            total += len(name_changes) + len(changes)
            if new_stem != p.stem:
                print(f"改名：{p.name} -> {new_stem}{p.suffix}")
    print(f"r10 写出 {len(list(DST.glob('*.md')))} 份，新增替换 {total} 处 -> {DST}")
    return 0


if __name__ == "__main__":
    common.force_utf8_stdout()
    sys.exit(main())
