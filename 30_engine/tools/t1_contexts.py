"""T1 definition evidence (07章 §2.2, 11章 P2.5): pull corpus contexts for dictionary terms.

Purpose: before anyone (human or Claude) writes a T1 definition for a term, look at how the corpus
actually uses it. This tool only COLLECTS evidence; it never writes definitions or touches terms.jsonl.

Which terms (pick one):
  --missing        kind=术语 and t1_definition empty (the 291 corpus-derived terms of P2.5)
  --zero-freq      in_dict_before=true and corpus_freq==0 (legacy terms never seen in raw_materials)
  --term X [...]   explicit terms

Corpus (default): the r10 de-identified batch + 20_knowledge/corpus/ (.md/.txt files, plus the
"text" field of .jsonl chunk files). Files listed in 20_knowledge/corpus/不外流清单_密级标记.txt
are skipped. Snippets are passed through deidentify.deidentify() unless --no-mask, because
20_knowledge/corpus/ is NOT de-identified.

Per term: total hits, number of documents, and up to --per-term snippets (±--window chars),
at most one per document, preferring snippets with definitional cues (是指/指的是/即/包括/...).

Output: JSON lines to --out (or stdout), one object per term:
  {"term", "hits", "docs", "contexts": [{"src", "cue", "text"}]}

--apply DRAFTS.tsv [--notes NOTES.tsv]: write reviewed drafts back into terms.jsonl (P2.5, 2026-10-07).
  DRAFTS.tsv / NOTES.tsv are "term<TAB>text" lines. Only kind=术语 rows whose t1_definition is empty
  are touched; an existing definition is never changed. Filled rows get t1_status="draft" and
  t1_source; terms in NOTES get t1_note (definition stays empty, e.g. "语料不足：…").
  Every draft must pass validate_definition() or nothing is written.
Pure standard library; runs the same on Windows and Linux.

CLI examples:
  python 30_engine/tools/t1_contexts.py --missing --out <scratch>/t1_ctx.jsonl
  python 30_engine/tools/t1_contexts.py --term 精益管理 现代终端 --per-term 8
  python 30_engine/tools/t1_contexts.py --apply drafts.tsv --notes notes.tsv
"""

import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import common
import deidentify

DEFAULT_BATCH = "30_engine/batches/B-20261004-deid-个人历史交付物-r10"
DEFAULT_CORPUS = "20_knowledge/corpus"
BLOCKLIST = "20_knowledge/corpus/不外流清单_密级标记.txt"
FRONTMATTER_RE = re.compile(r"^---\s*\n.*?\n---\s*\n", re.DOTALL)
# Definitional cues right after the term: "X是指…" "X，即…" "X包括…"
CUE_RE = re.compile(r"^(?:\s*[”」]?\s*)(?:是指|指的是|是|即|就是|主要是|包括|主要包括|是以|是在|作为|，即|，是|（)")
TEXT_SUFFIXES = {".md", ".txt"}
DRAFT_STATUS = "draft"
DRAFT_SOURCE = "语料归纳（2026-10-07，未经人工审）"
DEF_MIN, DEF_MAX = 40, 120
# Digits are allowed only inside method/tool names (A3 报告、5S/6S/7S 现场管理), never as data
ALLOWED_DIGIT_TOKENS = re.compile(r"A3|[5-7]S")


