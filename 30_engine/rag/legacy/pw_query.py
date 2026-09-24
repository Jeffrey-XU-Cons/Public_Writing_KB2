r"""
公文写作 KB · 本地多层级 RAG —— 查询 CLI（镜像 tobacco_kb/08_query.py）

用法（在 tobacco_kb venv 下）：
  $py = "D:\projects\tobacco_kb\.venv-cuda\Scripts\python.exe"
  & $py D:\projects\Public_Writing_KB\rag\pw_query.py "管理效能攻坚 成效" `
      --collection pw_paragraphs --layer 内容 --min-quality 8 --top 8 --rerank --show-text

多层级：--collection 选粒度库；--layer/--doc-type/--min-quality 落 metadata 过滤。
--hybrid：对 terms/patterns/golden 融合 jieba-BM25（需先跑 build_bm25.py；否则自动降级 dense）。
--out 写文件（skill 用）。
"""
import argparse
import pickle
from pathlib import Path

import _common as C

# --granularity → 默认 collection
GRAN_COLL = {
    "skeleton": "pw_templates", "document": "pw_articles", "paragraph": "pw_paragraphs",
    "sentence": "pw_golden", "title": "pw_patterns", "pattern": "pw_patterns", "term": "pw_terms",
}
HYBRID_DEFAULT = {"pw_terms", "pw_patterns", "pw_golden"}   # 这三个默认走字面融合


def build_where(args):
    conds = []
    if args.layer:
        conds.append({"layer": args.layer})
    if args.doc_type:
        conds.append({"doc_type": args.doc_type})
    if args.min_quality is not None:
        conds.append({"quality_score": {"$gte": float(args.min_quality)}})
    if args.cat1:
        conds.append({"cat1": args.cat1})
    if args.cat2:
        conds.append({"cat2": args.cat2})
    if not conds:
        return None
    return conds[0] if len(conds) == 1 else {"$and": conds}


def bm25_candidates(collection_name, query, pool):
    """读 build_bm25 产出的稀疏索引，返回候选 source_id 列表；无索引则空。"""
    pkl = C.BM25_DIR / f"{collection_name}.pkl"
    if not pkl.exists():
        return []
    import jieba
    with open(pkl, "rb") as f:
        obj = pickle.load(f)
    bm25, ids = obj["bm25"], obj["ids"]
    toks = [t for t in jieba.lcut(query) if t.strip()]
    if not toks:
        return []
    scores = bm25.get_scores(toks)
    order = sorted(range(len(ids)), key=lambda i: -scores[i])[:pool]
    return [ids[i] for i in order if scores[i] > 0]


def retrieve(collection, query, top=10, recall_pool=50, rerank=False, hybrid=False, where=None):
    """核心检索：dense(∪BM25) → 可选 rerank。返回 [(sid, doc, meta, cosine, final), ...]。
    可被 smoke_test / skill 驱动脚本 import 复用。"""
    model = C.get_model()
    q_emb = model.encode([C.QUERY_PREFIX + query], normalize_embeddings=True)[0]
    coll_name = collection.name
    use_hybrid = hybrid or coll_name in HYBRID_DEFAULT
    n_recall = recall_pool if (rerank or use_hybrid) else top

    res = collection.query(query_embeddings=[q_emb.tolist()], n_results=n_recall, where=where)
    cand = {i: (d, m, 1 - dist) for i, d, m, dist in
            zip(res["ids"][0], res["documents"][0], res["metadatas"][0], res["distances"][0])}

    if use_hybrid:
        extra = [s for s in bm25_candidates(coll_name, query, recall_pool) if s not in cand]
        if extra:
            got = collection.get(ids=extra, where=where, include=["documents", "metadatas"])
            for sid, d, m in zip(got["ids"], got["documents"], got["metadatas"]):
                cand[sid] = (d, m, 0.0)

    items = [(sid, d, m, cos) for sid, (d, m, cos) in cand.items()]
    if (rerank or use_hybrid) and items:
        scores = C.get_reranker().predict([(query, d) for _, d, _, _ in items],
                                           show_progress_bar=False, batch_size=32)
        order = sorted(range(len(items)), key=lambda i: -float(scores[i]))[:top]
        return [(items[i][0], items[i][1], items[i][2], items[i][3], float(scores[i])) for i in order]
    items = sorted(items, key=lambda x: -x[3])[:top]
    return [(s, d, m, c, c) for s, d, m, c in items]


def emit(lines, out):
    text = "\n".join(lines)
    if out:
        Path(out).parent.mkdir(parents=True, exist_ok=True)
        Path(out).write_text(text, encoding="utf-8")
        print(f"[OK] 写出 {out}（{len(lines)} 行）")
    else:
        print(text)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("query")
    ap.add_argument("--collection")
    ap.add_argument("--granularity", choices=list(GRAN_COLL))
    ap.add_argument("--layer", choices=["结构", "内容", "语言"])
    ap.add_argument("--cat1", help="六大类：文种规范/格式规范/结构与逻辑/语言与措辞/场景实战/思维与原则")
    ap.add_argument("--cat2", help="小类，如 禁忌错误/开头写法/惯用语")
    ap.add_argument("--doc-type", dest="doc_type")
    ap.add_argument("--min-quality", dest="min_quality", type=float)
    ap.add_argument("--top", type=int, default=10)
    ap.add_argument("--recall-pool", dest="recall_pool", type=int, default=50)
    ap.add_argument("--rerank", action="store_true")
    ap.add_argument("--hybrid", action="store_true", help="融合 jieba-BM25（字面命中）")
    ap.add_argument("--show-text", dest="show_text", action="store_true")
    ap.add_argument("--out")
    args = ap.parse_args()

    coll_name = args.collection or (GRAN_COLL.get(args.granularity) if args.granularity else None)
    if not coll_name:
        print("[ERROR] 需给 --collection 或 --granularity"); return

    client = C.get_client()
    names = [c.name for c in client.list_collections()]
    if coll_name not in names:
        print(f"[ERROR] collection '{coll_name}' 不存在（现有 {names}）。先跑 build_index.py。"); return
    collection = client.get_collection(coll_name)

    where = build_where(args)
    items = retrieve(collection, args.query, top=args.top, recall_pool=args.recall_pool,
                     rerank=args.rerank, hybrid=args.hybrid, where=where)

    lines = [f"[QUERY]「{args.query}」 collection={coll_name}" + (f" 过滤={where}" if where else ""),
             f"返回 {len(items)} 条：", ""]
    for i, (sid, doc, meta, cos, final) in enumerate(items):
        lines.append(f"--- #{i+1}  score {final:.3f} | cosine {cos:.3f} ---")
        lines.append(f"[ID] {sid}  {meta.get('cat1','')}·{meta.get('cat2','')}"
                     f"  层:{meta.get('layer','')}  文种:{meta.get('doc_type','')}"
                     + (f"  质:{meta.get('quality_score','')}" if meta.get('quality_score') else "")
                     + (f"  标签:{meta.get('tags','')}" if meta.get('tags') else ""))
        src = meta.get("source_file", "")
        if src:
            lines.append(f"[来源] {src}" + (f" / {meta.get('section_path','')}" if meta.get("section_path") else ""))
        body = doc if args.show_text else (doc[:150] + ("..." if len(doc) > 150 else ""))
        lines.append(body)
        lines.append("")
    emit(lines, args.out)


if __name__ == "__main__":
    main()
