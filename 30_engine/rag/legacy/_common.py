r"""
公文写作 KB · 本地多层级 RAG —— 共享底座（_common.py）

镜像 tobacco_kb 的离线本地栈：BGE-large-zh-v1.5 (fp16/CUDA) + ChromaDB PersistentClient
+ BGE-reranker-base。复用 tobacco_kb 已下载的 HF 缓存与 reranker，零下载、零装机。

所有 rag/ 脚本（build_index / pw_query / build_bm25 / ingest_industry）都从这里取
环境、模型、client、chunk 工具与 metadata 归一函数。改路径只改这一处。
"""
import sys
try:
    sys.stdout.reconfigure(encoding="utf-8")   # Windows 控制台 cp1252 会崩中文，必须
except Exception:
    pass

import os
import re
import json
import hashlib
from pathlib import Path

# ── 路径（集中一处，便于日后迁移解耦 tobacco_kb）────────────────────────
PW_ROOT = Path(__file__).resolve().parents[1]              # D:\projects\Public_Writing_KB
TOBACCO_ROOT = Path(r"D:\projects\tobacco_kb")             # 复用其 venv/models
CHROMA_DIR = PW_ROOT / "rag" / "index" / "chroma_db"
BM25_DIR = PW_ROOT / "rag" / "index" / "bm25"

MODEL_NAME = "BAAI/bge-large-zh-v1.5"
RERANKER_PATH = TOBACCO_ROOT / "models" / "bge_reranker_base"
QUERY_PREFIX = "为这个句子生成表示以用于检索相关文章："   # BGE 中文检索必需前缀

CHUNK_MIN_CHARS = 50
CHUNK_MAX_CHARS = 1500
CHUNK_OVERLAP = 100

# ── 离线 HF：指向 tobacco_kb 已下好的缓存，不联网 ─────────────────────
for k in ["ALL_PROXY", "all_proxy", "HTTPS_PROXY", "https_proxy", "HTTP_PROXY", "http_proxy"]:
    os.environ.pop(k, None)
os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS_WARNING", "1")
_hf_cache = TOBACCO_ROOT / "models" / "hf_cache"
if (_hf_cache / "hub" / "models--BAAI--bge-large-zh-v1.5").exists():
    os.environ.setdefault("HF_HOME", str(_hf_cache))
    os.environ.setdefault("HF_HUB_OFFLINE", "1")


# ── 懒加载模型 / client（脚本按需调用，避免 import 即加载）──────────────
_model = None
_reranker = None


def get_model(fp16=True):
    global _model
    if _model is None:
        import torch
        from sentence_transformers import SentenceTransformer
        m = SentenceTransformer(MODEL_NAME)
        if fp16 and torch.cuda.is_available():
            m.half()
        _model = m
    return _model


def get_reranker():
    global _reranker
    if _reranker is None:
        import torch
        from sentence_transformers import CrossEncoder
        dev = "cuda" if torch.cuda.is_available() else "cpu"
        _reranker = CrossEncoder(str(RERANKER_PATH), device=dev)
    return _reranker


def get_client():
    import chromadb
    CHROMA_DIR.mkdir(parents=True, exist_ok=True)
    return chromadb.PersistentClient(path=str(CHROMA_DIR))


def batch_size():
    import torch
    return 128 if torch.cuda.is_available() else 16


# ── metadata 归一：Chroma 不接受 None / list / dict，一律转为标量 ────────
META_KEYS = [
    "source_id", "granularity", "layer", "doc_type", "category",
    "term_kind", "quality_score", "position", "source_file",
    "section_path", "year",
    "cat1", "cat2", "tags",   # 六大类分类体系（taxonomy.py）
]


def norm_meta(d: dict) -> dict:
    """把一条 record 的元数据归一为 Chroma 可接受的标量（str/int/float/bool）。
    缺省填空串；list/dict 转 JSON 串；None → ''。"""
    out = {}
    for k in META_KEYS:
        v = d.get(k, "")
        if v is None:
            v = ""
        elif isinstance(v, (list, dict)):
            v = json.dumps(v, ensure_ascii=False)
        elif isinstance(v, bool):
            pass
        elif not isinstance(v, (str, int, float)):
            v = str(v)
        out[k] = v
    return out


# ── Markdown 切段（照搬 ingest_new.py，保证与 tobacco_kb 一致）──────────
def parse_md_to_chunks(md_text: str):
    chunks, current_section, current_text = [], [], []
    for line in md_text.split("\n"):
        m = re.match(r"^(#{1,6})\s+(.+?)\s*$", line)
        if m:
            level, heading = len(m.group(1)), m.group(2).strip()
            if current_text:
                sp = " / ".join(current_section) if current_section else "(无标题)"
                t = "\n".join(current_text).strip()
                if t:
                    chunks.append((sp, t))
                current_text = []
            current_section = current_section[:level - 1]
            current_section.append(heading)
        else:
            current_text.append(line)
    if current_text:
        sp = " / ".join(current_section) if current_section else "(无标题)"
        t = "\n".join(current_text).strip()
        if t:
            chunks.append((sp, t))
    if not chunks and md_text.strip():
        chunks.append(("(无标题)", md_text.strip()))
    return chunks


