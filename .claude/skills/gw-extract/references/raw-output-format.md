# raw_output.md 格式契约（kb_ingest 的解析口径）

> 口径来源：`30_engine/tools/kb_ingest.py`（解析）、`30_engine/tools/kb_validate.py`（校验）、`30_engine/tools/vocab.py`（受控词表与数量上下限）。三者与本文冲突时以代码为准，并回来改本文。
> 旧项目 legacy 的 gw-extract 规格是十列、旧路径，已过时，不要照抄。

## 1. 文件结构

```
---
batch_id: B-YYYYMMDD-NN
extract_method: v7.1
source_path: 10_source/raw_materials/…/某文件.md
---

| category_l1 | 问题 | 答案 | answer_type | tags | scenarios | question_keywords | category_l2 | doc_types | source_anchor | source_path | depth | enforce | w_layer | 挂钩 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 3 | 问法1？ / 问法2？ / 问法3？ | 核心观点：…<br>机理解释：…<br>… | 方法型 | 标签1；标签2；… | 【主要适用场景】…【典型使用者】…【触发时机】…【注意】… | 词1；词2；… | 主体展开 | 通用 | 汇编一-023 | 10_source/…/某文件.md | method | soft | W2；W3 | QA-C6-00008 |
```

- 头部 `batch_id`、`extract_method` 必填；`extract_method` 取 `v7.1`（M1）、`v6.0`（M2）、`m3`、`人工`。
- 头部 `source_path` 与行内 `source_path` 至少有一个；行内的覆盖头部。跨分册、跨文件的组必须逐行写。路径一律写**项目内相对路径**、正斜杠。
- **表头后 5 列文字必须完全是** `source_path | depth | enforce | w_layer | 挂钩`，顺序错了 kb_ingest 整表拒收。只有 10 列时视为旧格式（无挂钩字段）。

## 2. 单元格三条硬规则

1. 换行写 `<br>`，表内不能真换行。
2. 内容里的竖线写 `\|`。
3. 数组字段（tags、question_keywords、doc_types）用中文分号“；”分隔；w_layer、挂钩可用分号、逗号或空格分隔。

## 3. 字段取值（数字以 vocab.py 为准）

| 列 | 规则 |
|---|---|
| category_l1 | 1—6，须与 category_l2 属同一大类 |
| 问题 | 3—6 个问法，用“ / ”（两侧各一空格）分隔；方法型、拆解型至少 1 个反向问法（含踩坑、误区、错误、失败、禁忌，或“为什么…不”） |
| 答案 | 条文型 ≥150 字；方法型、拆解型 ≥500 字；任何档上限 2000 字。**不得含英文直引号**，中文用“”‘’（项目规定不用「」『』） |
| answer_type | 条文型（lite：结论／条文→依据→正误对照→易错点）；方法型、拆解型（full 七层：核心观点／机理解释／案例论证／反向踩坑预警／实操建议／边界与延伸／可复用清单） |
| tags | 5—12 个 |
| scenarios | 四段标记齐全：【主要适用场景】【典型使用者】【触发时机】【注意】 |
| question_keywords | 5—10 个，含口语说法与反向搜索词 |
| category_l2 | 04 章§4.2 受控词表，校验以 vocab.py `CATEGORY_L2` 为准 |
| doc_types | vocab.py `DOC_TYPES` 受控值，通用知识填“通用” |
| source_anchor | 章节或篇号，如“汇编一-023”“第 12 章·七步成文法” |
| depth | axiom／principle／method／technique／rule，可空 |
| enforce | hard／soft／advice，可空；默会类知识标 advice，不硬套规则（H3 部分成立） |
| w_layer | W1—W5 子集，可空 |
| 挂钩 | 按 depth 解读：axiom 填管辖大类号（3；C3）；technique 填所实现的 method id；method、principle 填所出自的上一级 id；rule 不挂钩，填了会报错 |

08 章 full 档原定 1200—2300 字，但入库校验上限是 2000 字，按 2000 写；超了拆成两条或精简。

## 4. 不在表里写、由 kb_ingest 自动生成的字段

id（按各大类独立续号）、answer_hash、batch_id、extract_method、quality_grade（一律 B）、quality_checked（false）、status（active）、created、updated。

## 5. 入库前自查（dry-run 只查得出格式问题，下面几项只能人查）

- 每条只讲一个知识点，问法问的确实是答案答的那件事。
- 答案里的数字、比例、引语回源核对过。
- 答案不含书名、作者、篇名、客户名、人名。
- 与已入库条目的关系在 plan.md 去重表里写清了。
