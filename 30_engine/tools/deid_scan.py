"""De-identification residual scan: list leak CANDIDATES in a de-identified batch for human review.

Why (2026-09-30): r7 was marked “有效版”, yet a scan found 117 real names in member lists / personnel
tables and 30+ county-level places. deidentify.py is rule-based and the long tail (counties, landmarks,
OCR typos like 王林=玉林) cannot be enumerated up front. Every batch must be scanned and the candidates
reviewed by a human before anything leaves the machine; confirmed items go back into deidentify.py
(EXTRA_PLACES) or the batch's names file, then the batch is re-run.

Candidates, not verdicts: most hits are ordinary words. Review, don't auto-replace.

CLI: python deid_scan.py BATCH_DIR [--names NAMES.txt] [--json]
  --names  confirmed-names file: any of them still present in the batch is reported as a hard leak
           (person names, or typed entries “〔某企业〕Name”, see deidentify.load_names_file).
Exit code 1 if any hard leak (known name still present, or a province/city name left outside the
political-phrase exemptions, or anything the 2026-10-07 rules in deidentify.r11_rules would still
change: phone numbers, name-list rows, brand spec names, overflowed placeholders …); candidates alone
exit 0. Exit code 2 if BATCH_DIR does not exist or holds no .md files — an empty scan used to print
“硬泄露 0” and pass, which is how a typo in the path looked like a clean batch.
"""

import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import common
import deidentify as d

NAME = "[" + d.SURNAMES + "][一-龥]{1,2}"
CONTEXTS = {
    "名单": re.compile("(?:" + d.ROLE_WORDS + r")[：:]\s*((?:" + NAME + r"[、，,\s]*)+)"),
    "人员表": re.compile(r"(?<![一-龥])(" + NAME + r")\s*[|\s]\s*[男女](?:[\s|]|$)"),
    "裸名+动词": re.compile("(" + NAME + ")(?=强调|指出|要求|表示|介绍|说|同志)"),
}
PLACE_CAND = re.compile(r"([一-龥]{2})(市|县|新区|旗|自治州|州)(?![一-龥]?(?:场|民|级|域|委|政|直|长|区县))")
# 候选的首字若是虚词/量词/泛指，基本不是地名（“各县”“全州”“个县”）
FUNC_FIRST = set("的了在和与及等为将对向由到是有中上下以其这那此各全本该每个两三多几所超大小新老某")
EXEMPT = re.compile("(?:延安|遵义|南昌|井冈山|西柏坡)(?:精神|会议|起义|整风|时期|道路)|保定额")
META_FILES = re.compile("复核报告|试跑报告")  # 批次里的复核记录不是语料（r7 里就混进了带原始单位名的复核报告）


# r10 的误伤形态：“及时处置”→“及〔姓名〕处置”，“17项处于”→“17〔姓名〕处于”
MISFIRE_RE = re.compile(r"(?:及|\d)〔姓名〕处(?=[置理于罚])")


