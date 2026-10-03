"""QA 库向量近重复判重（P5 SOP 第⑥步后半）。只读，不写任何 jsonl。

对 20_knowledge/qa/c*.jsonl 全部 active 记录的 answer 编码，两两算余弦相似度，输出：
  ① 相似度 > 阈值（默认 0.92）的所有对；② 相似度最高的 N 对（默认 20，无论是否过线）；
  ③ --pairs 指定对的分数。
阈值可按全库分布定：--percentile 99 取所有对相似度的第 99 百分位为线，列出不低于该线的对
（Jeffrey 2026-10-02 定：本库分数挤在 0.43–0.86，固定 0.92 永远不触发）。
--out 把过线对写成逐对人工判定清单（Markdown），供 Jeffrey 填合并/保留/废弃。
嵌入模型复用 Kb-RAG 建索引用的同一个（kb_index.load_model，注册表登记的 bge-m3），
不另装依赖、不另选模型，所以必须用 Kb-RAG 规定的解释器（见 Kb-RAG CLAUDE.md“运行环境”，下记 $KPY）跑：
  $KPY 30_engine/tools/kb_dedup_vec.py \
      [--kbrag D:/projects/Kb-RAG] [--threshold 0.92 | --percentile 99] [--top 20]
      [--pairs A,B C,D ...] [--json] [--out 清单.md]
Kb-RAG 目录默认取 --kbrag，其次环境变量 KBRAG_DIR，再次本项目的同级目录 Kb-RAG。
（不用 KBRAG_ROOT：那个变量在本项目里指公文库根目录。）
"""

import argparse
import json
import math
import os
import sys
from pathlib import Path

from common import force_utf8_stdout, qa_dir

DEFAULT_THRESHOLD = 0.92
DEFAULT_TOP = 20


def load_records(directory=None):
    """读全部 active 记录，按 id 排序。"""
    directory = Path(directory) if directory else qa_dir()
    records = []
    for path in sorted(directory.glob("c*.jsonl")):
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            rec = json.loads(line)
            if rec.get("status", "active") == "active":
                records.append(rec)
    return sorted(records, key=lambda r: r["id"])


def first_question(rec):
    return rec["question"].split(" / ")[0].strip()


def cosine(a, b):
    dot = sum(x * y for x, y in zip(a, b))
    norm = math.sqrt(sum(x * x for x in a)) * math.sqrt(sum(y * y for y in b))
    return dot / norm if norm else 0.0


def all_pairs(ids, vectors):
    """返回 [(id_a, id_b, score)]，按分数降序。"""
    pairs = []
    for i in range(len(ids)):
        for j in range(i + 1, len(ids)):
            pairs.append((ids[i], ids[j], cosine(vectors[i], vectors[j])))
    pairs.sort(key=lambda p: p[2], reverse=True)
    return pairs


def pair_scores(wanted, ids, vectors):
    """wanted: [(id_a, id_b)]。库里没有的 id 分数记 None。"""
    index = {qid: n for n, qid in enumerate(ids)}
    out = []
    for a, b in wanted:
        if a in index and b in index:
            out.append((a, b, cosine(vectors[index[a]], vectors[index[b]])))
        else:
            out.append((a, b, None))
    return out


def percentile_value(scores, pct):
    """最近秩法：取升序排列后第 ceil(pct% × n) 个值。scores 不需预先排序。"""
    ordered = sorted(scores)
    if not ordered:
        return 0.0
    rank = max(1, math.ceil(pct / 100 * len(ordered)))
    return ordered[min(rank, len(ordered)) - 1]


def analyze(records, encode, threshold=DEFAULT_THRESHOLD, top=DEFAULT_TOP, wanted=(),
            percentile=None):
    """encode: list[str] -> list[list[float]]。测试可注入假编码器。
    给了 percentile 时，阈值改为全部对相似度的该百分位，过线判据为“不低于”阈值。"""
    ids = [r["id"] for r in records]
    vectors = [list(map(float, v)) for v in encode([r["answer"] for r in records])]
    ranked = all_pairs(ids, vectors)
    questions = {r["id"]: first_question(r) for r in records}
    scores = [p[2] for p in ranked]

    if percentile is not None:
        threshold = percentile_value(scores, percentile)
        over = [p for p in ranked if p[2] >= threshold]
    else:
        over = [p for p in ranked if p[2] > threshold]

    def row(a, b, s):
        return {"a": a, "b": b, "score": None if s is None else round(s, 4),
                "q_a": questions.get(a, "（库中无此 id）"), "q_b": questions.get(b, "（库中无此 id）")}

    return {
        "records": len(records),
        "pair_count": len(ranked),
        "percentile": percentile,
        "threshold": round(threshold, 4),
        "distribution": {name: round(percentile_value(scores, pct), 4) if scores else None
                         for name, pct in (("median", 50), ("p90", 90), ("p99", 99), ("max", 100))},
        "over_threshold": [row(*p) for p in over],
        "top": [row(*p) for p in ranked[:top]],
        "pairs": [row(*p) for p in pair_scores(list(wanted), ids, vectors)],
    }


def kbrag_dir(arg):
    if arg:
        return Path(arg)
    if os.environ.get("KBRAG_DIR"):
        return Path(os.environ["KBRAG_DIR"])
    return Path(__file__).resolve().parents[3] / "Kb-RAG"


