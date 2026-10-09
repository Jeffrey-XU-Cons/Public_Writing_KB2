---
name: gw-extract
description: 公文域知识萃取成 QA 批次——按 P5 分组方案选篇、建批次、写 plan.md 预估与去重表、首件给 Jeffrey 抽读、整组写 15 列 raw_output.md，跑到 kb_ingest --dry-run 通过为止（04 章十步 SOP 第①—④步）。触发须带“公文库／入库／G 组”字样：「萃取入公文库」「做一批公文 QA」「跑 G03 组」「拆解这篇范文入库」。不响应：通用书籍萃取（全局 book2qa）、把资料蒸馏成 skill（knowledge-distiller）、范文标注（按范文标注规格做，入库归 gw-ingest）、正式入库与抽检（gw-ingest）。
---

# gw-extract · 公文知识萃取（SOP ①—④）

依据：04 章§4.1（schema）、§4.4（十步 SOP）；08 章§2.3（双档答案）；07 章（depth/enforce/挂钩链）；`30_engine/runs/P5_三源萃取分组方案.md`（分组、节奏、判重纪律）。
产出物是**批次**：`30_engine/batches/B-YYYYMMDD-NN/` 下的 `plan.md` 与 `raw_output.md`。本 skill **不写 `20_knowledge/`**，入库交 gw-ingest。

## 铁律（违反即停）

1. **首件铁律**：每组、每个新子类，先萃 1 篇（章）交 Jeffrey 抽读口径，确认后才做整组。首件之前禁止批量。
2. **真实性**：答案里的数字、案例、比例必须能在素材原文里找到；原文没有数字就写定性描述。2026-10-03 抽检查出过 1 处编造比例，回源核对是必做项，不是可选项。
3. **答案不带来源信息**：不写书名、作者、篇名、客户名、人名；出处只进 `source_path`、`source_anchor` 两列。
4. **单批 30—50 条封顶**，超了按篇目或章节拆 a/b 两批，不拆单篇。实产比预估高出三成以上，停下查是不是把一个知识点拆碎了。
5. **一条一主类**：每行填自己的 category_l1，跨类靠 tags，不重复入库；一批可跨六大类，kb_ingest 按行路由。
6. **节奏**：每萃 3 批实写 1 篇（P5 纪律）；讲评型篇目暂缓（2026-09-28 裁定）；顺序按缺口排，不按素材排。
7. **素材转换只用全局 `to-md`**，不自写转换脚本；回源一律按“文件＋行号区间”取，不把原文复制进批次目录。
8. **个人交付物（M2 拆解）只用脱敏批次**（当前有效版 r10），不碰 `10_source` 里的原件；答案里不得出现〔A 省中烟〕这类占位以外的任何单位与人名。

## 两台机器的分工

| 步骤 | 7050 | ThinkBook |
|---|---|---|
| ①—④ 登记、预估、萃取、dry-run | 能 | 能 |
| ⑥后半 向量近重复判重 | **不能**（无模型） | 能（见 gw-audit） |
| ⑨ 导入 Kb-RAG、建索引、冒烟；⑩ git 提交 | **不能** | 能（见 gw-ingest） |

所以 7050 上萃出的批次，在 ThinkBook 做完向量判重之前不算闭环。开工前先确认另一台没有在写本项目（双机规则）。

## 第①步 · 登记

1. 定批次号：当天日期＋两位序号，不与已有目录重名。列当天已有批次（参数换成当天日期；脱敏、范文、C2 等批次也占当天的目录名，一并避开）：
```
python3 -c "import pathlib,sys;print(sorted(p.name for p in pathlib.Path('30_engine/batches').iterdir() if p.name.startswith('B-'+sys.argv[1])))" 20261007
```
2. 建 `30_engine/batches/B-YYYYMMDD-NN/`。
3. 在 `20_knowledge/qa/_manifest.yaml` 对应来源下**只追加**本批（S1 技巧汇编追加 `articles`／`batches`，书籍追加 `batches` 与章节说明）。移出本轮的来源不登记（方案开头的 2026-09-29 裁定）。

