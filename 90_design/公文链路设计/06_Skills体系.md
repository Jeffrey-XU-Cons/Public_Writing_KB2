# 第六章 · Skills 体系

> 公文写作智能体 · 总体设计方案 **v1.2** · 第 6/8 章
> 导航：[索引](00_设计方案索引.md) ｜ 上一章：[写作流程](05_写作流程.md) ｜ 下一章：[项目管理与质保](07_项目管理与质保.md)
> v1.1 修订：新增 6.2 修改能力矩阵（ADR-014）；gw-draft/gw-review 职责与 references 扩充（modules/ 速查库）；仍维持 7 个 skill 封顶（ADR-004 不变）
> v1.2 修订（ADR-015）：gw-ingest 流水线去掉 Excel 转换环节；人工修改知识库的入口是 kb_editor.py 网页端（工具而非 skill，不占 skill 名额）

---

## 6.1 清单（7 个封顶）

| skill | 职责 | 触发词要点 | 下游 |
|---|---|---|---|
| `gongwen` | 总控：判意图（写/改/查/建库）→判文种→任务单→派工→终验（20 条门禁呈报）。只调度不动笔，薄 skill | 「写公文」「起草+文种名」「改这份公文」；**不含裸的「起草」「写材料」**（避让全局 draft） | gw-search/draft/review；references/wenzhong-router.md |
| `gw-search` | 检索：V5 诊断→多路查询→A/B 分级→素材包 | 「查公文素材」「检索公文库」「找写法/例句/模板」 | tools\search.py |
| `gw-draft` | **文章提纲设计** + 初稿（内置大纲确认闸：不确认不展开）；【v1.1】模块写法指导（指导思想/工作目标等板块按模块要点生成） | 「出大纲」「搭骨架」「写初稿」（主要由总控派工） | gw-search 补检；references/framework-guide、tobacco-style、wenzhong/×6、**modules/** |
| `gw-review` | 四 pass 审校（格式/措辞/站位/润色）+ 诊断模式（改他稿）+ 【v1.1】**四类定点修改操作**（标题/段落结构/内容修辞/语句修辞） | 「审校」「三审」「校对这份材料」；定点修改口语触发：「标题再想几个」「这段重排」「这句拗口」 | tools\draft_lint.py；references/quality-checklist(Q-001~094)、format-rules、**title-guide、rhetoric-guide** |
| `gw-extract` | 萃取：M1 v7.1 / M2 底层解码双模式，批次制+预估报告+首件确认 | 「萃取入公文库」「拆解这篇范文」（绑定「公文库/入库」字样，避让全局 book2qa） | 前置全局 to-md；收尾派工 gw-ingest；references/qa-schema、deep-decode、category-map |
| `gw-ingest` | 入库编排：调 kb_ingest.py 一条龙（**校验→审计→建索引**，v1.2 无转换环节）；提示人工修改走 kb_editor.py 网页端 | 「入库」「建索引」「导入语料」「打开知识库编辑页」 | tools\kb_ingest.py（**门禁在 exit code 上，skill 调用只是提醒**）；tools\kb_editor.py |
| `gw-audit` | 库体检：全量审计+golden 评测，红黄绿灯+修复清单 | 「审计知识库」「知识库体检」「质量门禁」 | tools\kb_audit.py + kb_eval.py |

否决记录：❌ pm-check（收尾例程非按需能力）❌ gw-plan（诊断归 gw-search 提示词）❌ gw-polish（并入 review pass4）❌ 知识分类/模板管理/检索评测 skill ❌ 12 个文种/专项 skill（旧项目拆法，维护灾难）❌【v1.1】标题/段落/修辞独立 skill（四类定点操作共享同一份稿件上下文与审校知识，拆开 = 传四次全文，并入 gw-review 为「操作模式」）。

## 6.2 修改能力矩阵（v1.1 新增，ADR-014 的落地总表）

用户需求的五类能力 → skill 内操作模式 → 知识与 references 的完整映射：

| 能力 | 入口 | 动作要点 | 知识库调用 | references |
|---|---|---|---|---|
| **文章提纲设计/重构** | gw-draft 大纲模式 | 主旨句（判断句）+三级骨架+论点地图；重构 = 先诊断失分再重排；产出重走确认点 2 | c3（开头/主体/结尾/**模块写法**）+ c1 骨架 + 模板库 | framework-guide、wenzhong/ |
| **文字标题设计修改** | gw-review·标题操作 | 标题四戒 + 文种标题规范（发文机关+事由+文种）+ 一次出 3 个候选供选（选择题式呈报） | c2 标题规范 + c4 惯用语 | title-guide（含词句大全标题模式库精选） |
| **段落结构设计修改** | gw-review·段落操作 | 段首撮要/总分对应/MECE 重排/过渡衔接补全；附前后对照 | c3 主体展开·过渡衔接 + 段落库同 func 范例 | framework-guide |
| **文字内容修辞修改** | gw-review·内容操作 | 大话降级/具象化（数字、场景锚定）/零信息句清除/金句只从库中定向调取不编 | c4 措辞分寸·惯用语 + patterns 句式库 | rhetoric-guide、tobacco-style |
| **语句结构修辞修改** | gw-review·语句操作 | 25 字断句/主语补全/排比节奏/领起词交替（防「一是坚持…二是坚持…」单调） | c4 + patterns | rhetoric-guide、quality-checklist 语言项 |
| **模块写法借鉴**（贯穿上述各项与初稿生成） | gw-draft / gw-review 皆可调 | 「这段指导思想怎么写」→ 先检索模块写法 QA + 模块段落范例，再动笔 | `--category c3 --l2 模块写法` + 段落库 `模块-*` func | **modules/** 速查（见 6.3） |

路由说明：gongwen 总控把定点修改口语指令（「标题再想几个」等）直接路由到对应操作，不走完整写作主干；操作产出一律附前后对照。

## 6.3 modules/ 模块写法速查库（v1.1 新增，`gw-draft/references/modules/`）

一模块一文件，每份 ≤60 行「写法要点卡」：功能定位（这个模块在文中干什么）/ 标准结构 / 常用句式领起词 / 好坏对照各 1 例 / 易错点：

```
modules/指导思想.md   modules/总体要求.md   modules/工作思路.md   modules/工作目标.md
modules/思想认识.md   modules/基本原则.md   modules/主要任务.md   modules/重点举措.md
modules/保障措施.md   modules/组织领导.md   modules/实施步骤.md
```

内容来源（Phase 2/3 随萃取批次同步沉淀，不另立阶段）：技巧汇编中讲模块写法的篇目（M1 萃取时顺产要点卡）+ 范文 M2 拆解时归纳的模块段落规律。**双轨定位**：要点卡常驻 references（写作时必读的硬规范，省一次检索）；完整方法 QA 与段落范例入库（按需检索的软素材，供深挖和多范例对比）——与「方法论一半 references 一半入库」的总原则一致。

## 6.4 与全局 skills 边界（写进项目 CLAUDE.md「skill 路由声明」小节，约 10 行）

| 全局 skill | 分界 |
|---|---|
| draft | 文体分界：有文种/行文关系/落款的公文→gongwen；咨询报告材料段落→draft |
| book2qa | 目标库分界：通用书籍→book2qa 入 D:\Knowledge-QA；公文域素材→gw-extract 入本项目六类库 |
| knowledge-distiller | 产物分界：本项目只萃 QA 不再蒸 skill |
| kb-organize | 不同域：gw-* 不碰 Obsidian；触发词避开「整理 md/加编号」 |
| to-md | 直接复用作 gw-extract 前置，严禁重写转换脚本 |
| presentation-design | 讲话稿/汇报文字稿→gongwen；汇报 PPT→presentation-design，遇「做汇报 PPT」主动转出 |

## 6.5 旧 skill 文档改造

- skill_quality.md(94 条) → gw-review/references/quality-checklist.md：逐条编号 Q-001~094；每条标 [AUTO]/[LLM]，AUTO 项分流进 draft_lint.py；直引号改弯引号
- skill_style.md → gw-draft/references/tobacco-style.md（单一权威源，gw-review 以路径引用不复制）；河南中烟专属段加 [客户:] 标注
- skill_framework.md → 「立意三题+主旨句三检验」提进 gw-draft 正文（过关闸须常驻）；其余留 references/framework-guide.md
- 旧「公文写作体系」12-skill 套件：判文种表→gongwen/references/wenzhong-router.md；文种_01~06 精华→gw-draft/references/wenzhong/ 6 个指南；专项_02 标题 / 专项_04 用词 / 专项_05 金句的词句库 →【v1.1】分别充实 title-guide、rhetoric-guide 与大类④萃取种子。**方法论一半降维 references（写作必读硬规范）、一半 QA 化入库（按需检索软素材）——这是相对旧项目的结构性升级**
