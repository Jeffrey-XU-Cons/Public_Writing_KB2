"""Controlled vocabularies for the QA knowledge base.

This module is the SINGLE source of truth for all enum values
(ADR-014: category c3 includes 模块写法). Every validator, ingest
script and the future web editor must import from here — never
hard-code these lists elsewhere.
"""

# 六大类：1骨 2形 3架 4肉 5用 6魂
CATEGORY_NAMES = {
    1: "文种规范",
    2: "格式规范",
    3: "结构与逻辑",
    4: "语言与措辞",
    5: "场景实战",
    6: "思维与原则",
}

# category_l2 受控词表（用户钦定小类；v1.1 起 c3 含「模块写法」）
CATEGORY_L2 = {
    1: ["通知通报通告", "请示报告", "函批复", "会议纪要",
        "意见决定决议", "讲话发言稿", "总结计划方案", "简报信息"],
    2: ["版式格式", "行文规则", "标题规范", "落款与成文日期", "附件与印章"],
    3: ["开头写法", "主体展开", "结尾写法", "过渡衔接", "篇幅控制", "模块写法"],
    4: ["公文惯用语", "措辞分寸", "称谓规范", "禁忌与常见错误", "数字时间规范"],
    5: ["向上汇报", "布置工作", "跨部门协调", "应急敏感行文",
        "领导讲话稿代笔", "修改审核他人公文"],
    6: ["政治性与准确性", "站位思维", "简明性原则", "公文与普通写作的区别",
        "结构优先原则"],  # 2026-09-24 新增，容纳 A6（改框架成本是改终稿的 1/10）——
                        # 原 4 类都是"表达"维度，A6 讲的是"过程/时机"维度，硬塞进去会牵强
}

DOC_TYPES = [
    "通知", "通报", "通告", "请示", "报告", "函", "批复", "会议纪要",
    "意见", "决定", "决议", "讲话稿", "总结", "计划", "方案", "简报", "通用",
    # 2026-10-07 范文库扩到六个文种指南（gw-draft references/wenzhong 01—06）时补：非法定文种，但是咨询交付物的主力
    "汇报材料", "规划", "调研报告",
]

ANSWER_TYPES = ["条文型", "方法型", "拆解型"]
EXTRACT_METHODS = ["v7.1", "v6.0", "m3", "人工"]
STATUS_VALUES = ["active", "deprecated"]
QUALITY_GRADES = ["A", "B", "C"]

# answer length bounds (chars) per answer_type
# ADR-017: 方法/拆解型 answers 500–2000; 条文型 keeps a light floor so genuine
# format/statute knowledge is not padded (padding hurts retrieval).
ANSWER_MIN_CHARS = {"条文型": 150, "方法型": 500, "拆解型": 500}
ANSWER_MAX_CHARS = 2000  # global ceiling, all types

# question count range (v1.1: 3–6 问法)
QUESTION_COUNT = (3, 6)
TAGS_COUNT = (5, 12)
KEYWORDS_COUNT = (5, 10)

# scenarios 四段标记（v7.1 结构化应用场景）
SCENARIO_MARKERS = ["【主要适用场景】", "【典型使用者】", "【触发时机】", "【注意】"]

# QA 真源文件名（每大类一个 JSONL）
QA_FILENAMES = {
    1: "c1_文种规范.jsonl",
    2: "c2_格式规范.jsonl",
    3: "c3_结构与逻辑.jsonl",
    4: "c4_语言与措辞.jsonl",
    5: "c5_场景实战.jsonl",
    6: "c6_思维与原则.jsonl",
}

# 段落库 func 受控值（v1.1 新增 模块-* 前缀族），检索切片启用
PARAGRAPH_FUNCS = [
    "开头", "主体-成绩", "主体-问题", "主体-措施", "过渡", "结尾",
    "模块-指导思想", "模块-工作思路", "模块-工作目标", "模块-思想认识",
    "模块-基本原则", "模块-主要任务", "模块-保障措施", "模块-组织领导",
]

# 反向问法启发式（方法型/拆解型至少命中一问）
REVERSE_QUESTION_PATTERN = r"(踩坑|误区|错误|失败|禁忌|坑|为什么.*不)"

# 全项目禁用命名（audit 巡查）
BANNED_NAME_PATTERN = r"(_v\d|_final|_backup|旧版|清洗前)"

# --- 07 章 v2 §1.1/1.2/1.3、09 章§4.1（11 章 P1.3 落地，范围收窄到 depth/enforce/
# w_layer + 最小挂钩链，07 章 §1.4 的 usability/tobacco_fit/confidence/conflict_with
# 留到后续阶段） ---

# 抽象度分层（同一大类内，07 章§1.1）
DEPTH_VALUES = ["axiom", "principle", "method", "technique", "rule"]

# 执行强度（07 章§1.3）
ENFORCE_VALUES = ["hard", "soft", "advice"]

# 写作体系六层，可多值（09 章§4.1）
W_LAYER_VALUES = ["W1", "W2", "W3", "W4", "W5"]

# --- 范文库 articles.jsonl（04 章§4.1 非 QA 单元；2026-10-04 P4 第 5、6 轮缺口提前开讲话类）---
# 04 章原字段 id/title/doc_type/org_level/industry/summary/why_good/linked_qa/source_path/grade，
# 讲话类加 subtype/skeleton/must_haves 三字段：起草时逐条对照“范文有、本稿缺”。

ARTICLE_FILENAME = "articles.jsonl"
ARTICLE_ID_PATTERN = r"^AR-\d{4}$"
ARTICLE_REQUIRED = ["id", "title", "doc_type", "subtype", "org_level", "industry", "summary",
                    "skeleton", "why_good", "must_haves", "linked_qa", "source_path", "grade", "batch_id"]

# 讲话稿子类（文种_06 及其变体）
SPEECH_SUBTYPES = ["工作会议讲话", "现场会讲话", "启动部署讲话", "推进会讲话", "培训动员讲话", "总结讲话"]

# 讲话人所在层级（脱敏后保留的行政层级）
ORG_LEVELS = ["行业", "省级商业", "省级工业", "地市级", "县级"]

ARTICLE_GRADES = ["A", "B"]          # C 级不入库
ARTICLE_WHY_GOOD_COUNT = (3, 6)
ARTICLE_MUST_HAVES_COUNT = (4, 10)
