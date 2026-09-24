r"""
公文写作 KB · 本地多层级 RAG —— 建索引主入口（collection 1-6）

用法（在 tobacco_kb 的 venv 下跑）：
  $py = "D:\projects\tobacco_kb\.venv-cuda\Scripts\python.exe"
  & $py D:\projects\Public_Writing_KB\rag\build_index.py --reset            # 建全部 1-6
  & $py D:\projects\Public_Writing_KB\rag\build_index.py --only pw_terms --reset
  & $py D:\projects\Public_Writing_KB\rag\build_index.py --dry-run          # 只统计不入库

多层级 = 按「粒度」分 collection + metadata.layer 过滤。industry 文章走 ingest_industry.py。
"""
import argparse
import time

import _common as C
import taxonomy

D = C.PW_ROOT


# ── doc_type 归一到 {汇报,总结,方案,规划,调研,讲话,简报,通用} ──────────
def norm_doctype(s):
    s = str(s or "")
    for kw, dt in [
        ("讲话", "讲话"), ("发言", "讲话"),
        ("规划", "规划"), ("计划", "规划"),   # 发展规划/工作计划→规划；实施方案→方案（下）
        ("方案", "方案"),
        ("调研", "调研"),                     # 调研报告→调研（须在“报告”之前）
        ("简报", "简报"),
        ("汇报", "汇报"), ("经验", "汇报"),
        ("总结", "总结"), ("报告", "总结"),
    ]:
        if kw in s:
            return dt
    return "通用"


def _num(x, default=0.0):
    try:
        return float(x)
    except (TypeError, ValueError):
        return default


import re as _re

_FRONTMATTER = _re.compile(r"^\s*---\s*\n.*?\n---\s*\n", _re.DOTALL)
_paren = _re.compile(r"^\s*[（(][^）)]{0,25}[）)]\s*")
# 文档标题/开场噪声（corpus_golden 里混入的报告标题、讲话开场，非金句）
_TITLE_NOISE = _re.compile(r"(同志们[：:]|在.{2,30}(会议|大会|工作会).{0,12}(上的)?(报告|讲话|发言)|起草情况的说明)")
# 词典 intro/更新日志类噪声
_TERM_NOISE = _re.compile(r"(本词典收集|更新日志|^#+\s*简介|版本[:：])")


def strip_frontmatter(text):
    return _FRONTMATTER.sub("", text, count=1)


def rec(source_id, text, **meta):
    m = {"source_id": source_id, "text": text}
    m.update(meta)
    return m


# ══════════════════════════════════════════════════════════════════════
# LOADERS：每个返回 list[dict{source_id,text,+META_KEYS}]
# ══════════════════════════════════════════════════════════════════════

def _skeleton_sections(v):
    """structure_skeleton 可能是 list[dict] 或其 str repr；抽出各 section 名。"""
    import ast
    if isinstance(v, str):
        try:
            v = ast.literal_eval(v)
        except Exception:
            return []
    if isinstance(v, list):
        return [str(s.get("section", "")) for s in v if isinstance(s, dict) and s.get("section")]
    return []


def _tpl_text(title, dt, sub, usage, skeleton, constraints):
    import ast
    secs = _skeleton_sections(skeleton)
    if isinstance(constraints, str):
        try:
            constraints = ast.literal_eval(constraints)
        except Exception:
            constraints = [constraints]
    cons = [str(x) for x in (constraints or [])][:3]
    parts = [x for x in [title, dt, sub, usage] if x]
    if secs:
        parts.append("骨架：" + "；".join(secs))
    if cons:
        parts.append("要点：" + "；".join(cons))
    return " ｜ ".join(parts)


