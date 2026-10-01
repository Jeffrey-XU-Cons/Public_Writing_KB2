"""Locate article boundaries in the 技巧汇编 files (no heading structure).

Reads the screening list (20_knowledge/corpus/legacy/技巧汇编_筛选结果.txt),
finds each title as a standalone line in the body (after the table of contents),
and writes a locator table: volume / no / status / title / line range / Chinese chars.

Pure standard library; runs on both machines:
    python3 30_engine/tools/source_locate.py [--out 路径.tsv]
"""
import argparse
import re
from difflib import SequenceMatcher
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC_DIR = ROOT / "10_source/raw_materials/15.公文写作技巧汇编（305篇145万字）"
SCREEN = ROOT / "20_knowledge/corpus/legacy/技巧汇编_筛选结果.txt"

VOLUME_FILES = {
    "汇编一": "公文写作技巧汇编一（65篇31万字）.md",
    "汇编二": "公文写作技巧汇编二（14篇6万字）.md",
    "汇编三": "公文写作技巧汇编三（101篇33万字）.md",
    "汇编四": "公文写作技巧汇编（四）（50篇39万字）.md",
    "汇编五": "公文写作技巧汇编（五）（75篇36万字）.md",
}

CN_CHAR = re.compile(r"[一-鿿]")
NOT_WORD = re.compile(r"[^一-鿿A-Za-z0-9]")
SCREEN_LINE = re.compile(r"^(✅|❓|❌)\s*(汇编[一二三四五])-(\d+)\.\s*(.+)$")


def normalize(text):
    return NOT_WORD.sub("", text)


def read_screening():
    articles = []
    for line in SCREEN.read_text(encoding="utf-8").splitlines():
        match = SCREEN_LINE.match(line.strip())
        if match:
            status, volume, number, title = match.groups()
            articles.append({"volume": volume, "no": number, "status": status, "title": title.strip()})
    return articles


def toc_end_line(lines):
    """Body starts after the last TOC line (TOC lines end with a page number)."""
    last_toc = 0
    for index, line in enumerate(lines[:600]):
        if re.search(r"(…|\.{3}|\t)\s*\d+\s*$", line):
            last_toc = index
    return last_toc + 1


def title_keys(title):
    """Normalized match keys; series titles like 'X·第二章：Y' appear in the body as '第二章：Y'."""
    keys = [normalize(title)]
    if "·" in title:
        keys.append(normalize(title.split("·", 1)[1]))
    return keys


def line_matches(line_key, key):
    if line_key == key:
        return True
    probe = key[:10]
    if len(probe) >= 6 and line_key.startswith(probe):
        return True
    if len(line_key) >= 6 and key.startswith(line_key):
        return True
    # wording drift between TOC and body, e.g. 公务活动中的席位安排 / 公务活动中席位安排
    return len(key) >= 6 and SequenceMatcher(None, line_key, key).ratio() >= 0.85


def find_title(lines, title, start):
    """First standalone line at/after `start` whose normalized text matches the title."""
    keys = title_keys(title)
    for index in range(start, len(lines)):
        line_key = normalize(lines[index])
        if not line_key:
            continue
        for key in keys:
            if len(line_key) <= len(key) + 20 and line_matches(line_key, key):
                return index
    return None


def locate_volume(volume, articles):
    lines = (SRC_DIR / VOLUME_FILES[volume]).read_text(encoding="utf-8").splitlines()
    cursor = toc_end_line(lines)
    for article in articles:
        hit = find_title(lines, article["title"], cursor)
        article["start"] = hit
        if hit is not None:
            cursor = hit + 1
    found = [a for a in articles if a["start"] is not None]
    for current, following in zip(found, found[1:] + [None]):
        end = following["start"] if following else len(lines)
        current["end"] = end  # exclusive, 0-based
        current["chars"] = len(CN_CHAR.findall("\n".join(lines[current["start"]:end])))
    return articles


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default=str(ROOT / "10_source/manifest/技巧汇编_篇目定位.tsv"))
    args = parser.parse_args()

    articles = read_screening()
    for volume in VOLUME_FILES:
        locate_volume(volume, [a for a in articles if a["volume"] == volume])

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    rows = ["volume\tno\tstatus\ttitle\tfile\tline_start\tline_end\tcn_chars"]
    missing = 0
    for a in articles:
        if a["start"] is None:
            missing += 1
            rows.append(f"{a['volume']}\t{a['no']}\t{a['status']}\t{a['title']}\t{VOLUME_FILES[a['volume']]}\t\t\t")
        else:
            # 1-based inclusive line numbers for humans
            rows.append(f"{a['volume']}\t{a['no']}\t{a['status']}\t{a['title']}\t{VOLUME_FILES[a['volume']]}\t{a['start'] + 1}\t{a['end']}\t{a['chars']}")
    out_path.write_text("\n".join(rows) + "\n", encoding="utf-8")
    print(f"articles={len(articles)} located={len(articles) - missing} missing={missing} -> {out_path}")


if __name__ == "__main__":
    main()
