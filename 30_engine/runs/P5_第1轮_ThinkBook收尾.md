# P5 第 1 轮 · ThinkBook 收尾清单（SOP 第⑥⑦⑨⑩步）

> 2026-10-01 在 dell-7050 上写。7050 上的会话在发起本清单后结束，**7050 此后不再写本项目，直到 ThinkBook 交回执行记录**。
> 7050 已完成：三批萃取入库（共 83 条，库由 40 条增至 123 条）、kb_validate 全过、audit 0E/0W、单测 223 过。
> 7050 做不了、留给本清单的：向量近重复判重（第⑥步后半）、导入 Kb-RAG 与建索引及冒烟（第⑨步）、git 提交（第⑩步）、专家抽检单（第⑦步，抽检本身由 Jeffrey 做）。

## 怎么启动

在 ThinkBook 上（PowerShell）：
```
cd D:\projects\Public_Writing_KB
claude --add-dir D:\projects\Kb-RAG "读 30_engine/runs/P5_第1轮_ThinkBook收尾.md，按第 0–6 步逐步执行，每步打勾，结果写进文末“执行记录”。"
```

## 执行边界（先读）

**先读**：本项目 `CLAUDE.md`；`30_engine/runs/P3.7_检索接入_ThinkBook操作清单.md` 的“执行记录”（上次 ThinkBook 会话踩过的坑，下面已吸收）；Kb-RAG 的 `CLAUDE.md`。

**解释器**：Kb-RAG 的命令一律用 `D:/ai-runtime/venv-cuda/Scripts/python.exe`（2026-10-02 由 tobacco_kb 迁出，Kb-RAG ADR-030）（下文记作 `$KPY`）。系统 `py` 在会话里会被拒，且没有 torch/lancedb。路径一律写正斜杠。

**允许改的文件**：
- 本项目：新增 `30_engine/tools/kb_dedup_vec.py` 及其测试；本清单；`30_engine/batches/B-20260929-01/plan.md`、`B-20260929-02/plan.md`、`B-20261001-01/plan.md` 的“完成报告”下追加判重结果；`CLAUDE.md` 的检索栈、测试两行
- Kb-RAG：只重跑导入与建索引（生成物 `knowledge/kbs/public_writing_qa/qa.jsonl` 与 `index/` 下对应目录），**不改代码与注册表**
- **`20_knowledge/qa/*.jsonl` 只读**：判重发现问题只记录，不改条目、不删条目、不改 `quality_checked`

**必须停下报告**：
- 第 0 步：7050 上有会话在写本项目，或出现 `*.sync-conflict-*`，或库条数不是 123
- 第 2 步：单测、kb_validate、kb_audit 任一不过
- 第 4 步：F6-01～04 有未命中（不要为过验收改 QA 文本）
- 同一步失败 3 次

## 0. 前置核对

- [x] 本项目、Kb-RAG 两个目录最近一小时无他人改动；全盘无 `*.sync-conflict-*`
- [x] Syncthing 已同步完：`20_knowledge/qa/` 下 6 个 jsonl（**新增了 `c2_格式规范.jsonl`**），合计 **123 行**；按大类 c1:19 c2:5 c3:33 c4:8 c5:29 c6:29
- [x] 三个批次目录都在：`30_engine/batches/B-20260929-01/`、`B-20260929-02/`、`B-20261001-01/`，各有 plan.md、raw_output.md
- [x] 7050 期间的文件改名已同步到位：`90_design/公文链路设计/07_知识分层与词典架构.md` 存在、`07_…_v2.md` 不存在；根目录 `CLAUDE_旧版_v1.1_20260914.md` 已移到 `99_前期资料/04_旧文档报告/`

## 1. 本项目在 Windows 上的回归测试

7050 上改了公共工具，Windows 上必须再跑一遍，不能只信 7050 的结果：
- `common.py`：项目根改为 `parents[2]`（原为上两级，不设 `KBRAG_ROOT` 时指向空目录）
- `kb_ingest.py`：支持 15 列表（逐行 source_path + depth/enforce/w_layer/挂钩）
- `kb_audit.py`：命名检查豁免 `10_source/`、`99_前期资料/`、`legacy/`；`PROJECT_STRUCTURE.md` 入根目录白名单
- `draft_lint.py`：新增 R7 逐段审表硬闸
- 34 条老记录的 source_path 已由 `D:\…` 改为项目内相对路径

