---
name: gw-ingest
description: 公文库入库编排——QA 批次走 kb_ingest（dry-run→正式入库，内嵌校验、精确判重、审计，不过整批回滚），抽检后用 kb_mark_checked 标记；范文批次文件校验、查重号后并入 articles.jsonl；交代 ThinkBook 上的 Kb-RAG 导入建索引与提交。触发：「入库」「把 B-XXX 入库」「正式入库」「标记抽检完成」「范文批次入库」「合并范文批次」「建索引」。不响应：萃取本身（gw-extract，含“拆解这篇范文入库”——那是把范文萃成 QA）、库体检与脱敏扫描（gw-audit）、写稿（gongwen）、把文件放进 10_source 的“导入语料”。
---

# gw-ingest · 入库编排（SOP ④—⑩）

依据：04 章§4.1（存储与人工编辑纪律）、§4.4（十步 SOP）、§4.6（门禁）；`30_engine/runs/P5_第1轮_ThinkBook收尾.md`（⑥—⑩的实跑记录）。
**门禁在脚本的退出码上**，本 skill 只负责按顺序调用和如实报告，不替脚本放行。

## 开工前三查

1. 另一台机器没有在写本项目（双机规则：同一时刻只一台写，Syncthing 不做合并）；目录里没有 `*.sync-conflict-*`，有就报告 Jeffrey，不自行处理。
2. 全库审计当前是干净的：kb_ingest 正式入库后跑全量 audit，**库里任何地方有 error 都会让本批整体回滚**，所以先排除旧债：
```
python3 30_engine/tools/kb_audit.py
```
3. 批次已由 gw-extract 跑过 dry-run 并在 plan.md 写了完成报告。

Windows 上把 `python3` 换成 `python`；全部为标准库脚本，两台机器都能跑。

## A · QA 批次入库

**④ 先验，再正式入库**：
```
python3 30_engine/tools/kb_ingest.py --batch 30_engine/batches/B-YYYYMMDD-NN --dry-run
python3 30_engine/tools/kb_ingest.py --batch 30_engine/batches/B-YYYYMMDD-NN
```
- **已入库的批次不要再跑 dry-run 或正式入库**：精确判重会把本批每条都判成与库内重复，并用失败报告**覆盖**批次目录里原来的 `check_report.md`（入库成功记录随之丢失）。先用下面“亲自数”的命令确认该 batch_id 在库里是 0 条，再跑。
- 脚本内顺序：解析 15 列表 → 分配 id → 逐条校验 → answer_hash 与全库精确判重 → 原子写入各大类文件 → 全量 audit；任何一关不过，本批不进库（已写的整批回滚），原因写进批次目录的 `check_report.md`。
- 成功后读 `check_report.md`，**亲自数**新增 id（不信自报）：
```
python3 -c "import json,glob,sys;ids=[r['id'] for f in glob.glob('20_knowledge/qa/c*.jsonl') for r in map(json.loads,open(f,encoding='utf-8')) if r['batch_id']==sys.argv[1]];print(len(ids),'条',ids[:3],'…',ids[-3:])" B-20261003-01
```

**⑤ 校验**（kb_ingest 已内嵌；手改 JSONL 后必须紧跟一次）：
```
python3 30_engine/tools/kb_validate.py
```

**⑥ 判重**：精确判重 kb_ingest 已做；向量近重复只在 ThinkBook 跑（见 gw-audit），过线对交 Jeffrey 逐对判定合并／保留／废弃。7050 上入库的批次，在这一步做完之前不算闭环。

**⑦ 专家抽检**：按 batch_id 抽 max(5 条, 10%)，合格率 ≥90%，否则整批打回 gw-extract 第③步。**强制差评**：必须点名本批最差一条及问题，不许交全优白卷。
- 抽检人是 Jeffrey。Claude 只有在 Jeffrey 明确授权时代检，并在 plan.md 写明“Claude 代检，非专家本人”；代检必须把本批全部答案的数字回源核对。
- 修正：04 章设计的网页编辑页 kb_editor.py **尚未建成**，不要调用。改条目的合法路径只有一条：直接编辑 JSONL，紧跟 `kb_validate`；批量修正写成迁移脚本放 `30_engine/tools/migrations/`（先例 `30_engine/tools/migrations/20261003_p5_spotcheck_fix.py`），改 answer 后 answer_hash 要重算。
- 抽检通过后标记（可同时定级 A/B/C；脚本末尾自动再校验、再审计）：
```
python3 30_engine/tools/kb_mark_checked.py --batch B-YYYYMMDD-NN
```

