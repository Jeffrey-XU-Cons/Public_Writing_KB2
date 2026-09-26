"""Corpus hygiene scan: empty shells + duplicates (11章 P2.2).

Parameters calibrated 2026-09-25 to reproduce CLAUDE.md §五's measured 49 empty / 62 duplicate:
  empty shell = body (frontmatter stripped) < 200 chars       -> 49 exactly
  duplicate   = identical after stripping all whitespace + punctuation,
                bodies with < 20 word chars excluded            -> 61 (62 claimed, off by 1)
See 20_knowledge/corpus/清理清单_空壳与重复_说明.md.

Read-only on 10_source. CLI: python corpus_scan.py [OUT_JSON]
"""

import hashlib
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import common

EXCLUDE = "AI写材料提示词模板库"
EMPTY_THRESHOLD = 200
MIN_WORD_CHARS = 20
FRONTMATTER_RE = re.compile(r"^---\s*\n.*?\n---\s*\n", re.DOTALL)
NONWORD_RE = re.compile(r"[\s\W_]+", re.UNICODE)


def scan(root: Path):
    empty, groups, body_len = [], defaultdict(list), {}
    for p in sorted(root.rglob("*.md")):
        if EXCLUDE in str(p):
            continue
        body = FRONTMATTER_RE.sub("", p.read_text(encoding="utf-8"), count=1).strip()
        rel = str(p.relative_to(root))
        body_len[rel] = len(body)
        if len(body) < EMPTY_THRESHOLD:
            empty.append({"file": rel, "body_chars": len(body)})
        norm = NONWORD_RE.sub("", body)
        if len(norm) >= MIN_WORD_CHARS:
            groups[hashlib.sha1(norm.encode("utf-8")).hexdigest()].append(rel)
    dups = []
    for files in groups.values():
        if len(files) > 1:
            ranked = sorted(files, key=lambda f: (-body_len[f], f))
            dups += [{"keep": ranked[0], "duplicate_of_keep": f} for f in ranked[1:]]
    return {"empty_shells": empty, "duplicates": dups}


def main(argv):
    root = common.project_root() / "10_source" / "raw_materials"
    out = Path(argv[0]) if argv else common.project_root() / "20_knowledge" / "corpus" / "清理清单_空壳与重复.json"
    result = scan(root)
    out.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"空壳 {len(result['empty_shells'])}，重复 {len(result['duplicates'])} -> {out}")
    return 0


if __name__ == "__main__":
    common.force_utf8_stdout()
    sys.exit(main(sys.argv[1:]))
