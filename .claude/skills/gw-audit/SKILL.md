---
name: gw-audit
description: 公文库体检——全库校验与审计（kb_validate、kb_audit）、单测回归、脱敏残留扫描（deid_scan）、语料空壳与重复扫描（corpus_scan）、QA 向量近重复判重（kb_dedup_vec，仅 ThinkBook），汇总成红黄绿灯与修复清单。只读不修。触发：「审计知识库」「知识库体检」「质量门禁」「脱敏扫描」「查脱敏漏网」「语料查重」「向量判重」。不响应：稿件机检 draft_lint（归 gw-review）、修数据与入库（归 gw-ingest 或迁移脚本）、做脱敏本身之外的语料加工。
---

# gw-audit · 库体检

依据：04 章§4.6（门禁指标）、07 章（脱敏）、CLAUDE.md §4.2 与“语料/脱敏”状态行、`20_knowledge/corpus/清理清单_空壳与重复_说明.md`。
本 skill **只读、只出清单**：查出的问题交 gw-ingest、迁移脚本或 Jeffrey 处理，不在体检里顺手改数据。

## 两台机器能跑什么

| 检查 | 7050 | ThinkBook | 命令 |
|---|---|---|---|
| ① 全库校验 | 能 | 能 | kb_validate |
| ② 全库审计 | 能 | 能 | kb_audit |
| ③ 单测回归 | 能 | 能 | pytest |
| ④ 脱敏残留扫描 | 能 | 能 | deid_scan |
| ⑤ 语料空壳与重复 | 能 | 能 | corpus_scan |
| ⑥ 向量近重复 | **不能**（无模型） | 能 | kb_dedup_vec |
| ⑦ 检索回归 | **不能** | 能 | run_f6_kbrag（见 gw-search） |

7050 上跑不了的项，在报告里写“未跑（仅 ThinkBook）”，不写“通过”。Windows 上把 `python3` 换成 `python`。

## ① 全库校验

```
python3 30_engine/tools/kb_validate.py
```
不带参数查全部 QA 大类文件；退出码 0 = 全部合格。

## ② 全库审计

```
python3 30_engine/tools/kb_audit.py
python3 30_engine/tools/kb_audit.py --fast
```
- 全量查：A JSON 逐行可解析（QA 与范文库）、B 每条过校验、C id 与 answer_hash 唯一、范文 linked_qa 指向存在的 QA、D 卫生（禁用命名、根目录文档白名单、skill 直引索引路径）。`--fast` 跳过 B 和 D。
- 退出码 0 = 无 error（warning 允许，逐条列出）。
- 04 章写的 `--scope`、索引一致性（E 项）、文档一致性（G 项）、golden Top5 命中率，**脚本里都还没有**；06 章设想的 kb_eval.py 也未建。不要声称查过这些项，在报告“未覆盖”栏如实列出。

## ③ 单测回归

7050：
```
.venv/bin/python -m pytest 40_tests/kb_ingest -q
```
ThinkBook：用本项目规定的 Windows 解释器跑同一目录（见 `30_engine/runs/P5_第1轮_ThinkBook收尾.md` 末尾“解释器”）。`test_skills.py` 在 Windows 上偶发 WinError 6，连跑复核后再判回归。
其中 `40_tests/kb_ingest/test_draft_lint_golden.py` 是 82 份真实成稿的机检基线，脱敏批次不在本机时自动跳过。

## ④ 脱敏残留扫描（任何脱敏批次出炉后必跑，外流前必跑）