命令（**不设 `KBRAG_ROOT`**，验证根目录修复在 Windows 上也成立）：
```
python 30_engine/tools/kb_validate.py
python 30_engine/tools/kb_audit.py
python -m pytest -q 40_tests/kb_ingest
```
再把 `30_engine/batches/B-20261001-01/raw_output.md` 复制到系统临时目录下一个新建文件夹，对**副本**跑：
```
python 30_engine/tools/kb_ingest.py --batch <临时文件夹> --dry-run
```
（不要对原批次目录跑：失败时会把原目录里“通过”的 check_report.md 覆盖成“未通过”。）
- [x] kb_validate “全部记录合格”；kb_audit 0 error
- [x] 单测：7050 为 223 passed。Windows 上若有文件因缺 jieba 收集失败（上次 t2_collocation、term_candidates 两个），记下数量，不算本次失败；**其余必须全过**
- [x] 最后一条 dry-run 应**失败**并报“answer_hash 与库内已有记录重复”——证明批次已入库、判重在 Windows 上也生效（这是预期，不要“修”）

## 2. 向量近重复判重（第⑥步后半）

Kb-RAG 没有现成判重工具。新建 `30_engine/tools/kb_dedup_vec.py`：
- 读 `20_knowledge/qa/c*.jsonl` 全部 active 记录；用 Kb-RAG 的嵌入模型（与建索引同一个 bge-m3，从 Kb-RAG 的 `tools/common.py` 或 `kb_index.py` 里找它的嵌入函数复用，**不另装依赖、不另选模型**）对每条的 answer 编码
- 两两算余弦相似度，输出：①相似度 >0.92 的所有对；②相似度最高的 20 对（无论是否过线）；③指定对的分数（参数传入）
- 只读，不写任何 jsonl；输出打印到屏幕并可 `--json`
- 测试：至少 3 条——同一条与自身为 1.0；两条无关条目（如 QA-C2-00004 成文日期 vs QA-C6-00016 立意）明显低于 0.92；`--pairs` 参数能返回指定对

运行（用 `$KPY`，因为要用 Kb-RAG 的模型）：
```
$KPY 30_engine/tools/kb_dedup_vec.py --pairs QA-C6-00018,QA-C6-00014 QA-C3-00028,QA-C3-00026 QA-C5-00013,QA-C1-00007 QA-C4-00003,QA-C5-00009 QA-C5-00027,QA-C6-00019 QA-C5-00024,QA-C4-00003 QA-C5-00021,QA-C6-00008 QA-C1-00019,QA-C1-00014
```
上面 8 对是三批 plan.md 里点名要重点看的。
- [x] >0.92 的对逐对写进执行记录，附两条的首个问法；**只记录，由 Jeffrey 决定合并、保留或废弃**
- [x] 结果按批次追加到对应 plan.md 完成报告下“向量判重”小节

## 3. 导入 + 建索引（第⑨步前半）

```
cd D:/projects/Kb-RAG
$KPY tools/kb_import.py public_writing_qa
$KPY tools/kb_index.py public_writing_qa
```
- [x] 导入 123 条（上次 40 条），索引行数一致
- [x] 其他库不动：`$KPY tools/kb_import.py --all --dry-run --json`，除 public_writing_qa 外各库 records 与导入前一致

## 4. 检索验收（第⑨步后半）

**① F6 回归**（新增 83 条可能把原命中挤下去）：
```
$KPY D:/projects/Public_Writing_KB/40_tests/cases/run_f6_kbrag.py D:/projects/Kb-RAG
```
- [x] F6-01～04 仍全部 Top5 命中
- [x] F6-05～08（已知缺口）记录新的 Top1：本轮新增了 C4-00004“十个不写”、C4-00002 问题措辞等，看 F6-05“高度重视能不能用”是否有了相关命中

**② 冒烟 10 条**（每条一个新条目，Top5 命中即过）：
```
$KPY D:/projects/Kb-RAG/tools/search.py --kb public_writing_qa --top 5 --q "<问题>"
```