def load_terms(terms_path: Path, mode: str, explicit=()):
    rows = [json.loads(line) for line in terms_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    if mode == "missing":
        return [r["term"] for r in rows if r.get("kind") == "术语" and not (r.get("t1_definition") or "").strip()]
    if mode == "zero-freq":
        return [r["term"] for r in rows if r.get("kind") == "术语" and r.get("in_dict_before")
                and not r.get("corpus_freq")]
    return list(explicit)


def load_blocklist(root: Path):
    path = root / BLOCKLIST
    if not path.exists():
        return set()
    names = set()
    for line in path.read_text(encoding="utf-8").splitlines():
        rel = line.split("\t")[0].strip()
        if rel:
            names.add(Path(rel).name)
    return names


def iter_documents(paths, blocked_names=frozenset()):
    """Yield (source_label, text). A .jsonl chunk file yields one document per line ("text" field)."""
    for base in paths:
        base = Path(base)
        files = [base] if base.is_file() else sorted(p for p in base.rglob("*") if p.is_file())
        for f in files:
            if f.name in blocked_names:
                continue
            suffix = f.suffix.lower()
            if suffix in TEXT_SUFFIXES:
                try:
                    text = f.read_text(encoding="utf-8")
                except (UnicodeDecodeError, OSError):
                    continue
                yield f.name, FRONTMATTER_RE.sub("", text, count=1)
            elif suffix == ".jsonl":
                with f.open(encoding="utf-8", errors="replace") as fh:
                    for line in fh:
                        try:
                            obj = json.loads(line)
                        except json.JSONDecodeError:
                            continue
                        text = obj.get("text") if isinstance(obj, dict) else None
                        if isinstance(text, str) and text:
                            label = obj.get("file_name") or obj.get("chunk_id") or f.name
                            yield f"{f.name}:{label}", text


def snippet(text: str, pos: int, term: str, window: int):
    start, end = max(0, pos - window), min(len(text), pos + len(term) + window)
    return re.sub(r"\s+", " ", text[start:end]).strip()


def has_cue(text: str, pos: int, term: str):
    return bool(CUE_RE.match(text[pos + len(term): pos + len(term) + 6]))


def collect(terms, documents, per_term=5, window=60):
    """One pass over the corpus. Returns {term: {"hits", "docs", "cands": [(cue, src, snippet)]}}.

    Keeps at most one candidate per document per term (the first cue hit, else the first hit),
    and at most 4*per_term candidates per term so memory stays flat on a 480 MB corpus.
    """
    stats = {t: {"hits": 0, "docs": 0, "cands": []} for t in terms}
    cap = max(per_term * 4, per_term)
    for src, text in documents:
        for term in terms:
            n = text.count(term)
            if not n:
                continue
            s = stats[term]
            s["hits"] += n
            s["docs"] += 1
            cands = s["cands"]
            if len(cands) >= cap and all(c[0] for c in cands):
                continue
            pos, chosen, cue = text.find(term), None, False
            while pos != -1:
                if has_cue(text, pos, term):
                    chosen, cue = pos, True
                    break
                if chosen is None:
                    chosen = pos
                pos = text.find(term, pos + 1)
            item = (cue, src, snippet(text, chosen, term, window))
            if len(cands) < cap:
                cands.append(item)
            elif cue:
                # replace the first non-cue candidate
                for i, c in enumerate(cands):
                    if not c[0]:
                        cands[i] = item
                        break
    return stats


def pick(cands, per_term):
    """Cue snippets first, then others; drop exact duplicate snippet texts."""
    seen, out = set(), []
    for cue, src, text in sorted(cands, key=lambda c: not c[0]):
        if text in seen:
            continue
        seen.add(text)
        out.append({"src": src, "cue": cue, "text": text})
        if len(out) >= per_term:
            break
    return out


def run(terms, corpus_paths, per_term=5, window=60, mask=True, blocked=frozenset()):
    stats = collect(terms, iter_documents(corpus_paths, blocked), per_term, window)
    rows = []
    for term in terms:
        s = stats[term]
        contexts = pick(s["cands"], per_term)
        if mask:
            for c in contexts:
                c["text"] = deidentify.deidentify(c["text"])[0]
                c["src"] = deidentify.deidentify(c["src"])[0]
        rows.append({"term": term, "hits": s["hits"], "docs": s["docs"], "contexts": contexts})
    return rows


def validate_definition(text: str):
    """Problems with one T1 draft (empty list = OK). 07章/CLAUDE.md §4: no data, no unit/person names."""
    problems = []
    if not DEF_MIN <= len(text) <= DEF_MAX:
        problems.append(f"长度 {len(text)} 不在 {DEF_MIN}—{DEF_MAX}")
    if '"' in text or "'" in text or "「" in text or "」" in text:
        problems.append("引号须用中文弯引号")
    if re.search(r"[0-9０-９]", ALLOWED_DIGIT_TOKENS.sub("", text)):
        problems.append("含数字（定义不得带数据）")
    masked, changes, _ = deidentify.deidentify(text)
    if changes:
        problems.append("含单位名/人名/地名或数据：" + "、".join(c["orig"] for c in changes))
    return problems


def read_tsv(path: Path):
    out = {}
    for n, line in enumerate(Path(path).read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        term, sep, text = line.partition("\t")
        if not sep or not text.strip():
            raise ValueError(f"{path}:{n} 不是“词<TAB>文本”格式")
        if term in out:
            raise ValueError(f"{path}:{n} 重复的词：{term}")
        out[term] = text.strip()
    return out


def apply_drafts(rows, drafts, notes=None, source=DRAFT_SOURCE):
    """Fill empty T1 definitions in-place. Returns (filled, noted, problems).

    problems non-empty means the caller must NOT write anything.
    """
    notes = notes or {}
    problems = []
    by_term = {r["term"]: r for r in rows if r.get("kind") == "术语"}
    for term in set(drafts) & set(notes):
        problems.append(f"{term}：同时出现在定义稿和备注里")
    for term, text in list(drafts.items()) + list(notes.items()):
        row = by_term.get(term)
        if row is None:
            problems.append(f"{term}：terms.jsonl 中没有这个 kind=术语 的词")
        elif (row.get("t1_definition") or "").strip():
            problems.append(f"{term}：已有定义，不得覆盖")
    for term, text in drafts.items():
        problems.extend(f"{term}：{p}" for p in validate_definition(text))
    if problems:
        return 0, 0, problems
    for term, text in drafts.items():
        row = by_term[term]
        row["t1_definition"] = text
        row["t1_status"] = DRAFT_STATUS
        row["t1_source"] = source
    for term, text in notes.items():
        by_term[term]["t1_note"] = text
    return len(drafts), len(notes), []


def main(argv=None):
    common.force_utf8_stdout()
    root = common.project_root()
    ap = argparse.ArgumentParser(description="Collect corpus contexts for T1 definitions (evidence only).")
    group = ap.add_mutually_exclusive_group(required=True)
    group.add_argument("--missing", action="store_true", help="kind=术语 with empty t1_definition")
    group.add_argument("--zero-freq", action="store_true", help="legacy terms with corpus_freq 0")
    group.add_argument("--term", nargs="+", help="explicit terms")
    group.add_argument("--apply", help="TSV of reviewed T1 drafts to write into terms.jsonl")
    ap.add_argument("--notes", help="with --apply: TSV of t1_note for terms left empty")
    ap.add_argument("--terms-file", default=str(root / "20_knowledge/terms/terms.jsonl"))
    ap.add_argument("--corpus", nargs="+", help="corpus dirs/files (default: r10 batch + 20_knowledge/corpus)")
    ap.add_argument("--per-term", type=int, default=5)
    ap.add_argument("--window", type=int, default=60)
    ap.add_argument("--no-mask", action="store_true", help="skip deidentify on snippets (local eyes only)")
    ap.add_argument("--out", help="output JSONL path (default stdout)")
    args = ap.parse_args(argv)

    if args.apply:
        terms_path = Path(args.terms_file)
        rows = [json.loads(line) for line in terms_path.read_text(encoding="utf-8").splitlines() if line.strip()]
        filled, noted, problems = apply_drafts(rows, read_tsv(Path(args.apply)),
                                               read_tsv(Path(args.notes)) if args.notes else {})
        if problems:
            print("未写入，问题如下：\n" + "\n".join(problems), file=sys.stderr)
            return 1
        terms_path.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows), encoding="utf-8")
        print(f"写入 {filled} 条定义草稿、{noted} 条备注 -> {terms_path}", file=sys.stderr)
        return 0

    mode = "missing" if args.missing else "zero-freq" if args.zero_freq else "explicit"
    terms = load_terms(Path(args.terms_file), mode, args.term or ())
    corpus = [Path(p) for p in args.corpus] if args.corpus else [root / DEFAULT_BATCH, root / DEFAULT_CORPUS]
    rows = run(terms, corpus, args.per_term, args.window, mask=not args.no_mask, blocked=load_blocklist(root))
    text = "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows)
    if args.out:
        Path(args.out).write_text(text, encoding="utf-8")
        print(f"{len(rows)} 个词，{sum(1 for r in rows if r['hits'])} 个在语料中出现 -> {args.out}", file=sys.stderr)
    else:
        sys.stdout.write(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