def split_long_chunk(text, max_chars=CHUNK_MAX_CHARS, overlap=CHUNK_OVERLAP):
    if len(text) <= max_chars:
        return [text]
    parts, current = [], ""
    for p in text.split("\n\n"):
        if len(current) + len(p) + 2 <= max_chars:
            current = current + "\n\n" + p if current else p
        else:
            if current:
                parts.append(current)
            current = p
            while len(current) > max_chars:
                parts.append(current[:max_chars])
                current = current[max_chars - overlap:]
    if current:
        parts.append(current)
    return parts


def path_hash(s: str) -> str:
    return "x" + hashlib.md5(str(s).encode("utf-8")).hexdigest()[:10]


# ── 通用：把一条 dict 记录拼成用于 embedding 的文本 ────────────────────
_SKIP_TEXT_FIELDS = {
    "id", "source", "importance", "usage", "book", "formality_level",
    "applicable_direction", "applicable_position", "position_index",
    "word_count", "length", "chinese_chars", "line", "orig_num",
}


def record_to_text(rec: dict) -> str:
    """把词典/句式类记录的文本型字段拼起来（跳过纯元数据字段）。"""
    parts = []
    for k, v in rec.items():
        if k in _SKIP_TEXT_FIELDS:
            continue
        if isinstance(v, str) and v.strip():
            parts.append(v.strip())
        elif isinstance(v, list):
            parts.extend([str(x).strip() for x in v if isinstance(x, (str, int, float)) and str(x).strip()])
    # 去重保序
    seen, uniq = set(), []
    for p in parts:
        if p not in seen:
            seen.add(p)
            uniq.append(p)
    return " ｜ ".join(uniq)


_ENTRY_START = re.compile(r"^\s*-\s+id:\s*(\S+)")
_KV = re.compile(r"^\s*([A-Za-z_]+):\s*(.*\S)\s*$")


def parse_flat_entries(text: str):
    """行式解析 `- id: X` / `  key: value` 结构。
    用于结构规整但 YAML 解析失败的词典（排比句库/比喻词库：content 值含未转义冒号）。"""
    entries, cur = [], None
    for line in text.split("\n"):
        m = _ENTRY_START.match(line)
        if m:
            if cur:
                entries.append(cur)
            cur = {"id": m.group(1)}
            continue
        if cur is None:
            continue
        kv = _KV.match(line)
        if kv and kv.group(1) != "id":
            cur[kv.group(1)] = kv.group(2).strip().strip("[]")
    if cur:
        entries.append(cur)
    return entries


def load_yaml_records(path: Path):
    """双模加载一个词典 YAML：
    - 结构化：找到列表（entries/terms/policy_terms/sentence_patterns/...）→ [(sid, text, extra_meta), ...]
    - 失败或 markdown 包裹（{content: |...}）：按 md 切段 → [(hash, chunk, {section_path})]
    返回 (records, mode) ；mode ∈ {'records','md'}"""
    import yaml
    raw = path.read_text(encoding="utf-8")
    try:
        data = yaml.safe_load(raw)
    except Exception:
        data = None

    # markdown 包裹型（official_terms_v2 用 content: | 塞了一整篇 md）
    if isinstance(data, dict) and set(data.keys()) <= {"content", "meta", "metadata"} and "content" in data \
            and isinstance(data["content"], str):
        return _md_records(data["content"], path), "md"

    if data is None:  # YAML 解析失败 → 先试行式条目解析，再退化 md 切段
        flat = parse_flat_entries(raw)
        if len(flat) >= 3:
            recs = []
            for i, r in enumerate(flat):
                text = record_to_text(r)
                if len(text) >= 4:
                    recs.append((str(r.get("id") or f"{path.stem}_{i}"),
                                 text, {"category": r.get("category", "")}))
            if recs:
                return recs, "records"
        return _md_records(raw, path), "md"

    # 结构化：找第一个 list of dict
    lst = None
    if isinstance(data, list):
        lst = data
    elif isinstance(data, dict):
        for k, v in data.items():
            if isinstance(v, list) and v and isinstance(v[0], dict):
                lst = v
                break
    if lst is None:
        return _md_records(raw, path), "md"

    recs = []
    for i, rec in enumerate(lst):
        if not isinstance(rec, dict):
            continue
        text = record_to_text(rec)
        if len(text) < 4:
            continue
        sid = str(rec.get("id") or f"{path.stem}_{i}")
        extra = {"category": rec.get("category", "")}
        recs.append((sid, text, extra))
    return recs, "records"


def _md_records(md_text: str, path: Path):
    recs = []
    for ci, (section, chunk) in enumerate(parse_md_to_chunks(md_text)):
        if len(chunk) < CHUNK_MIN_CHARS:
            continue
        for si, sc in enumerate(split_long_chunk(chunk)):
            recs.append((f"{path_hash(path.name)}_{ci}_{si}", sc, {"section_path": section}))
    return recs


def read_jsonl(path: Path):
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                yield json.loads(line)