def model_encoder(kbrag):
    """加载 Kb-RAG 建索引用的同一个嵌入模型，返回 encode 函数。"""
    sys.path.insert(0, str(kbrag / "tools"))
    import kb_index  # noqa: E402  Kb-RAG 的模块
    import kb_registry  # noqa: E402

    model, cfg, _device = kb_index.load_model(kb_registry.load_registry())
    batch = cfg.get("batch_size", 16) or 16

    def encode(texts):
        return model.encode(texts, batch_size=batch, normalize_embeddings=True,
                            show_progress_bar=False, convert_to_numpy=True).tolist()

    return encode


def parse_pairs(items):
    pairs = []
    for item in items or []:
        a, _, b = item.partition(",")
        if not a or not b:
            raise SystemExit(f"--pairs 格式应为 ID1,ID2：{item}")
        pairs.append((a.strip(), b.strip()))
    return pairs


def batch_of(rec):
    return rec.get("batch_id", "")


def checklist_markdown(result, records, model_note=""):
    """把过线对写成逐对人工判定清单。判定列留空，由 Jeffrey 填。"""
    by_id = {r["id"]: r for r in records}
    dist = result["distribution"]
    rule = (f"第 {result['percentile']} 百分位（{result['threshold']:.4f}），列出不低于该线的对"
            if result["percentile"] is not None else f"固定阈值 > {result['threshold']}")
    lines = [
        "# QA 库向量判重 · 逐对判定清单",
        "",
        f"- 记录：active {result['records']} 条，两两 {result['pair_count']} 对；只对 answer 编码{model_note}",
        f"- 分布：中位数 {dist['median']}、P90 {dist['p90']}、P99 {dist['p99']}、最高 {dist['max']}",
        f"- 过线规则：{rule}；共 **{len(result['over_threshold'])} 对**",
        "- 判定填：合并（写明保留哪条）／保留（内容不同，写一句区别）／废弃（写明废哪条）。"
        "本清单只供判定，工具不改任何条目",
        "",
        "| # | 分数 | A | A 小类 | A 首个问法 | B | B 小类 | B 首个问法 | 同小类 | 批次 | 判定 | 理由 |",
        "|---|---|---|---|---|---|---|---|---|---|---|---|",
    ]
    for n, r in enumerate(result["over_threshold"], 1):
        ra, rb = by_id.get(r["a"], {}), by_id.get(r["b"], {})
        l2a, l2b = ra.get("category_l2", ""), rb.get("category_l2", "")
        same = "是" if l2a and l2a == l2b else ""
        batches = batch_of(ra) if batch_of(ra) == batch_of(rb) else f"{batch_of(ra)}／{batch_of(rb)}"
        cells = [str(n), f"{r['score']:.4f}", r["a"], l2a, r["q_a"], r["b"], l2b, r["q_b"],
                 same, batches, "", ""]
        lines.append("| " + " | ".join(c.replace("|", "｜") for c in cells) + " |")
    return "\n".join(lines) + "\n"


def print_report(result):
    def show(title, rows):
        print(f"\n## {title}（{len(rows)} 对）")
        for r in rows:
            score = "无此 id" if r["score"] is None else f"{r['score']:.4f}"
            print(f"{score}  {r['a']} × {r['b']}\n        {r['q_a']}\n        {r['q_b']}")

    dist = result["distribution"]
    print(f"active 记录 {result['records']} 条，{result['pair_count']} 对；"
          f"中位数 {dist['median']} P90 {dist['p90']} P99 {dist['p99']} 最高 {dist['max']}")
    print(f"阈值 {result['threshold']}" + (f"（第 {result['percentile']} 百分位）"
                                          if result["percentile"] is not None else ""))
    show(f"相似度过线（{result['threshold']}）", result["over_threshold"])
    show("相似度最高", result["top"])
    if result["pairs"]:
        show("指定对", result["pairs"])


def main(argv=None):
    force_utf8_stdout()
    ap = argparse.ArgumentParser(description="QA 库向量近重复判重（只读）")
    ap.add_argument("--kbrag", help="Kb-RAG 目录")
    gate = ap.add_mutually_exclusive_group()
    gate.add_argument("--threshold", type=float, default=DEFAULT_THRESHOLD)
    gate.add_argument("--percentile", type=float, help="按全库分布取阈值，如 99")
    ap.add_argument("--top", type=int, default=DEFAULT_TOP)
    ap.add_argument("--pairs", nargs="*", help="指定对，形如 QA-C6-00018,QA-C6-00014")
    ap.add_argument("--json", action="store_true", help="以 JSON 输出")
    ap.add_argument("--out", help="把过线对写成逐对判定清单（Markdown）")
    args = ap.parse_args(argv)

    records = load_records()
    result = analyze(records, model_encoder(kbrag_dir(args.kbrag)),
                     args.threshold, args.top, parse_pairs(args.pairs), args.percentile)
    if args.out:
        Path(args.out).write_text(
            checklist_markdown(result, records, "，模型同 Kb-RAG 建索引（bge-m3）"), encoding="utf-8")
        print(f"清单已写入 {args.out}", file=sys.stderr)
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print_report(result)
    return 0


if __name__ == "__main__":
    sys.exit(main())
