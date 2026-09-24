# 项目目录结构

> v2.0 ｜ 2026-09-14 ｜ 按 `90_design/公文链路设计/` 04–10 章的新架构重组。
> 旧结构（49 个散文件 + 21 个平铺目录）已归档至 `99_前期资料/`。

---

## 一、编号规则

目录编号按**数据流方向**排，不按重要性：

```
10 源  →  20 知识  →  30 引擎  →  40 测试  →  50 任务
                                                    90 设计（横贯，是全部依据）
                                                    99 前期（已退役）
```

数字留空档（10/20/30…）是为了后续插入不必重编号。

---

## 二、目录说明

### `10_source` · 语料真源

```
10_source/
    raw_materials/        3,055 份原始语料 / 3,349 万字（原 00_raw_materials）
    (待建) manifest/      切分账：篇名 / locator / 篇型 / 是否已萃
```

**纪律**：批次目录不复制原文，一律按 `locator`（文件+行区间）回源取。复制会产生查不出的不一致。

### `20_knowledge` · 知识库

```
20_knowledge/
    qa/          (待建) C1–C6 六大类 JSONL，QA 主库
    terms/       词典
        legacy/              旧词典（390 术语，覆盖率 58%，official_terms_v2 程序读不了）
        (待建) terms.jsonl   四层词典：T1 定义 / T2 搭配 / T3 分寸 / T4 辨析
    corpus/      语料制品
        legacy/              范文库 P3、段落库 v2、selected_articles
        industry_docs/       行业文档 242 篇（原 knowledge/）
        (待建) paragraphs.jsonl / articles.jsonl
    templates/
        legacy/              文种骨架 A2 系列（原 01_templates）
    rules/
        legacy/              rules_master 345 条 + 五本书方法论提炼（原 02_rules）
```

**`legacy/` 的含义**：**可查、可复用、但不是最终形态**。新库建成后按 07 章 v2 重构，届时 legacy 转入 99。

### `30_engine` · 引擎

```
30_engine/
    rag/
        legacy/       现有 ChromaDB 检索栈（⚠️ 依赖 tobacco_kb，待解耦换 LanceDB）
    tools/
        legacy_skills/    旧 skill 套件（skill_style/quality/framework + 公文写作体系 12 件）
        benchmarks/       检索基准
        (待建) qa_check.py / qa_merge.py / qa_tag.py …
    runs/         (待建) 批次配置 *.json —— 不放 scratchpad
    batches/      (待建) 批次产出 B-YYYYMMDD-NN/
```

**七个新 skill**（gongwen / gw-search / gw-draft / gw-review / gw-rag / gw-ingest / gw-audit）建在 `.claude/skills/`，不在这里——那是 Claude Code 的约定位置。

### `40_tests` · 测试

```
40_tests/
    legacy/       Dify 时代 E2E 框架（框架作废，18 个用例可迁移）
    cases/        (待建) 场景 34 条 + 节点 118 条
    golden/       (待建) 检索 golden set
    defects/      (待建) 缺陷注入池——跨层回退测试的关键资产
```

### `50_tasks` · 写作任务

```
50_tasks/
    _历史任务/                  4 个旧任务
    [日期]_[文种]_[主题]/
        素材/
        outline.md              W2 产物，含论点地图
        v1_初稿.md
        review_report.md        W5 产物，不生成不得呈报终稿
        终稿.md
```

### `90_design` · 设计方案 ★

```
90_design/公文链路设计/
    04_知识萃取与知识库.md          C1–C6、QA schema、门禁
    05_写作流程.md                  S1–S5、三确认点、20 条门禁
    06_Skills体系.md                7 个 skill
    07_知识分层与词典架构_v2.md     depth/enforce/词典四层/脱敏
    08_kb-rag迁移与实施计划.md      QA 引擎、双档规格
    09_写作体系总体架构.md          A 层公理、W1–W5、八场景
    10_写作体系作业规格_IPO.md      28 节点 IPO + 三级测试
    10_知识库建设作业计划.md        建库作业
    ── 已作废 ──
    07_L1-L5五层知识架构设计.md
    09_写作体系架构.md
```

**唯一依据**。动手前先读，不要凭记忆办事。

### `99_前期资料` · 已退役

五类归档，索引见 `99_前期资料/README.md`。**不要复用其中脚本，不要当现状看。**

---

## 三、设计→目录 对照

| 设计概念 | 落在哪 | 状态 |
|---|---|---|
| A 层 6 公理 | `20_knowledge/qa/c6_*.jsonl`（depth=axiom） | 待建 |
| C1–C6 QA 库 | `20_knowledge/qa/` | 待建 |
| 词典四层 | `20_knowledge/terms/terms.jsonl` | 待建 |
| 段落库 / 范文库 | `20_knowledge/corpus/` | 待建（legacy 可用） |
| 7 个 skill | `.claude/skills/` | 待建 |
| gw-rag 脚本 | `30_engine/tools/` | 待建（从 kb-rag copy） |
| 三级测试 | `40_tests/` | 待建 |
| W1–W5 产物 | `50_tasks/<任务>/` | 规格已定 |

---

## 四、根目录只留四样

```
CLAUDE.md                        项目指令
CLAUDE_旧版_v1.1_20260914.md     上一版备份
PROJECT_STRUCTURE.md             本文件
.env.template / .gitignore
```

**根目录不再堆散文件。** 新产物一律进编号目录。

---

*结构变更走 git mv，全程可追溯。*