```
python3 30_engine/tools/deid_scan.py 30_engine/batches/B-20261004-deid-个人历史交付物-r10 --names 30_engine/batches/B-20261004-deid-个人历史交付物-r10/names_confirmed.txt
```
- 退出码 1 = 有**硬泄露**（已知真名仍在、省市名留在豁免短语之外）→ 该批次一律不外流。
- **先确认路径对**：脚本只扫目录下的 `*.md`，不检查目录是否存在；路径写错、目录为空也照样输出“硬泄露 0 处”、退出码 0（2026-10-07 核查实测：传不存在的目录、传 `--help` 都报 0）。扫描前先数文件，数为 0 的扫描结果作废：
```
python3 -c "import pathlib,sys;print(len(list(pathlib.Path(sys.argv[1]).glob('*.md'))),'份 .md')" 30_engine/batches/B-20261004-deid-个人历史交付物-r10
```
- 候选（名单、人员表、裸名＋动词、地名）**不是结论**，多数是普通词，要人工筛；确认的回填 deidentify 的地名表或批次姓名名单，重跑脱敏，再扫。
- 不认 `--help`，别用它试探；加 `--json` 出机读结果。扫描输出含真名，只在本机看，不贴进任何会外流的文件。
- 产出新脱敏批次的完整顺序：`deidentify.py --harvest` 收姓名候选 → 人工核对成名单 → `deidentify.py --names 名单` 正式跑 → 本扫描。只给新规则补一刀时，照 `30_engine/tools/migrations/20261004_deid_r9_to_r10.py` 的做法施加在上一版上，不重跑整条管线。
```
python3 30_engine/tools/deidentify.py --harvest 输出目录 文件1.md 文件2.md
python3 30_engine/tools/deidentify.py --names 名单.txt 输出目录 文件1.md 文件2.md
```
  输出目录不能是 `10_source` 或其子目录（脚本会拒绝）；`deid_changes.jsonl` 含原名，本机专用。deidentify 也不认 `--help`（不带位置参数直接报错退出，不写文件）。注意它**会写文件**，不属于体检的只读动作：体检只跑 deid_scan，重跑脱敏是另起的加工任务。
- 当前有效版是 r10；4 份带密级标记的文件整份不外流（清单 `20_knowledge/corpus/不外流清单_密级标记.txt`）。

## ⑤ 语料空壳与重复

```
python3 30_engine/tools/corpus_scan.py 30_engine/runs/corpus_scan_YYYYMMDD.json
```
- 只读 `10_source/raw_materials`；第一个参数是**输出文件路径**，不认 `--help` 之类的选项（传什么都当文件名写）。
- 不给参数会覆盖现有清单 `20_knowledge/corpus/清理清单_空壳与重复.json`。体检时写新文件，与现有清单比对差异；要更新正式清单由 Jeffrey 定。
- 判据（说明文件里有校准过程）：正文去 frontmatter 后不足 200 字算空壳；去空白与标点后全同算重复。
- 清单只列不删：物理删除会经 Syncthing 传到 ThinkBook，删不删由 Jeffrey 定。

## ⑥ 向量近重复（仅 ThinkBook）

用 Kb-RAG 建索引的同一个嵌入模型，必须用 Kb-RAG 规定的解释器（下记 KPY，见 Kb-RAG CLAUDE.md“运行环境”），在本项目根目录跑：
```
KPY 30_engine/tools/kb_dedup_vec.py --percentile 99 --out 30_engine/runs/向量判重清单_YYYYMMDD.md
```
- 本库分数挤在 0.43—0.86，固定 0.92 阈值永远不触发，按全库分布取 P99（2026-10-02 Jeffrey 定）。
- 只读；`--out` 出逐对判定清单，判定列和理由列留空交 Jeffrey 填合并／保留／废弃，合并由迁移脚本执行（先例 `30_engine/tools/migrations/20261003_p5_dedup_merge.py`）。
- 查指定对：`--pairs QA-C6-00018,QA-C6-00014`。

## 汇总报告（红黄绿灯）

| 灯 | 判据 |
|---|---|
| 红 | 任一检查 error、硬泄露、单测失败 |
| 黄 | 只有 warning、待人工筛的候选、待判定的向量对、未跑项 |
| 绿 | 跑了的全部 0 error 0 warning，且未跑项已写明原因 |

报告按“检查项｜灯｜数字｜修复建议｜由谁处理”逐行写，数字照脚本输出抄，不估算。最后一栏写清哪些项本次没覆盖。
