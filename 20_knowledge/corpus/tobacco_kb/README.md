# tobacco_kb 迁入资料（语料 · 写作成品 · 召回草料）

2026-10-03 从 `D:/projects/tobacco_kb/output/` 复制迁入（Kb-RAG ADR-030 / STATUS D-068）。tobacco_kb 已弃用：它的 ChromaDB 向量库（bge-large-zh-v1.5）不再保留，**语料和写作资料归本项目所有**；检索一律经 Kb-RAG 的 `search.py`，本项目不自建检索栈。

> ⚠️ **未脱敏、不入库、不外流。** 本目录除本 README 外全部被 `.gitignore` 排除。内容含客户单位名、人名与内部标准原文；任何外流前须走 `30_engine/tools/deid_scan.py` 脱敏流程并人工抽查。

## 三个子目录

| 目录 | 内容 | 用途 |
|---|---|---|
| `语料/` | `chunks_full.jsonl`（69,283 段原文切块，6,654 份源文件，13 个客户域，2016–2025）、`tobacco_kb.db`（52,000 文件清单）、`02_classified.parquet`（文件分类）、`核心语料推荐清单.csv`、`噪音清单.csv`、`henan_full*`/`henan_standards`/`henan_sample`（河南中烟标准抽取）、`烟草行业热词表.md`、`writing_standards.md` | 原文证据的唯一保存处：源文件大多在 `D:/WB文本工作资料`，但**有 460 份原件已不在磁盘，正文只剩 `chunks_full.jsonl`**，不可删 |
| `交付物/` | 安顺 5A 标准化方案与报价、营销算法“方向一～四”研究方案（含各版本）、研究方向大纲、河南中烟欢迎词、改进机会清单 | 历史成稿，大多别处无副本；可作范文/段落库素材（脱敏后） |
| `召回草料/` | 旧 `/draft` 与各主题的召回结果（`draft_*`、`maturity_*`、`sa5a_*`、`rag_direction*`）、`jcgl_review/`、`lianxi/`、`findings_md/`、`pxfz_*.json` | 成稿过程留痕，追溯出处用 |

`manifest.tsv` 逐文件记录分组、相对路径、字节数与 SHA256（复制时已逐个校验一致）。

## 以后怎么用

- **现在**：只作档案与素材，不可检索。要查原文按 `manifest.tsv` 找文件，或直接 grep `chunks_full.jsonl`
- **原文检索（未建，看需求）**：Kb-RAG STATUS 的“缺原文登记”攒够 3–5 次真实需求后，再走 Kb-RAG 新 ADR 建原文证据层。届时沿用 ADR-029 的模式：**数据主权在本项目，Kb-RAG 只读导入、用 bge-m3 建索引、经 `search.py` 调用**，不在 Kb-RAG 里改数据
- tobacco_kb 原目录里的同名文件是旧副本，随其阶段 5 归档；以本目录为准