**⑧ 审计**：
```
python3 30_engine/tools/kb_audit.py
```
04 章写的 `--scope 本批` 参数**不存在**，只有全量与 `--fast` 两档。

**台账**：`20_knowledge/qa/_manifest.yaml` 对应来源追加本批；CLAUDE.md §〇 的条数统计由 Jeffrey 或总控会话更新，本 skill 只报告新数字。

**回退**：不物理删除、id 不回收。整批撤回 = 把该 batch_id 的记录 `status` 改为 deprecated（写迁移脚本），再跑校验与审计。

## B · 范文批次入库

范文由标注规格产出（讲话类 `30_engine/runs/B-20261004-AR-01_讲话范文标注规格.md`，其他文种 `30_engine/runs/B-20261007-AR-02_多文种范文标注规格.md`），标注者写批次目录下的分文件，**不直接写** `20_knowledge/articles/articles.jsonl`；并行标注时按号段预分配 id，合并不重编。

1. **逐文件校验**（0 条不合格才往下走）：
```
python3 -c "import sys,json;sys.path.insert(0,'30_engine/tools');import kb_validate;F=sys.argv[1];bad=[(i,e) for i,l in enumerate(open(F,encoding='utf-8'),1) if l.strip() for e in [kb_validate.validate_article(json.loads(l))] if e];[print(i,e) for i,e in bad];print('不合格',len(bad),'条')" 30_engine/batches/B-20261007-AR-02/汇报材料.jsonl
```
2. **查重号**（与库内、批内）：
```
python3 -c "import json,sys;old={json.loads(l)['id'] for l in open('20_knowledge/articles/articles.jsonl',encoding='utf-8') if l.strip()};new=[json.loads(l)['id'] for l in open(sys.argv[1],encoding='utf-8') if l.strip()];print('与库重号',sorted(old&set(new)) or '无','｜批内重号',len(new)-len(set(new)),'｜待并入',len(new),'条')" 30_engine/batches/B-20261007-AR-02/汇报材料.jsonl
```
   有重号就停，回标注规格查号段，不自行改号。
3. **并入**：多个分文件由**一个会话统一合并**，不并行写 articles.jsonl。逐个文件把行追加到 articles.jsonl 末尾（Claude 用 Edit／Write 追加，或写进迁移脚本；不手抄字段）。并入后跑：
```
python3 30_engine/tools/kb_audit.py
```
   audit 查 JSON、范文 id 唯一、字段与 `source_path`、`linked_qa` 指向存在的 QA。
4. **回退**：按 batch_id 过滤删除本批行，再跑 audit。
5. 范文目前不进 Kb-RAG 索引（gw-draft、gw-search 直读 jsonl），不需要 ThinkBook 步骤。

## C · ThinkBook 收尾（⑨⑩，7050 做不了）

7050 无 git、无 Kb-RAG 运行环境。QA 入库后交 Jeffrey 或 ThinkBook 会话执行（解释器取 Kb-RAG CLAUDE.md“运行环境”当时规定的，下记 KPY；cwd = Kb-RAG）：
```
KPY tools/kb_import.py public_writing_qa
KPY tools/kb_index.py public_writing_qa
KPY tools/search.py --kb public_writing_qa --top 5 --q "新条目首问" --json
```
- 冒烟 10 条：每条取一个新条目的问法，Top5 命中即过，门槛 ≥8/10；再跑 F6 回归（命令见 gw-search「回归」）。
- 冒烟只证明进了索引、能被召回，不证明换个说法也能找到。
- ⑩ 提交：jsonl 与 `30_engine/batches/` 同一个 commit，支持整批回滚；push 由 Jeffrey 定。
- 做法与判读先例：`30_engine/runs/P5_第1轮_ThinkBook收尾.md`。

## 硬规则

- 不改校验器、不放宽门禁来让批次过关；校验器只有一份（`30_engine/tools/kb_validate.py`）。
- 同一批连续 3 次入库失败，停下报告。
- 未完成的步骤如实报“未做”，不报“已入库可检索”——7050 上入库的条目在 ThinkBook 重建索引之前检索不到。
