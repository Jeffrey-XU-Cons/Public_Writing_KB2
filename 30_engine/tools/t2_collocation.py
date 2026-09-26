"""T2 collocation layer (07章 §2.2-2.3, 11章 P2.4): corpus co-occurrence stats for dictionary terms.

For each term: which content words most often come right before (前接) and right after (后接).
Offline batch only — jieba is used here, not in any retrieval path (Kb-RAG's no-jieba ADR is about
query-time dependencies).

Corpus: 10_source/raw_materials minus the prompt-template library, minus empty shells and
duplicate copies listed by corpus_scan.py.
Safety: collocates are statistics, but a collocate could still be a place/unit/person name; those are
filtered (deidentify place/unit rules + jieba POS nr/ns/nt). 典型搭配 is assembled from the top
collocates, NOT a raw corpus sentence — a raw sentence would bypass the de-identification gate.

CLI: python t2_collocation.py [OUT_JSONL]
"""

import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

import jieba
import jieba.posseg as pseg
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
import common
import deidentify

jieba.setLogLevel(60)

FRONTMATTER_RE = re.compile(r"^---\s*\n.*?\n---\s*\n", re.DOTALL)
HAN_RE = re.compile(r"^[一-鿿]+$")
# 找邻词时跳过的虚词（不跨标点）
SKIP = set("的 地 得 了 着 过 和 与 及 等 并 也 都 是 在 对 为 将 把 以 从 向 于 其 之 而 且 又 还 就 要 被".split())
TOP_N, MIN_COUNT = 5, 3


def load_terms(root: Path, with_candidates=False):
    terms = {}
    for f in sorted((root / "20_knowledge/terms/legacy/tobacco_terms").glob("*.yaml")):
        data = yaml.safe_load(f.read_text(encoding="utf-8"))
        for v in data.values():
            if not isinstance(v, list):
                continue
            for x in v:
                if isinstance(x, dict) and x.get("term") and x["term"] not in terms:
                    terms[x["term"]] = {"source_id": x.get("id"), "definition": x.get("definition", ""),
                                        "domain": x.get("domain") or x.get("category"), "source_file": f.name,
                                        "in_dict_before": True}
    accepted = root / "20_knowledge/terms/candidates_accepted.jsonl"
    if with_candidates and accepted.exists():
        for line in accepted.read_text(encoding="utf-8").splitlines():
            c = json.loads(line)
            if c["term"] not in terms:
                # T1 定义留空：定义要人或 LLM 写，不能从语料里编（CLAUDE.md §4.1）
                terms[c["term"]] = {"source_id": None, "definition": "", "domain": None,
                                    "source_file": accepted.name, "in_dict_before": False}
    return terms


def official_rule_rows(root: Path, start: int):
    """07章 §2.5：官方词表解构的禁用词/搭配错误/套话并入 terms.jsonl，kind 区分。"""
    src = root / "20_knowledge/terms/official_terms_解构.jsonl"
    if not src.exists():
        return []
    kind_of = {"禁用词": "禁用词", "搭配": "搭配错误", "套话": "套话"}
    key_of = {"禁用词": "banned", "搭配": "wrong", "套话": "original"}
    rows = []
    for n, line in enumerate(src.read_text(encoding="utf-8").splitlines(), start):
        r = json.loads(line)
        rows.append({"id": f"T-{n:05d}", "kind": kind_of[r["category"]], "term": r[key_of[r["category"]]],
                     "rule": {k: v for k, v in r.items() if k not in ("id", "category")},
                     "source_id": r["id"], "source_file": src.name, "status": "active"})
    return rows


def corpus_files(root: Path):
    raw = root / "10_source/raw_materials"
    skip = set()
    scan = root / "20_knowledge/corpus/清理清单_空壳与重复.json"
    if scan.exists():
        d = json.loads(scan.read_text(encoding="utf-8"))
        skip |= {x["file"] for x in d["empty_shells"]} | {x["duplicate_of_keep"] for x in d["duplicates"]}
    return [p for p in sorted(raw.rglob("*.md"))
            if "AI写材料提示词模板库" not in str(p) and str(p.relative_to(raw)) not in skip]


def neighbor(tokens, i, step):
    j = i + step
    while 0 <= j < len(tokens):
        t = tokens[j].strip()
        if not t:
            j += step
            continue
        if not HAN_RE.match(t):
            return None  # 标点/数字 = 边界，不跨过去
        if t in SKIP:
            j += step
            continue
        return t
    return None


def collect(texts, termset):
    """freq / before / after 是出现次数；返回的 df 是 (term, 方向, 邻词) 出现在多少份不同文件里。"""
    freq, before, after = Counter(), defaultdict(Counter), defaultdict(Counter)
    df = Counter()
    for text in texts:
        tokens = jieba.lcut(text, HMM=False)
        seen = set()
        for i, tok in enumerate(tokens):
            if tok in termset:
                freq[tok] += 1
                b, a = neighbor(tokens, i, -1), neighbor(tokens, i, +1)
                if b and len(b) >= 2:
                    before[tok][b] += 1
                    seen.add((tok, "前", b))
                if a and len(a) >= 2:
                    after[tok][a] += 1
                    seen.add((tok, "后", a))
        df.update(seen)
    return freq, before, after, df