| # | 问题 | 应命中 |
|---|---|---|
| 1 | 领导离任讲话怎么写 | QA-C5-00016 |
| 2 | 工作会议表态发言怎么写 | QA-C5-00017 |
| 3 | 汇报材料的重点怎么定 | QA-C5-00007 |
| 4 | 请示和报告有什么区别 | QA-C1-00016 |
| 5 | 成文日期怎么写 | QA-C2-00004 |
| 6 | 百分点和百分比有什么区别 | QA-C4-00006 |
| 7 | 工作总结怎么改成汇报材料 | QA-C1-00007 |
| 8 | 写材料前怎样立意 | QA-C6-00016 |
| 9 | 文件中的指导思想怎么写 | QA-C3-00018 |
| 10 | 讲话稿怎么开场 | QA-C5-00020 |

- [x] 记录每条 Top5 id 与分数；≥8/10 命中算过，未命中的写明 Top1 是什么，不改条目

**③ tags 过滤**：
- [x] `--tags gw:C2` 只返回 C2 条目；`--tags gw:depth=rule` 只返回 rule 级条目（本轮新增的 8 条条文型都是 rule）

## 5. 专家抽检单（第⑦步，只出单不打分）

按批次各随机抽 max(5 条, 10%)：B-20260929-01 抽 5、B-20260929-02 抽 5、B-20261001-01 抽 5。**每批必须包含 plan.md 里点名的“最差一条”**（QA-C5-00011、QA-C6-00029、QA-C5-00029）。
- [x] 把 15 个 id 与首个问法列进执行记录，交 Jeffrey 在 kb_editor 抽检；本会话不改 `quality_grade`、`quality_checked`

## 6. 提交（第⑩步）

**上次的坑**：本项目有大量文件长期未提交，其中有 7050 其他会话的工作（如脱敏第 8 轮）。本次**只提交下列与 P5 第 1 轮直接相关的文件，分两个提交**，其余未提交文件列进执行记录，不动不提交。

提交 A：工具与规则（先提交）
```
30_engine/tools/common.py  kb_ingest.py  kb_audit.py  draft_lint.py  kb_dedup_vec.py
30_engine/tools/migrations/20260929_p5_relative_source_path.py
40_tests/kb_ingest/test_common.py  test_ingest.py  test_audit.py  test_draft_lint.py  （及 kb_dedup_vec 的测试）
.claude/skills/gw-review/SKILL.md  templates/review_report.md  references/quality-checklist.md
90_design/公文链路设计/07_知识分层与词典架构.md（及删除的 07_…_v2.md）  08、09、10 章
PROJECT_STRUCTURE.md  99_前期资料/README.md  99_前期资料/04_旧文档报告/CLAUDE_旧版_v1.1_20260914.md（及根目录原文件的删除）
50_tasks/2026-09-29_介绍_河南中烟流程体系/逐段审表_交接说明.md
```
提交 B：数据（jsonl 与批次同一个提交，SOP 第⑩步要求）
```
20_knowledge/qa/  （6 个 jsonl + _manifest.yaml）
30_engine/batches/B-20260929-01/  B-20260929-02/  B-20261001-01/
30_engine/runs/P5_三源萃取分组方案.md  P5_技巧汇编篇目分组.tsv  P5_第1轮_启动指令.md  本清单
10_source/manifest/技巧汇编_篇目定位.tsv  30_engine/tools/source_locate.py
CLAUDE.md
```
- [x] 提交前 `git diff --stat` 核对：提交 B 中 jsonl 的新增行数合计 83
- [x] Kb-RAG 单独提交派生文件 `knowledge/kbs/public_writing_qa/qa.jsonl`（索引按惯例不进 git）
- [x] 两个提交号写进执行记录

## 7. 收尾

- [x] `CLAUDE.md` §〇 检索栈一行：“已索引 40 条（P5 新增条目尚未导入…）”改为已索引 123 条及日期；测试一行补上 Windows 回归结果
- [x] 执行记录写完，交回 7050

## 执行记录

（ThinkBook 会话填写：各步 ✅/❌、单测数、>0.92 对、F6 与冒烟 Top5、抽检 15 条、两个仓库提交号、未提交文件清单、遇到的问题）

**2026-10-01 · ThinkBook（经 SSH）· Claude Code 会话（Opus 5.5）· 中途交接**

> SSH 会话在第 4 步中途关闭，Jeffrey 换 ThinkBook 本地窗口续做。**接续从第 4 步②开始**；第 0–3 步与第 4 步①已完成，不用重跑。