## 第②步 · 预估报告 plan.md（宁低勿高）

样板：`30_engine/batches/B-20260914-01/plan.md`。至少写：

- **素材范围**：P5 组从 `30_engine/runs/P5_技巧汇编篇目分组.tsv` 取本组篇目（group 列），逐篇写文件与 `line_start–line_end`；篇号以筛选结果为准，不以原文目录为准（汇编三第 7 篇之后差 1）。定位表可重跑（会覆盖原表，只在怀疑行号错位时跑，跑完比对分组 TSV 的行号）：
```
python3 30_engine/tools/source_locate.py --out 10_source/manifest/技巧汇编_篇目定位.tsv
```
- **与已入库条目的去重表**（本批最关键的一节）：先列目标小类已有条目，逐条写“不碰／部分重叠只补什么／合并增强”：
```
python3 -c "import json,sys;[print(r['id'],r['status'],r.get('depth',''),r['question'].split(' / ')[0][:40]) for r in map(json.loads,open(sys.argv[1],encoding='utf-8')) if r['category_l2']==sys.argv[2]]" 20_knowledge/qa/c3_结构与逻辑.jsonl 模块写法
```
  组内已知重叠对（方案§五）只出一条，后读到的更深阐述并入。跨组重复不在这里裁决，交第⑥步判重。
- **归类预判**：每个拟定主题的 category_l1／l2、answer_type、depth、档（lite／full）。
- **预估条数**：按方案§三的校准密度估，写明依据。

## 第③步 · 萃取 raw_output.md

格式契约见 `references/raw-output-format.md`（15 列表头、单元格规则、各字段取值与挂钩写法）。要点：

**分档（08 章§2.3 判定规则，不靠人拍）**：这条知识能不能举出“做错了会怎样”的完整失败路径？能 → full 档（方法型／拆解型，七层）；不能，只是“规定如此” → lite 档（条文型，结论→依据→正误对照，200—600 字，落在 500—600 的不超过本批三分之一）。

**两种模式**：
- **M1（v7.1）**：技巧、教程、书籍——萃“怎么做”。
- **M2（v6.0 底层解码）**：优秀范文、领导讲话——萃“为什么这样写有效”，answer_type 用拆解型，多落 C5、C6、C3 模块写法；只用脱敏批次。

**首件**：本组选 1 篇最能代表主文种的，萃完先跑第④步 dry-run，**到此停下**，向 Jeffrey 报告：条目摘要（每条首问＋大类小类＋档＋字数）、dry-run 结果、拿不准的归类。确认口径后再做整组。

**整组写完自数**（不信自报，亲自数条数和字数分布）：
```
python3 -c "import sys,collections;sys.path.insert(0,'30_engine/tools');import kb_ingest;rows=kb_ingest.parse_table(open(sys.argv[1],encoding='utf-8').read());print(len(rows),'行',dict(collections.Counter(r['category_l1'] for r in rows)));[print(i,r['category_l1'],r['category_l2'],r['answer_type'],len(r['answer']),'字') for i,r in enumerate(rows,1)]" 30_engine/batches/B-20261003-01/raw_output.md
```
（把路径换成本批的 raw_output.md。）实产比预估少一截，先看是不是写到半截断了。

**回源核对**：每条答案里的数字、引语、案例，回原文行号区间逐一核对，核不上的删或改定性。

## 第④步 · dry-run（本 skill 的终点）

```
python3 30_engine/tools/kb_ingest.py --batch 30_engine/batches/B-YYYYMMDD-NN --dry-run
```
- 通过时只打印“dry-run 通过：N 条待入库（c?:…）”，不写库。
- 不过时写（覆盖）批次目录的 `check_report.md`，逐条回第③步修，不许改校验器或放宽规则（校验器只能有一份，`30_engine/tools/kb_validate.py`）。
- 同一批连续 3 次 dry-run 不过，停下报告卡在哪。

通过后在 plan.md 末尾追加**完成报告**：实产 vs 预估及偏差原因、放弃的知识点与理由、遗留归类争议、本批最差一条（强制差评，自评一次，抽检时还会再评）。然后交 gw-ingest 正式入库。
