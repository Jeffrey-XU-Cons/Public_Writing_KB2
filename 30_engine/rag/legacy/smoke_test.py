r"""
端到端冒烟测试：取 00_raw_materials 的真实材料主题，跑多层级 RAG 召回，人工核相关性。
模型/reranker 只加载一次。用法：& $py D:\projects\Public_Writing_KB\rag\smoke_test.py
"""
import _common as C
from pw_query import retrieve

client = C.get_client()


def W(**kw):
    conds = []
    if kw.get("layer"): conds.append({"layer": kw["layer"]})
    if kw.get("doc_type"): conds.append({"doc_type": kw["doc_type"]})
    if kw.get("cat1"): conds.append({"cat1": kw["cat1"]})
    if kw.get("cat2"): conds.append({"cat2": kw["cat2"]})
    if kw.get("min_q") is not None: conds.append({"quality_score": {"$gte": kw["min_q"]}})
    if not conds: return None
    return conds[0] if len(conds) == 1 else {"$and": conds}


def show(title, coll, query, top=2, **filt):
    c = client.get_collection(coll)
    items = retrieve(c, query, top=top, rerank=True, where=W(**filt))
    tag = " ".join(f"{k}={v}" for k, v in filt.items())
    print(f"\n▶ {title}  [{coll}]  「{query}」  {tag}")
    if not items:
        print("   （无结果）")
    for i, (sid, doc, m, cos, fin) in enumerate(items):
        snip = " ".join(doc.split())[:72]
        print(f"   #{i+1} {fin:.2f} {m.get('cat1','')}·{m.get('cat2','')} | {m.get('source_file','')[:26]} | {snip}")


print("=" * 78)
print("材料 A（汇报）：河南中烟管理效能攻坚三年行动实施方案起草情况的汇报")
print("=" * 78)
show("结构·骨架", "pw_templates", "管理效能攻坚 工作情况 汇报", doc_type="汇报")
show("结构·范文", "pw_articles", "管理提升 总体思路 工作成效", layer="结构")
show("内容·成效段", "pw_paragraphs", "管理效能攻坚 取得成效 指标提升", cat2="主体展开", min_q=8.0)
show("语言·金句", "pw_golden", "管理效能 高质量发展 攻坚")
show("语言·用词校验", "pw_terms", "制定规划 加强意识 落实任务", cat2="禁忌错误")

print("\n" + "=" * 78)
print("材料 B（方案）：全面导入卓越绩效管理实施方案")
print("=" * 78)
show("结构·骨架", "pw_templates", "卓越绩效 管理提升 实施方案", doc_type="方案")
show("内容·措施段", "pw_paragraphs", "卓越绩效管理 导入 推进措施", min_q=8.0)
show("语言·标题", "pw_patterns", "卓越绩效 提质增效 对标一流", cat2="标题规范")

print("\n[DONE] 冒烟测试完成")