| 步 | 结果 | 说明 |
|---|---|---|
| 0 前置 | ✅ | 一小时内改动只有 7050 收尾落盘（最晚 21:10 本清单），Kb-RAG 无改动；无 `*.sync-conflict-*`；6 个 jsonl 共 123 行，c1:19 c2:5 c3:33 c4:8 c5:29 c6:29；三批次目录齐；07 章改名、旧版 CLAUDE 移位已到位 |
| 1 Windows 回归 | ✅ | 不设 `KBRAG_ROOT`。kb_validate“全部记录合格”；kb_audit 0 error / 0 warning；单测 **212 passed**，另 t2_collocation、term_candidates 两个文件（11 条）缺 jieba 未收集，合计 223 与 7050 一致；副本 dry-run 按预期失败，19 条全部“answer_hash 与库内已有记录重复”（= G02 批 19 条） |
| 2 向量判重 | ✅ | 新建 `30_engine/tools/kb_dedup_vec.py` + `40_tests/kb_ingest/test_kb_dedup_vec.py`（5 条，含真模型用例：自身 1.0、C2-00004×C6-00016 <0.92，系统 Python 下 5 passed）。123 条 7,503 对，**无一对 >0.92**，最高 0.8584；全库中位数 0.655、P99 0.792。三份 plan.md 已追加“向量判重”小节 |
| 3 导入 + 建索引 | ✅ | 导入 123 条 / 565 问法（上次 40 条）；索引 123 行 / 1024 维 / icu；其余库 dry-run 前后逐库一致（60 库 16,205 条，无差异） |
| 4① F6 回归 | ✅ | F6-01 第 2 位、F6-02/03/04 第 1 位，应命中 4/4。缺口类 Top1：F6-05 C6-00010、F6-06 C6-00010、F6-07 C5-00001、F6-08 C3-00008——**与上轮相同，新增的 C4-00004“十个不写”、C4-00002 未顶上 F6-05 的 Top1**；Top5 全表与分数未采到，见下 |
| 4② 冒烟 10 条 | ✅ | **10/10 全部 Top1 命中**（门槛 ≥8/10），明细见下 |
| 4③ tags 过滤 | ✅ | `gw:C2` 返回 5 条全为 C2（= 库内 C2 全部 5 条）；`gw:depth=rule` 返回 10 条全为 rule，0 条混入。但库内 rule 共 14 条，漏 C1-00004/C1-00006/C1-00016/C2-00003——查 `search.py:651`，标签是**召回后过滤**（本次候选 58 → 筛后 10），不是索引预过滤。判读见下 |
| 5 抽检单 | ✅ | 15 条已出，见下；未改 `quality_grade`/`quality_checked` |
| 6 提交 | ✅ | 本项目提交 A `7477d83`、提交 B 与 Kb-RAG 提交号见下；**只提交本地，未 push** |
| 7 收尾 | ✅ | CLAUDE.md §〇 检索栈、测试两行已改 |

**向量判重 >0.92 的对**：无。最高 20 对与 8 个点名对的分数见三份 plan.md“向量判重”小节；点名对：C6-00018×C6-00014 0.8258、C3-00028×C3-00026 0.7523、C5-00013×C1-00007 0.6606、C4-00003×C5-00009 0.8457、C5-00027×C6-00019 0.7275、C5-00024×C4-00003 0.8326、C5-00021×C6-00008 0.6638、C1-00019×C1-00014 0.8359。
判读：bge-m3 对整段答案编码，分数挤在 0.43–0.86，0.92 这条线在本库上基本不会触发。要真抓换词复述，阈值应按分布定（例如 >P99 即 0.79 以上逐对人看，共 22+21+9 对量级），这条留 Jeffrey 定。

**接续要点（本地窗口）**
- 解释器：Kb-RAG 命令用 `D:/ai-runtime/venv-cuda/Scripts/python.exe`；本项目单测用 `C:/Users/febin/AppData/Local/Python/bin/python`（WindowsApps 里的 `python` 是商店别名，执行被拒）
- 4②③ 可直接跑 `$KPY tools/search.py --kb public_writing_qa --top 5 --q "…" --json`（cwd = Kb-RAG），JSON 的 `results[].id/score/tags` 即所需字段
- 5、6、7 按清单原文执行；提交 A 记得带上 `kb_dedup_vec.py` 与 `test_kb_dedup_vec.py`，提交 B 带上三份 plan.md 的改动