def load_templates():
    import json
    import yaml
    out, seen = [], set()

    # 1) 富模板 JSON（title+usage_scene+骨架章节+约束）——含实施方案/汇报/计划/纪要/制度
    for fp in sorted((D / "01_templates").rglob("*.json")):
        try:
            j = json.loads(fp.read_text(encoding="utf-8"))
        except Exception:
            continue
        if not isinstance(j, dict) or not j.get("doc_type"):
            continue
        tid = str(j.get("template_id") or fp.stem)
        dt_raw = str(j.get("doc_type", ""))
        title = str(j.get("title", ""))
        text = _tpl_text(title, dt_raw, str(j.get("sub_type", "")), str(j.get("usage_scene", "")),
                         j.get("structure_skeleton"), j.get("constraints"))
        if len(text) < 6:
            continue
        seen.add(tid)
        out.append(rec(tid, text, granularity="skeleton", layer="结构",
                       doc_type=norm_doctype(dt_raw + title), category=dt_raw,
                       source_file=str(fp.relative_to(D))))

    # 2) A2 多文档骨架 YAML（补 讲话/报告 等 46 个 JSON 未覆盖的文体）
    for a2 in sorted((D / "01_templates").glob("A2_*.yaml")):
        try:
            docs = [d for d in yaml.safe_load_all(a2.read_text(encoding="utf-8")) if isinstance(d, dict)]
        except Exception:
            docs = []
        for i, d in enumerate(docs):
            dt_raw = str(d.get("doc_type", ""))
            if not dt_raw:
                continue
            tid = f"A2_{a2.stem[:8]}_{dt_raw}_{i}"
            text = _tpl_text("", dt_raw, "", str(d.get("usage_scene", "")),
                             d.get("structure_skeleton"), d.get("constraints"))
            if len(text) < 6:
                continue
            seen.add(tid)
            out.append(rec(tid, text, granularity="skeleton", layer="结构",
                           doc_type=norm_doctype(dt_raw), category=dt_raw, source_file=a2.name))

    # 3) templates_import 兜底：无 JSON 的薄模板（新闻/简报/事迹等，保覆盖）
    for r in C.read_jsonl(D / "data_prep" / "templates_import.jsonl"):
        tid = str(r.get("template_id") or r.get("id"))
        if tid in seen:
            continue
        name = str(r.get("name", "")).lstrip(". ").strip()
        dt_raw = str(r.get("doc_type", "")).strip()
        text = " ｜ ".join([x for x in [name, dt_raw, str(r.get("sub_type", "")).lstrip(". ").strip(),
                                        str(r.get("usage", ""))] if x])
        if len(text) < 4:
            continue
        out.append(rec(tid, text, granularity="skeleton", layer="结构",
                       doc_type=norm_doctype(dt_raw + name), category=str(r.get("usage", "")),
                       source_file=str(r.get("file_path", ""))))
    return out


def load_articles():
    import json
    idx = {}
    idx_path = D / "04_corpus" / "selected_articles" / "article_index.json"
    if idx_path.exists():
        for a in json.loads(idx_path.read_text(encoding="utf-8")):
            idx[a["article_id"]] = a
    out = []
    for fp in sorted((D / "04_corpus" / "selected_articles").glob("TA-*.md")):
        aid = fp.stem
        meta_a = idx.get(aid, {})
        dtypes = meta_a.get("doc_types") or ["通用"]
        doc_type = norm_doctype(dtypes[0])
        title = meta_a.get("title", fp.stem)
        ctype = meta_a.get("content_type", "")
        text = strip_frontmatter(fp.read_text(encoding="utf-8", errors="ignore"))
        for ci, (section, chunk) in enumerate(C.parse_md_to_chunks(text)):
            if len(chunk) < C.CHUNK_MIN_CHARS:
                continue
            for si, sc in enumerate(C.split_long_chunk(chunk)):
                out.append(rec(
                    f"{aid}_{ci}_{si}", sc,
                    granularity="document", layer="结构", doc_type=doc_type,
                    category=ctype, source_file=title, section_path=section,
                ))
    return out


def load_paragraphs():
    out = []
    for r in C.read_jsonl(D / "data_prep" / "corpus_paragraphs.jsonl"):
        content = str(r.get("content", "")).strip()
        if len(content) < 10:
            continue
        out.append(rec(
            str(r.get("id")), content,
            granularity="paragraph", layer="内容", doc_type="通用",
            category=str(r.get("category", "")), quality_score=_num(r.get("quality_score")),
            position=str(r.get("position", "")), source_file=str(r.get("source_file", "")),
        ))
    return out


def load_golden():
    out = []
    # 1) corpus 金句（滤掉混入的文档标题/讲话开场/#小节头）
    for r in C.read_jsonl(D / "data_prep" / "corpus_golden_sentences.jsonl"):
        content = _paren.sub("", str(r.get("content", "")).strip())
        if len(content) < 6 or content.startswith("#") or _TITLE_NOISE.search(content):
            continue
        if len(content) > 200:  # 金句/排比不会太长，过长多为整段
            continue
        out.append(rec(
            str(r.get("id")), content,
            granularity="sentence", layer="语言", doc_type="通用",
            category=str(r.get("category", "金句")), source_file=str(r.get("source_file", "")),
        ))
    # 2) 词典金句/排比/比喻（结构化优先，坏文件退化 md 切段）
    for fp in sorted((D / "03_dictionary" / "golden_sentences").glob("*.yaml")):
        recs, mode = C.load_yaml_records(fp)
        for sid, text, extra in recs:
            if len(text) < 6:
                continue
            out.append(rec(
                sid, text, granularity="sentence", layer="语言", doc_type="通用",
                category=extra.get("category", "") or fp.stem, source_file=fp.name,
                section_path=extra.get("section_path", ""),
            ))
    return out


