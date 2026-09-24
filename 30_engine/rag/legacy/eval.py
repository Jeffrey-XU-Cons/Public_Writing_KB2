r"""
检索质量评估台：一组贴近真实公文写作任务的查询（覆盖 6 文种 × 6 大类），
跑 top-3 召回，打印表格 + 落 JSON（供判分工作流做前后对比）。

用法：& $py D:\projects\Public_Writing_KB\rag\eval.py --out rag\eval_before.json
"""
import argparse
import json

import _common as C
from pw_query import retrieve

client = C.get_client()

# (id, 说明, 查询, collection, filters)
CASES = [
    ("T1", "汇报骨架", "管理效能攻坚 工作推进情况 汇报", "pw_templates", {"doc_type": "汇报"}),
    ("T2", "实施方案骨架", "卓越绩效 全面导入 实施方案", "pw_templates", {"doc_type": "方案"}),
    ("T3", "讲话骨架", "现场会 领导讲话 安排部署", "pw_templates", {"doc_type": "讲话"}),
    ("T4", "规划骨架", "十五五 发展规划 目标指标", "pw_templates", {"doc_type": "规划"}),
    ("A1", "结构范文", "公文 总体思路 结构层次 成效", "pw_articles", {"layer": "结构"}),
    ("A2", "讲话范文", "讲话稿 开头 抓住听众", "pw_articles", {"doc_type": "讲话"}),
    ("P1", "成效段", "管理效能攻坚 取得成效 指标提升进位", "pw_paragraphs", {"cat2": "主体展开", "min_q": 8.0}),
    ("P2", "开头段", "这次会议的主要任务 传达学习贯彻", "pw_paragraphs", {"cat2": "开头写法"}),
    ("P3", "问题段", "存在问题 短板不足 差距", "pw_paragraphs", {"min_q": 8.0}),
    ("G1", "成就金句", "高质量发展 攻坚克难 谱写新篇章", "pw_golden", {}),
    ("G2", "担当排比", "责任担当 使命在肩 苦干实干", "pw_golden", {}),
    ("N1", "比喻标题", "比喻 做亮标题 抓落实 压舱石", "pw_patterns", {"cat2": "标题规范"}),
    ("N2", "开头句式", "开头 引出主题 承上启下 过渡", "pw_patterns", {}),
    ("D1", "搭配纠错", "制定规划 加强意识 落实任务", "pw_terms", {"cat2": "禁忌错误"}),
    ("D2", "套话识别", "高度重视 进一步加强 扎实推进 空话套话", "pw_terms", {}),
    ("D3", "开头用语", "根据精神 为贯彻落实 现通知如下 开头用语", "pw_terms", {"cat2": "惯用语"}),
    ("P4", "部署段", "下一步 重点任务 强化落实 保障措施", "pw_paragraphs", {"min_q": 8.0}),
    ("A3", "写作技巧", "写材料 立意 观点提炼 避免套路", "pw_articles", {}),
]


def W(filt):
    conds = []
    for k, key in [("layer", "layer"), ("doc_type", "doc_type"), ("cat1", "cat1"), ("cat2", "cat2")]:
        if filt.get(k):
            conds.append({key: filt[k]})
    if filt.get("min_q") is not None:
        conds.append({"quality_score": {"$gte": filt["min_q"]}})
    if not conds:
        return None
    return conds[0] if len(conds) == 1 else {"$and": conds}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out")
    ap.add_argument("--top", type=int, default=3)
    ap.add_argument("--start", type=int, default=0)
    ap.add_argument("--end", type=int, default=len(CASES))
    args = ap.parse_args()
    cases = CASES[args.start:args.end]

    global client
    dump = []
    print(f"{'ID':4} {'说明':10} {'Top1分':7} {'cat1·cat2':20} 来源/摘要")
    for cid, desc, query, coll, filt in cases:
        items = []
        for attempt in range(3):   # ChromaDB 单进程多 collection 偶发 hnsw 段缓存报错 → 清缓存重建 client 重试
            try:
                items = retrieve(client.get_collection(coll), query, top=args.top, rerank=True, where=W(filt))
                break
            except Exception:
                try:
                    import chromadb
                    chromadb.api.client.SharedSystemClient.clear_system_cache()
                except Exception:
                    pass
                client = C.get_client()
        res = [{
            "score": round(float(fin), 3), "cat1": m.get("cat1", ""), "cat2": m.get("cat2", ""),
            "doc_type": m.get("doc_type", ""), "source": m.get("source_file", ""),
            "text": doc[:400],
        } for (sid, doc, m, cos, fin) in items]
        top1 = res[0] if res else {"score": 0, "cat1": "", "cat2": "", "source": "", "text": "（无）"}
        snip = " ".join(top1["text"].split())[:40]
        print(f"{cid:4} {desc:10} {top1['score']:<7.2f} {(top1['cat1']+'·'+top1['cat2']):20} {top1['source'][:20]} | {snip}")
        dump.append({"id": cid, "desc": desc, "query": query, "collection": coll, "filters": filt, "results": res})

    avg = sum(d["results"][0]["score"] for d in dump if d["results"]) / len(dump)
    print(f"\nTop1 rerank 均分：{avg:.3f}（{len(dump)} 例）")
    if args.out:
        from pathlib import Path
        Path(args.out).write_text(json.dumps(dump, ensure_ascii=False, indent=1), encoding="utf-8")
        print(f"[OK] 落 {args.out}")


if __name__ == "__main__":
    main()
