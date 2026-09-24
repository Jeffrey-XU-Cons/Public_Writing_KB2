r"""
公文写作知识库 · 六大类分类体系（权威定义 + 规则打标）

大类排序即 V5 层次：⑥思维=元认知(为什么)｜①②③④=方法论(怎么做)｜⑤场景=案例(什么样)。
每条知识打 (cat1 大类, cat2 主小类, tags 全小类[含跨类关联])。
Chroma 只能按标量精确过滤 → cat1/cat2 单值可过滤；tags 逗号串进 BM25，跨类也能命中。

同源文件：`公文分类体系.md`（人读版）与萃取提示词补丁。改分类规则只改本文件。
"""

# 六大类 → 小类清单（权威）
TAXONOMY = {
    "文种规范": ["通知通报", "请示报告", "函与批复", "会议纪要", "意见决定", "讲话稿", "总结计划", "简报"],
    "格式规范": ["版式格式", "行文规则", "标题规范", "落款日期", "附件印章"],
    "结构与逻辑": ["开头写法", "主体展开", "结尾写法", "过渡衔接", "篇幅控制"],
    "语言与措辞": ["惯用语", "措辞分寸", "称谓规范", "禁忌错误", "数字时间"],
    "场景实战": ["向上汇报", "布置工作", "跨部门协调", "应急行文", "讲话稿代笔", "修改审核"],
    "思维与原则": ["政治准确", "站位思维", "简明原则", "公文本质"],
}
CAT1_LIST = list(TAXONOMY)
V5_LAYER = {  # 大类 → V5 认知层
    "思维与原则": "元认知", "文种规范": "方法论", "格式规范": "方法论",
    "结构与逻辑": "方法论", "语言与措辞": "方法论", "场景实战": "案例",
}

# doc_type（6 文种口径）→ 文种小类
_DOCTYPE_TO_MINOR = {
    "讲话": "讲话稿", "汇报": "请示报告", "调研": "请示报告",
    "总结": "总结计划", "方案": "总结计划", "规划": "总结计划", "简报": "简报",
}


def _dedup(seq):
    seen, out = set(), []
    for x in seq:
        if x and x not in seen:
            seen.add(x)
            out.append(x)
    return out


def classify(collection, rec):
    """返回 (cat1, cat2主小类, tags全小类list)。rec 含 category/term_kind/doc_type/position/source_file。"""
    cat = str(rec.get("category", ""))
    tk = str(rec.get("term_kind", ""))
    dt = str(rec.get("doc_type", ""))
    pos = str(rec.get("position", ""))
    src = str(rec.get("source_file", ""))

    if collection == "pw_templates":
        minor = _DOCTYPE_TO_MINOR.get(dt, "")
        return "文种规范", (minor or "总结计划"), _dedup([minor, "篇幅控制"])

    if collection == "pw_paragraphs":
        minor = "开头写法" if "开头" in pos else "结尾写法" if "结尾" in pos else "主体展开"
        return "结构与逻辑", minor, _dedup([minor])

    if collection == "pw_golden":
        return "语言与措辞", "惯用语", _dedup(["惯用语", "措辞分寸"])

    if collection == "pw_patterns":
        if rec.get("granularity") == "title" or "标题" in src or "标题" in cat:
            return "结构与逻辑", "标题规范", _dedup(["标题规范"])  # 标题写法↔格式·标题规范
        if "开头结尾" in src:
            return "结构与逻辑", "开头写法", _dedup(["开头写法", "结尾写法"])
        return "语言与措辞", "惯用语", _dedup(["惯用语", "过渡衔接"])

    if collection == "pw_terms":
        if tk == "禁用词":
            return "语言与措辞", "禁忌错误", _dedup(["禁忌错误"])
        if tk == "搭配规范":
            return "语言与措辞", "禁忌错误", _dedup(["禁忌错误", "措辞分寸"])
        if tk == "套话替换":
            return "语言与措辞", "惯用语", _dedup(["惯用语", "禁忌错误"])
        # 行业术语 / 常用用语 → 惯用语（专业用语）；组织称谓类才归称谓规范
        if "组织" in cat or "称谓" in cat:
            return "语言与措辞", "称谓规范", _dedup(["称谓规范"])
        return "语言与措辞", "惯用语", _dedup(["惯用语"])

    if collection == "pw_articles":
        ctype = cat  # load_articles 把 content_type 存进 category
        # 只有“范例(example)”按文种归；技巧/清单按知识类型归（避免技巧文误标成讲话稿等文种）
        if ctype == "example" and dt and dt != "通用":
            minor = _DOCTYPE_TO_MINOR.get(dt, "")
            return "文种规范", (minor or "总结计划"), _dedup([minor])
        # 写作技巧类 → 按标题关键词粗分
        for kw, (c1, c2) in [
            ("标题", ("结构与逻辑", "标题规范")), ("开头", ("结构与逻辑", "开头写法")),
            ("结尾", ("结构与逻辑", "结尾写法")), ("过渡", ("结构与逻辑", "过渡衔接")),
            ("结构", ("结构与逻辑", "主体展开")), ("提纲", ("结构与逻辑", "主体展开")),
            ("修改", ("场景实战", "修改审核")), ("审核", ("场景实战", "修改审核")),
            ("讲话", ("场景实战", "讲话稿代笔")),
            ("政治", ("思维与原则", "政治准确")), ("站位", ("思维与原则", "站位思维")),
            ("简明", ("思维与原则", "简明原则")), ("为文", ("思维与原则", "公文本质")),
        ]:
            if kw in src:
                return c1, c2, _dedup([c2])
        # 技巧类默认：清单归“魂”，其余归“架·主体展开”
        if ctype == "checklist":
            return "思维与原则", "公文本质", _dedup(["公文本质"])
        return "结构与逻辑", "主体展开", _dedup(["主体展开"])

    return "思维与原则", "公文本质", ["公文本质"]


def tag_records(collection, records):
    for r in records:
        c1, c2, tags = classify(collection, r)
        r["cat1"] = c1
        r["cat2"] = c2
        r["tags"] = ",".join(tags)
    return records