**2026-10-01 · ThinkBook 本地窗口 · Claude Code 会话（Opus 5.5）· 续做 4②–7**

**4② 冒烟明细**（`--top 5 --json`，分数为 rerank 后 score）

| # | 问题 | 应命中 | 名次 | Top5 |
|---|---|---|---|---|
| 1 | 领导离任讲话怎么写 | C5-00016 | 1 | C5-00016 1.0000；C5-00028 0.6841；C5-00015 0.5571；C5-00020 0.3860；C5-00019 0.3423 |
| 2 | 工作会议表态发言怎么写 | C5-00017 | 1 | C5-00017 1.0000；C5-00015 0.7104；C5-00019 0.7080；C5-00020 0.6489；C5-00028 0.4802 |
| 3 | 汇报材料的重点怎么定 | C5-00007 | 1 | C5-00007 1.0000；C6-00020 0.8267；C6-00016 0.4189；C5-00008 0.3333；C3-00001 0.2859 |
| 4 | 请示和报告有什么区别 | C1-00016 | 1 | C1-00016 1.0000；C1-00018 0.4741；C2-00001 0.1339；C1-00001 0.1256；C1-00008 0.1078 |
| 5 | 成文日期怎么写 | C2-00004 | 1 | C2-00004 0.9995；C3-00025 0.0242；C2-00002 0.0217；C4-00006 0.0124；C6-00026 0.0095 |
| 6 | 百分点和百分比有什么区别 | C4-00006 | 1 | C4-00006 0.9839；C1-00008 0.0042；C6-00010 0.0025；C6-00025 0.0018；C3-00019 0.0017 |
| 7 | 工作总结怎么改成汇报材料 | C1-00007 | 1 | C1-00007 0.9995；C5-00001 0.9824；C5-00008 0.2328；C1-00009 0.2163；C3-00016 0.2142 |
| 8 | 写材料前怎样立意 | C6-00016 | 1 | C6-00016 0.9995；C6-00017 0.9502；C6-00028 0.8472；C1-00014 0.3013；C6-00006 0.2766 |
| 9 | 文件中的指导思想怎么写 | C3-00018 | 1 | C3-00018 1.0000；C1-00011 0.8452；C3-00017 0.4368；C3-00019 0.3315；C1-00012 0.2444 |
| 10 | 讲话稿怎么开场 | C5-00020 | 1 | C5-00020 0.9995；C5-00021 0.8086；C5-00027 0.6768；C5-00023 0.5957；C5-00018 0.5469 |

判读：10 个问题基本就是条目自带的首个问法，rerank 分接近 1.0 是字面对上了。这一步证明 83 条已进索引、能被召回，**不证明换个说法也能找到**——泛化能力仍以 F6 为准。值得 Jeffrey 看的两处高分并列：#7 C1-00007（总结改汇报）与 C5-00001 0.98 几乎同分；#8 C6-00016/C6-00017 0.95。两对向量判重分数都不高，内容是否重叠由抽检时一并判断。

**4③ tags 过滤判读**：清单判据“只返回该标签条目”成立。召回后过滤的副作用是：要“列出某标签全部条目”不能靠 `--tags`，查询词偏了会漏（rule 级本次漏 4/14）。gw-draft 按标签取规则时要知道这一点；Kb-RAG 改预过滤属 Kb-RAG 代码改动，不在本清单权限内，只记录。

**5 专家抽检单**（每批 = 点名最差 1 条 + `random.Random(20261001)` 从其余条目抽 4 条，可复现；全部 B 级、`quality_checked=false`）

| 批次 | id | 首个问法 |
|---|---|---|
| B-20260929-01 | QA-C5-00011（最差） | 民主生活会对照检查材料怎么写？ |
| B-20260929-01 | QA-C1-00014 | 经验材料怎么写？ |
| B-20260929-01 | QA-C3-00017 | 文件结构常见的毛病有哪些？ |
| B-20260929-01 | QA-C3-00018 | 文件中的指导思想怎么写？ |
| B-20260929-01 | QA-C6-00014 | 起草文件时怎样准确表达领导决策？ |
| B-20260929-02 | QA-C6-00029（最差） | 起草人的个人偏好会怎样影响公文？ |
| B-20260929-02 | QA-C3-00028 | 公文大标题怎样才能和内容对得上？ |
| B-20260929-02 | QA-C3-00030 | 一篇材料分几大部分合适？ |
| B-20260929-02 | QA-C6-00020 | 一篇材料的主题怎么确定？ |
| B-20260929-02 | QA-C6-00028 | 每年都要写的材料怎样写出新意？ |
| B-20261001-01 | QA-C5-00029（最差） | 一篇好的领导讲话稿有什么标准？ |
| B-20261001-01 | QA-C1-00017 | 领导讲话稿有哪些类型？ |
| B-20261001-01 | QA-C1-00019 | 先进事迹材料怎么写？ |
| B-20261001-01 | QA-C5-00015 | 部署工作的领导讲话稿怎么写？ |
| B-20261001-01 | QA-C5-00017 | 工作会议上的表态发言怎么写？ |

