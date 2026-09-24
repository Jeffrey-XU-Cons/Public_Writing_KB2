---
name: gw-extract
description: 公文知识萃取。把公文写作素材按 v7.1 分档标准萃取成 QA 批次（raw_output.md 十列表，首列 category_l1 每条一大类），供 kb_ingest.py 入库自动路由到六大类；优秀范文/领导讲话另走 v6.0 底层解码模式拆「为什么这样写有效」。触发词：萃取入公文库、公文知识萃取、拆解这篇范文入库、萃取这篇文章、做一批公文QA、整本书萃取入库。仅限公文写作域素材；通用书籍萃取用全局 book2qa。
---

# gw-extract · 公文知识萃取

产出物是**批次**，不是散条：一个批次 = `batches\B-YYYYMMDD-NN\` 下的 `plan.md`（预估报告）+ `raw_output.md`（九列 MD 表）。入库由 `python tools/kb_ingest.py --batch <批次目录>` 完成（内嵌校验+审计，不过则整批拒收）——本 skill 不直接写 `knowledge\`。

## 铁律（违反即停）

1. **首件铁律**：每开一本新书/新子类，第一批只做 1 个部分（约 1 章/1 场景）、交 Jeffrey 抽检确认口径后才准批量
2. **真实性红线**（v7.1）：不编数据、不编案例；原文没有数字就用定性描述；案例须可溯源到素材原文
3. **单批 30–50 条封顶**；**一条一主类**（每条填 category_l1，跨类靠 tags 不靠重复入库）；**一批可跨大类**（ADR-016，kb_ingest 按 category_l1 自动路由到六大类文件）
4. **整本书拆批**：书太大必须拆——按书自身结构（篇/部分/章/场景）一批一部分，先 1 部分走通再批量其余
5. 旧项目 `D:\projects\Public_Writing_KB` **只读**；Office/PDF 素材先用全局 `to-md` 转换，严禁自写转换

## 流程

1. **登记**：在 `source\manifest.yaml` 更新素材状态与批次号；建 `batches\B-YYYYMMDD-NN\`
2. **预估报告**（v7.1 第0步，宁低勿高）→ `plan.md`：素材字数/类型、目标大类与小类、预估条数、answer_type 分布预判
3. **萃取**：通读素材 → 识别可独立成 QA 的知识点 → 按 [references/qa-schema.md](references/qa-schema.md) 的分档规格逐条产出：
   - 条文型（默认档）：4 段「条文+出处+正误对照+易错点」≥150 字
   - 方法型/拆解型：七层结构 ≥400 字，问法含 ≥1 反向问法
   - 每条：问法 3–6 个多角度 / tags 5–12 / keywords 5–10 / scenarios 四段标记齐全
   - 大类小类判定拿不准时查 [references/category-map.md](references/category-map.md)，表上没有就先记录争议、按最接近项归类，**不停下来空转**
4. **落表**：按 qa-schema.md 的 raw_output.md 格式规范写九列表（头部元数据块必填；单元格 `<br>` 换行、`\|` 转义、数组「；」分隔）
5. **完成报告**：追加到 plan.md 末尾（实产条数 vs 预估、放弃的知识点及原因）
6. **收尾派工**：提示运行 `python tools/kb_ingest.py --batch batches\B-YYYYMMDD-NN --dry-run` 先验，通过后去掉 --dry-run 正式入库；入库后提醒 Jeffrey 抽检（强制差评制：必须指出本批最差一条）

## 双模式

- **M1（v7.1 原子化）**：教程/技巧/手册类素材——讲「怎么做」的知识
- **M2（v6.0 底层解码）**：优秀范文/领导讲话——拆「为什么这样写有效」，产出归 ⑤场景实战/⑥思维与原则/③模块写法；范文中的指导思想段、目标段、保障段顺手登记为模块段落样本（检索切片启用后入段落库）
