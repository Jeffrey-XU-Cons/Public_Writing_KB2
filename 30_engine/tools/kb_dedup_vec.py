"""QA 库向量近重复判重（P5 SOP 第⑥步后半）。只读，不写任何 jsonl。

对 20_knowledge/qa/c*.jsonl 全部 active 记录的 answer 编码，两两算余弦相似度，输出：
  ① 相似度 > 阈值（默认 0.92）的所有对；② 相似度最高的 N 对（默认 20，无论是否过线）；
  ③ --pairs 指定对的分数。
嵌入模型复用 Kb-RAG 建索引用的同一个（kb_index.load_model，注册表登记的 bge-m3），
不另装依赖、不另选模型，所以必须用 Kb-RAG 的 venv 解释器跑：
  D:/projects/tobacco_kb/.venv-cuda/Scripts/python.exe 30_engine/tools/kb_dedup_vec.py \
      [--kbrag D:/projects/Kb-RAG] [--threshold 0.92] [--top 20] [--pairs A,B C,D ...] [--json]
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


def analyze(records, encode, threshold=DEFAULT_THRESHOLD, top=DEFAULT_TOP, wanted=()):
    """encode: list[str] -> list[list[float]]。测试可注入假编码器。"""
    ids = [r["id"] for r in records]
    vectors = [list(map(float, v)) for v in encode([r["answer"] for r in records])]
    ranked = all_pairs(ids, vectors)
    questions = {r["id"]: first_question(r) for r in records}

    def row(a, b, s):
        return {"a": a, "b": b, "score": None if s is None else round(s, 4),
                "q_a": questions.get(a, "（库中无此 id）"), "q_b": questions.get(b, "（库中无此 id）")}

    return {
        "records": len(records),
        "threshold": threshold,
        "over_threshold": [row(*p) for p in ranked if p[2] > threshold],
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


def print_report(result):
    def show(title, rows):
        print(f"\n## {title}（{len(rows)} 对）")
        for r in rows:
            score = "无此 id" if r["score"] is None else f"{r['score']:.4f}"
            print(f"{score}  {r['a']} × {r['b']}\n        {r['q_a']}\n        {r['q_b']}")

    print(f"active 记录 {result['records']} 条，阈值 {result['threshold']}")
    show(f"相似度 > {result['threshold']}", result["over_threshold"])
    show("相似度最高", result["top"])
    if result["pairs"]:
        show("指定对", result["pairs"])


def main(argv=None):
    force_utf8_stdout()
    ap = argparse.ArgumentParser(description="QA 库向量近重复判重（只读）")
    ap.add_argument("--kbrag", help="Kb-RAG 目录")
    ap.add_argument("--threshold", type=float, default=DEFAULT_THRESHOLD)
    ap.add_argument("--top", type=int, default=DEFAULT_TOP)
    ap.add_argument("--pairs", nargs="*", help="指定对，形如 QA-C6-00018,QA-C6-00014")
    ap.add_argument("--json", action="store_true", help="以 JSON 输出")
    args = ap.parse_args(argv)

    records = load_records()
    result = analyze(records, model_encoder(kbrag_dir(args.kbrag)),
                     args.threshold, args.top, parse_pairs(args.pairs))
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print_report(result)
    return 0


if __name__ == "__main__":
    sys.exit(main())