def load_patterns():
    out = []
    specs = [
        (D / "03_dictionary" / "title_patterns", "title"),
        (D / "03_dictionary" / "sentence_patterns", "pattern"),
    ]
    for folder, gran in specs:
        for fp in sorted(folder.glob("*.yaml")):
            recs, mode = C.load_yaml_records(fp)
            for sid, text, extra in recs:
                if len(text) < 4:
                    continue
                out.append(rec(
                    sid, text, granularity=gran, layer="语言", doc_type="通用",
                    category=extra.get("category", "") or fp.stem, source_file=fp.name,
                    section_path=extra.get("section_path", ""),
                ))
    return out


def _term_kind(text):
    for kw, kind in [("禁用", "禁用词"), ("不得使用", "禁用词"), ("错误写法", "搭配规范"),
                     ("易错搭配", "搭配规范"), ("搭配", "搭配规范"), ("套话", "套话替换"),
                     ("替换", "套话替换")]:
        if kw in text:
            return kind
    return "术语"


def load_terms():
    out = []
    # 1) official_terms_v2（content:| 包裹的 md，按小节切段）
    recs, mode = C.load_yaml_records(D / "03_dictionary" / "official_terms_v2.yaml")
    for sid, text, extra in recs:
        if len(text) < 8 or _TERM_NOISE.search(text):
            continue
        out.append(rec(
            sid, text, granularity="term", layer="语言", doc_type="通用",
            category="公文用语", term_kind=_term_kind(text),
            source_file="official_terms_v2.yaml", section_path=extra.get("section_path", ""),
        ))
    # 2) tobacco_terms 各 yaml
    for fp in sorted((D / "03_dictionary" / "tobacco_terms").glob("*.yaml")):
        recs, mode = C.load_yaml_records(fp)
        for sid, text, extra in recs:
            if len(text) < 4:
                continue
            out.append(rec(
                sid, text, granularity="term", layer="语言", doc_type="通用",
                category=extra.get("category", "") or fp.stem, term_kind="术语",
                source_file=fp.name,
            ))
    return out


LOADERS = {
    "pw_templates": load_templates,
    "pw_articles": load_articles,
    "pw_paragraphs": load_paragraphs,
    "pw_golden": load_golden,
    "pw_patterns": load_patterns,
    "pw_terms": load_terms,
}


def embed_and_store(client, name, records, reset, dry):
    # 1) 文本去重：完全相同正文只留第一条（corpus 有重复段落）
    seen, deduped = set(), []
    for r in records:
        key = r["text"].strip()
        if key in seen:
            continue
        seen.add(key)
        deduped.append(r)
    records = deduped
    # 2) ID 唯一化：跨文件/同文件 id 冲突时加后缀，保全所有条目（排比库 GS-0xx 有复用）
    seen_ids = {}
    for r in records:
        sid = str(r["source_id"])
        if sid in seen_ids:
            seen_ids[sid] += 1
            r["source_id"] = f"{sid}#{seen_ids[sid]}"
        else:
            seen_ids[sid] = 0
    print(f"\n[{name}] 记录 {len(records)} 条（去重后）", flush=True)
    if dry:
        for r in records[:3]:
            print(f"   e.g. [{r['source_id']}] {r['text'][:70]}...")
        return
    if not records:
        print("   （空，跳过）")
        return
    if reset:
        try:
            client.delete_collection(name)
        except Exception:
            pass
    try:
        coll = client.get_collection(name)
    except Exception:
        coll = client.create_collection(name=name, metadata={"hnsw:space": "cosine"})

    model = C.get_model()
    bs = C.batch_size()
    t0 = time.time()
    for i in range(0, len(records), bs):
        batch = records[i:i + bs]
        texts = [r["text"] for r in batch]
        embs = model.encode(texts, batch_size=bs, show_progress_bar=False, normalize_embeddings=True)
        coll.upsert(
            ids=[str(r["source_id"]) for r in batch],
            embeddings=embs.tolist(),
            documents=texts,
            metadatas=[C.norm_meta(r) for r in batch],
        )
    print(f"   入库完成 count={coll.count()} 耗时{time.time()-t0:.1f}s", flush=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", help="只建某个 collection")
    ap.add_argument("--reset", action="store_true", help="建前清空该 collection")
    ap.add_argument("--dry-run", action="store_true", help="只统计不入库、不加载模型")
    args = ap.parse_args()

    targets = [args.only] if args.only else list(LOADERS.keys())
    for t in targets:
        if t not in LOADERS:
            print(f"[ERROR] 未知 collection: {t}（可选 {list(LOADERS)}）")
            return

    client = None if args.dry_run else C.get_client()
    grand = 0
    for name in targets:
        records = LOADERS[name]()
        taxonomy.tag_records(name, records)   # 打六大类标签 cat1/cat2/tags
        grand += len(records)
        embed_and_store(client, name, records, args.reset, args.dry_run)
    print(f"\n[DONE] {'(dry-run) ' if args.dry_run else ''}共 {grand} 条，collection: {targets}")


if __name__ == "__main__":
    main()