**6 提交**
- 提交 A `7477d83`：22 个文件（工具、测试、gw-review 三件、07 章改名、08/09/10 章、PROJECT_STRUCTURE、99_前期资料 README 与旧版 CLAUDE 移位、逐段审表交接说明）
- 提交 B 前核对：jsonl `git diff --numstat` 新增 117 行、删除 34 行（34 条老记录 source_path 改相对路径的替换行），另 c2 新文件 5 行计入 117；净增 **83** ✓
- 提交 B、Kb-RAG 提交号：见本节末行
- **未 push**：远端是 GitHub（`Jeffrey-XU-Cons/Public_Writing_KB2`），仓库可见性本会话没查到（`gh` 网络 EOF）。提交 A 里的逐段审表交接说明含客户名与经营数字，push 前请 Jeffrey 确认仓库为私有

**未提交、未动的文件**（非 P5 第 1 轮，或清单未列）：
- `.claude/skills/gongwen/SKILL.md`、`gw-draft/SKILL.md`、`gw-draft/references/wenzhong/文种_01_汇报材料.md`、`gw-draft/templates/outline.md`、未跟踪 `gw-review/references/semantic-examples.md`
- `30_engine/tools/deidentify.py`、未跟踪 `30_engine/tools/deid_scan.py`、`40_tests/kb_ingest/test_deidentify.py`（脱敏第 8 轮）
- `40_tests/golden/make_draft_lint_snapshot.py`、`40_tests/kb_ingest/test_draft_lint_golden.py`
- `90_design/公文链路设计/05_写作流程.md`、`11_项目总体规划.md`
- 未跟踪 `50_tasks/2026-09-28_汇报_成熟度评价体系专题评审/`、`50_tasks/2026-09-29_介绍_河南中烟流程体系/` 下除交接说明外的文件

**遇到的问题 / 待 Jeffrey 定**
1. 向量判重 0.92 阈值在本库不触发（见上段），阈值要不要改按分布定。
2. `--tags` 是召回后过滤（见 4③）。
3. CLAUDE.md §〇 末段“重跑前须在 ThinkBook 把新条目导入 Kb-RAG”与 QA 库一行“P5 新条目未做专家抽检和向量判重”已过时，但不在本清单允许改的两行内，留给 7050 改。
4. Kb-RAG 提交时其 hook 提示“动了 knowledge/ 但未更新 STATUS.md”。STATUS.md 不在本清单允许改的范围内，未补；要不要在 Kb-RAG STATUS 记一笔，由 Jeffrey 定。

**提交号**：本项目提交 A `7477d83`、提交 B `10b74ec`（本行与第 4 条另以一个小提交补入）；Kb-RAG `63dc70d`。均未 push。

---

## 补充任务 · 2026-10-02（7050 写，ThinkBook 执行）

Jeffrey 2026-10-02 定：向量判重阈值不用固定 0.92，改为全库分布的 **P99**，过线对逐对出清单交人判定。7050 已给 `kb_dedup_vec.py` 加了 `--percentile` 和 `--out`（7050 单测 230 passed、1 skipped，跳过的是真模型用例）。7050 没有 torch，实际出分只能在这边跑。

$KPY 取 Kb-RAG `CLAUDE.md`“运行环境”里当时规定的解释器。tobacco_kb 规划弃用（Kb-RAG ADR-024⑤），若模型与 venv 已迁出，按新路径；本清单不再写死 tobacco_kb 路径。