# 首跑抽查的噪音：介词、轻动词、泛指代词、泛化机构名，对"该搭什么词"没有信息量
LIGHT = {"进行", "提供", "关于", "根据", "通过", "相关", "方面", "其他", "不同", "各个", "有关",
         "以及", "包括", "公司", "有限公司", "有限责任", "企业", "单位", "部门", "我们", "开展了", "实现了"}
# jieba 对孤立词的词性不可靠（"深化"标成缩略语 j、"全面""规范"标成 n），不能做白名单。
# 只做反向过滤：剔除明确的虚词类 + 数量短语，实词误标也不会被误杀。
DROP_POS = ("m", "q", "p", "r", "c", "u", "f")
QUANT_RE = re.compile(r"^[一二三四五六七八九十两几多各每数诸][个家项条类种级批次位名台辆大]?$|^[一二三四五六七八九十两几多各每数诸]{1,2}[个家项条类种级批次位名台辆]$")


def _junk(word):
    if QUANT_RE.match(word):
        return True
    return any(x.flag.startswith(DROP_POS) for x in pseg.lcut(word))


def is_sensitive(word, known_names=()):
    if word in known_names or deidentify.UNIT_RE.search(word) or deidentify.PLACE_RE.search(word):
        return True
    return any(flag in ("nr", "ns", "nt") for _, flag in pseg.lcut(word))


# 通用搭配应跨文件出现；只在少数几份里扎堆的邻词多半是具体单位/地名（首跑抽查：
# 某表外地级市+物流中心，地名表和 jieba 地名标注都没拦住）
MIN_DOCS = 5


def top(counter, known_names, df=None, key=None):
    keep = []
    for w, c in counter.most_common(50):
        if c < MIN_COUNT or w in LIGHT or _junk(w) or is_sensitive(w, known_names):
            continue
        if df is not None and df[key + (w,)] < MIN_DOCS:
            continue
        keep.append(w)
    return keep[:TOP_N]


def build(root: Path, known_names=()):
    terms = load_terms(root, with_candidates=True)
    splittable = {t for t in terms if HAN_RE.match(t)}  # 含"、"等标点的长提法 jieba 切不成一个词
    for t in splittable:
        jieba.add_word(t, freq=10 ** 6)
    texts = [FRONTMATTER_RE.sub("", p.read_text(encoding="utf-8"), count=1) for p in corpus_files(root)]
    freq, before, after, df = collect(texts, splittable)
    rows = []
    for n, (term, meta) in enumerate(terms.items(), 1):
        if term in splittable:
            f = freq[term]
            pre = top(before[term], known_names, df, (term, "前"))
            post = top(after[term], known_names, df, (term, "后"))
            t2 = {"前接": pre, "后接": post, "语料频次": f,
                  "典型搭配": (pre[0] if pre else "") + term + (post[0] if post else "") if (pre or post) else ""}
        else:
            f = sum(t.count(term) for t in texts)
            t2 = {"前接": [], "后接": [], "语料频次": f, "典型搭配": "", "note": "含标点的整句提法，按原文计频，不做邻词统计"}
        rows.append({"id": f"T-{n:05d}", "kind": "术语", "term": term, "t1_definition": meta["definition"],
                     "t2_collocation": t2, "t3_register": {}, "t4_contrast": [],
                     "domain": meta["domain"], "corpus_freq": f, "in_dict_before": meta["in_dict_before"],
                     "source_id": meta["source_id"], "source_file": meta["source_file"], "status": "active"})
    rows += official_rule_rows(root, len(rows) + 1)
    return rows, len(texts)


def main(argv):
    root = common.project_root()
    out = Path(argv[0]) if argv else root / "20_knowledge/terms/terms.jsonl"
    rows, n_docs = build(root)
    out.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows), encoding="utf-8")
    terms = [r for r in rows if r["kind"] == "术语"]
    old = [r for r in terms if r["in_dict_before"]]
    hit = sum(1 for r in terms if r["corpus_freq"] > 0)
    with_t2 = sum(1 for r in terms if r["t2_collocation"]["前接"] or r["t2_collocation"]["后接"])
    print(f"语料 {n_docs} 份；术语 {len(terms)} 条（原有 {len(old)} + 新增 {len(terms) - len(old)}），"
          f"语料中出现 {hit} 条（{hit / len(terms):.0%}），有搭配 {with_t2} 条；"
          f"另并入官方规则 {len(rows) - len(terms)} 条 -> {out}")
    return 0


if __name__ == "__main__":
    common.force_utf8_stdout()
    sys.exit(main(sys.argv[1:]))
