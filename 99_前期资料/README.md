# 99_前期资料

> 2026-09-14 整理。原名 `99_archive_废弃内容库`。
> 存放**与当前架构无关的前期资料**。这些东西不是垃圾——它们是项目走到今天的过程产物，
> 但**不再是活资产**：新架构（`07_design_公文链路设计/` 04–10 章）不依赖其中任何一项。

---

## 为什么归档

项目经历过一次**架构换代**：

```
旧：Dify 工作流 + 六智能体 + HTTP 部署 + 一次性建库脚本
新：本地 skill 体系（gongwen/gw-draft/gw-review/gw-rag…）
    + A 层公理 / W1–W5 五层 / C1–C6 六大类
    + kb-rag QA 引擎 + 本地检索栈
```

两套东西的**概念零重叠**——旧 CLAUDE.md 里 `gw-rag`、`depth`、`w_layer`、`门禁`、`公理` 的出现次数全是 0。
继续留在根目录只会让人误引用，所以整体归档。

---

## 目录说明

| 目录 | 内容 | 为什么不再用 |
|---|---|---|
| `01_旧版归档` | 旧版词典 `official_terms.yaml`、段落库/金句库 (P4)、范文索引 JSON、清洗清单 | 已被 `03_dictionary/official_terms_v2.yaml`、`04_corpus/段落库_v2.yaml` 取代；P4 金句库已退役 |
| `02_Dify部署` | Dify 部署全套：`deployment/`、`code/`（6 个 agent 脚本）、`prompts/`（6 个 agent 提示词）、docker-compose、nginx、DEPLOY 系列文档、`CLAUDE_旧版_Dify.md` | **架构换代**。新方案不走 Dify，改本地 skill |
| `03_建库脚本` | 21 个一次性建库脚本（prepare_/extract_/p3_/p4_/audit_ 等）、`scripts/`、`__pycache__` | 已跑完，产物就是 `01_templates`～`04_corpus`。新建库走 `10_知识库建设作业计划.md` |
| `04_旧文档报告` | 旧 README、PROJECT_STRUCTURE、旧架构设计 v2、各类进度/审计/清洗报告、`docs/` | 描述的是旧架构与旧进度，**与现状不符，误导性强** |
| `05_旧元数据` | `05_metadata/`、`data_prep/`（含 Dify 上传件）、`_backup_清洗前_2026-05-22/` | 旧统计与旧管线中间产物 |

---

## 什么情况下会用到这里

1. **查历史**：某个数据当初是怎么算出来的 → `03_建库脚本`
2. **追溯产物来源**：`04_corpus` 里某文件谁生成的 → `03_建库脚本` + `04_旧文档报告`
3. **旧词典比对**：新词典重构时想看旧版怎么组织 → `01_旧版归档/official_terms.yaml`

**不要**：直接复用这里的脚本、把这里的文档当现状、按 `02_Dify部署` 去部署。

---

## 保留在根目录的活资产（对照）

```
00_raw_materials/   原始语料 3,055 份（QA 与段落库的来源）
01_templates/       文种骨架
02_rules/           规则总表 + 五本书方法论提炼
03_dictionary/      词典（待按 07 章重构成四层）
04_corpus/          范文库 + 段落库 v2
06_testing/         测试（框架待重写，用例可迁移）
07_design_公文链路设计/  ★ 设计方案，唯一依据
benchmarks/ rag/    检索栈（待解耦 tobacco_kb）
knowledge/ skills/  行业文档 + 旧 skill（待改造）
tasks/              任务目录
```

---

*归档不删除。git 全程可追溯，需要时 `git log --follow` 查得到。*