def scan(batch_dir, known_names=()):
    hard, cands = [], defaultdict(Counter)
    examples = {}
    terms = [n if isinstance(n, str) else n[0] for n in known_names]
    name_rx = [(n, re.compile(r"[ 　]*".join(map(re.escape, n)))) for n in terms]
    for f in sorted(Path(batch_dir).glob("*.md")):
        if META_FILES.search(f.name):
            hard.append({"type": "非语料文件", "file": f.name, "hit": "复核/试跑记录混在批次里，可能含原始名称"})
            continue
        text = f.read_text(encoding="utf-8")
        for n, rx in name_rx:
            if rx.search(text) or rx.search(f.stem):
                hard.append({"type": "已确认名单残留", "file": f.name, "hit": n})
        # 2026-10-07 规则（deidentify.r11_rules）在这份文件上还能改动的地方，都是漏网
        for where, src in (("文件名", f.stem), ("正文", text)):
            for c in d.r11_rules(src)[1]:
                hard.append({"type": f"{c['type']}（{where}）", "file": f.name, "hit": c["orig"][:30]})
        for m in MISFIRE_RE.finditer(text):
            hard.append({"type": "人名规则误伤", "file": f.name, "hit": text[max(0, m.start() - 6):m.end() + 4]})
        # 文件名与正文都查：r9 的生僻字人名同时出现在文件名里，旧版只扫正文
        for where, src in (("文件名", f.stem), ("正文", text)):
            for m in d.PUA_NAME_RE.finditer(src):
                hard.append({"type": f"生僻字人名残留（{where}）", "file": f.name,
                             "hit": src[max(0, m.start() - 8):m.end() + 8]})
        plain = EXEMPT.sub("", text)
        for m in re.finditer("|".join(d.PLACES), plain):
            hard.append({"type": "省市名残留", "file": f.name, "hit": plain[max(0, m.start() - 8):m.end() + 8]})
        for m in d.DOCNO_ABBR_RE.finditer(text):
            hard.append({"type": "省份简称残留", "file": f.name, "hit": text[max(0, m.start() - 8):m.end() + 8]})
        # 字间加空格躲过扫描的地名（PDF 封面“雄 安 烟 草”）：去空格后再查一遍
        for m in d.SPACED_RUN_RE.finditer(plain):
            joined = re.sub(r"[ 　]+", "", m.group(0))
            if d.SPACED_HIT_RE.search(joined) or d.DOCNO_ABBR_RE.search(joined):
                hard.append({"type": "空格拆字地名残留", "file": f.name, "hit": joined[:30]})
        for kind, rx in CONTEXTS.items():
            for m in rx.finditer(text):
                for n in re.findall(NAME, m.group(1)):
                    if n not in d.NAME_FP and n not in d.PUBLIC_FIGURES:
                        cands[kind][n] += 1
                        examples.setdefault((kind, n), (f.name, text[max(0, m.start() - 10):m.end() + 10]))
        for m in PLACE_CAND.finditer(text):
            stem = m.group(1)
            if stem[0] in FUNC_FIRST or stem in d.CITIES:
                continue
            w = stem + m.group(2)
            cands["州县市候选"][w] += 1
            examples.setdefault(("州县市候选", w), (f.name, text[max(0, m.start() - 10):m.end() + 10]))
        for m in d.ABBR_DIRECTION_RE.finditer(text):
            cands["省简称方位"][m.group(0)] += 1
            examples.setdefault(("省简称方位", m.group(0)), (f.name, text[max(0, m.start() - 10):m.end() + 10]))
    return hard, cands, examples


def main(argv):
    as_json = "--json" in argv
    argv = [a for a in argv if a != "--json"]
    names = []
    if "--names" in argv:
        i = argv.index("--names")
        names = d.load_names_file(argv[i + 1])
        del argv[i:i + 2]
    batch = Path(argv[0]) if argv else None
    if batch is None or not batch.is_dir() or not any(batch.glob("*.md")):
        print(f"错误：批次目录不存在或没有 .md 文件：{batch}", file=sys.stderr)
        return 2
    hard, cands, ex = scan(batch, names)
    if as_json:
        print(json.dumps({"hard": hard, "candidates": {k: dict(v) for k, v in cands.items()}},
                         ensure_ascii=False, indent=1))
    else:
        print(f"== 硬泄露 {len(hard)} 处")
        for h in hard:
            print(f"  [{h['type']}] {h['file'][:30]} | {h['hit']}")
        for kind, c in cands.items():
            print(f"== 候选·{kind} {len(c)} 个（人工筛：确认的进 deidentify.EXTRA_PLACES 或批次姓名名单，重跑）")
            for w, n in c.most_common():
                f, ctx = ex[(kind, w)]
                print(f"  {n:3d} {w} | {f[:20]} | {ctx.replace(chr(10), ' ')[:50]}")
    return 1 if hard else 0


if __name__ == "__main__":
    common.force_utf8_stdout()
    sys.exit(main(sys.argv[1:]))