```
cd D:/projects/Public_Writing_KB
$KPY 30_engine/tools/kb_dedup_vec.py --percentile 99 --out 30_engine/runs/P5_第1轮_向量判重P99清单.md
$KPY -m pytest -q 40_tests/kb_ingest/test_kb_dedup_vec.py
```
- [x] 清单生成；P99 应接近上次的 0.792，过线约 76 对（7,503 × 1%）。数字明显不符就停下报告
- [x] 真模型用例在 `$KPY` 下通过（共 8 条）
- [x] 判定列、理由列留空，不改任何 jsonl；在本节下写一行结果（P99 值、对数、同小类对数）
- [x] 不提交，等 Jeffrey 填完判定一起处理（2026-10-03：Jeffrey 授权 Claude 判定，已处置并提交）

**结果（2026-10-03 ThinkBook，Kb-RAG 会话执行）**：解释器 `D:/ai-runtime/venv-cuda/Scripts/python.exe`（torch 2.11.0+cu128，tobacco_kb 迁出后的新环境，Kb-RAG ADR-030）。active 123 条、7,503 对；中位数 0.6552、P90 0.7356、**P99 0.7917**、最高 0.8585；过线 **76 对**，其中同小类 **25 对**；清单 `30_engine/runs/P5_第1轮_向量判重P99清单.md`，判定列、理由列留空待 Jeffrey 填。`test_kb_dedup_vec.py` 8 passed（15.6s）。未提交。

---

## 收尾决定与执行 · 2026-10-03（ThinkBook，Claude Code 会话；Jeffrey：“向量判重的你来合并……ThinkBook 收尾你决定”）

| 项 | 决定 | 执行结果 |
|---|---|---|
| 向量判重 P99 76 对 | 判据：两条回答的是不是同一个问题。合并 2 对（QA-C6-00001→QA-C3-00001，QA-C5-00002→QA-C5-00001），改问法 1 对，其余保留并写明边界 | 迁移 `20261003_p5_dedup_merge.py`；被并 2 条 deprecated；顺带全库 27 条「」统一为弯引号。逐对理由见 P99 清单 |
| 第⑤步专家抽检 15 条 | Claude 代检（记明不是专家本人检），并扩到三批 83 条全部答案的数字回源核对 | 12 条合格、3 条修正后合格（编造比例 1、例子写成规则 1、一条两点 1），迁移 `20261003_p5_spotcheck_fix.py`；三批 quality_checked=true。详见三份 plan.md“第⑦步抽检” |
| 问题 1 阈值 | 已由 Jeffrey 10-02 定为 P99，本轮执行完毕 | — |
| 问题 2 `--tags` 召回后过滤 | 不改 Kb-RAG：按标签取“全部条目”的需求目前没有，gw-draft“检索”节已写明这一局限；真出现需求时在 Kb-RAG 立 ADR | 只记录 |
| 问题 3 CLAUDE.md 过时两处 | 已在 10-03 前由 7050 改掉；本轮再按新状态更新 QA 库、检索栈两行 | 见 CLAUDE.md §〇 |
| 问题 4 Kb-RAG STATUS.md | 记：本库派生文件变动应在 STATUS 留一行，便于 Kb-RAG 侧知道数据来源变化 | Kb-RAG STATUS.md 补一行并与派生 qa.jsonl 同一提交 |

**重新导入与验收**：active 121 条 / 560 问法；索引 121 行；F6 应命中 4/4（F6-02、F6-03 的期望 id 随合并改为 QA-C5-00001、QA-C6-00008，F6-03 由第 2 位升为第 1 位）；冒烟 10/10 Top1；合并后的两条用新问法查（“工作总结写成流水账怎么办”“为什么材料要结论先行”“行动成果对照表怎么用”）均 Top1 或 Top2 命中。

**单测**：本会话前段 229 passed；后段 `test_skills.py` 两条起子进程的用例报 `WinError 6 句柄无效`，把改动全部 stash 后在 HEAD 上同样失败，判为本机会话环境问题，不是代码回归。同日稍后连续复跑 4 次 229 全过，确认是间歇性的。

**遗留**：kb_audit 有 18 个命名 error，全在 `20_knowledge/corpus/tobacco_kb/`（tobacco_kb 迁入时带的 `_v3` 文件名），使 `kb_mark_checked` 末尾 audit 报错退出（标记本身已写入）。改名可能牵动引用这些语料的脚本或配置（本会话未查全），没动，待 Jeffrey 定。
