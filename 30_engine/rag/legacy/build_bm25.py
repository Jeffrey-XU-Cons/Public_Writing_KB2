r"""
公文写作 KB · 本地多层级 RAG —— jieba-BM25 稀疏索引（hybrid 的字面命中路）

只给「靠字面命中」的三个 collection 建：pw_terms / pw_patterns / pw_golden
（禁用词、搭配、TP- 标题代码、数字口诀、跨类标签）。
分词语料 = 正文 + tags + category，让六大类的「跨类关联标签」也能被字面命中（两条路都命中）。

用法：
  & $py D:\projects\Public_Writing_KB\rag\build_bm25.py
产出：rag/index/bm25/<collection>.pkl  = {"bm25": BM25Okapi, "ids": [...]}
pw_query.py --hybrid（这三个 collection 默认自动开）即读它做 dense∪BM25 融合。
"""
import pickle

import jieba
from rank_bm25 import BM25Okapi

import _common as C

TARGETS = ["pw_terms", "pw_patterns", "pw_golden"]


def main():
    C.BM25_DIR.mkdir(parents=True, exist_ok=True)
    client = C.get_client()
    names = [c.name for c in client.list_collections()]
    for name in TARGETS:
        if name not in names:
            print(f"[SKIP] {name} 不存在（先跑 build_index.py）")
            continue
        coll = client.get_collection(name)
        got = coll.get(include=["documents", "metadatas"])
        ids, docs, metas = got["ids"], got["documents"], got["metadatas"]
        corpus = []
        for doc, m in zip(docs, metas):
            blob = " ".join([doc or "", m.get("tags", ""), m.get("category", ""), m.get("cat2", "")])
            corpus.append([t for t in jieba.lcut(blob) if t.strip()])
        bm25 = BM25Okapi(corpus)
        out = C.BM25_DIR / f"{name}.pkl"
        with open(out, "wb") as f:
            pickle.dump({"bm25": bm25, "ids": ids}, f)
        print(f"[OK] {name}: {len(ids)} 条 → {out}")


if __name__ == "__main__":
    main()
