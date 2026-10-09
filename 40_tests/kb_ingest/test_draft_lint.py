"""P3 出口判据：硬闸反例 8/8 拦截（11章 P3）。反例直接读 40_tests/cases/gates/，不在测试里改写。
同时必须放行一组正例（10章/skill_style 里的合格写法），防止规则一刀切。"""

import json
from pathlib import Path

import re

import pytest

import draft_lint as dl

CASES = Path(__file__).resolve().parents[1] / "cases/gates/batch1_硬闸反例.jsonl"


def run_gate(case):
    gate, text = case["gate"], case["input"]
    if gate.startswith("W1-2"):
        return dl.check_thesis(text)
    if gate.startswith("W2-4"):
        return [f for g in dl.sibling_groups(text) for f in dl.check_mece(g)]
    if gate.startswith("W3-2"):
        return dl.check_baseline(text)
    return [f for f in dl.lint(text, rules=[]) if f["gate"] == "W5-1" and f["severity"] == "block"]


@pytest.mark.parametrize("case", [json.loads(l) for l in CASES.read_text(encoding="utf-8").splitlines()],
                         ids=lambda c: c["id"])
def test_hard_gate_counterexample_blocked(case):
    assert run_gate(case), f"{case['id']} 未被拦截：{case['input']}"


# ---------------- 必须放行的正例 ----------------

@pytest.mark.parametrize("s", [
    "卷烟物流三项指标达标的关键在于前置调度",
    "主旨句：两年来，管理体系建设已从框架搭建期进入能力跃升期",
    "2025年以来，公司在管理成熟度评价体系建设上完成了从概念到落地的转变",
])
def test_thesis_pass(s):
    assert dl.check_thesis(s) == []


@pytest.mark.parametrize("s", ["2024年卷烟营销工作情况", "管理体系建设推进情况", "2024年工作总结",
                               "卷烟物流管理", "关于加强卷烟物流管理的思考"])
def test_thesis_topic_variants_blocked(s):
    assert dl.check_thesis(s)


@pytest.mark.parametrize("text", [
    "一、坚持思想破冰，有力推动干部职工观念转变\n二、坚持工作破题，有力保障管理提升扎实推进\n三、坚持改革破局，有力促进管理提升成效日益显现",
    "一、强化党建引领\n二、突出市场导向",
    "（一）组织保障\n（二）资源保障\n（三）考核保障",
])
def test_mece_pass(text):
    assert [f for g in dl.sibling_groups(text) for f in dl.check_mece(g)] == []


@pytest.mark.parametrize("s", [
    "销量同比增长12%，超年度目标3个百分点",
    "管理成熟度试点评价得分由72%提升至89%",
    "管理成熟度试点评价得分从72分提升至89分，提升17分。",
])
def test_baseline_pass(s):
    assert dl.check_baseline(s) == []


def test_clean_draft_has_no_block():
    text = ("一、充分肯定管理提升工作取得的成效\n"
            "（一）坚持思想破冰，推动观念转变\n"
            "“企业化、一体化”管理思维逐步树立，销量同比增长8.6%。\n"
            "（二）坚持工作破题，保障工作推进\n"
            "主要体现在两个方面：一是强化整体推进，二是狠抓责任落实。\n"
            "二、准确把握面临的形势\n")
    assert [f for f in dl.lint(text, rules=[]) if f["severity"] == "block"] == []


# ---------------- 单项规则 ----------------

def test_level_skip():
    assert any("层级跳级" in f["rule"] for f in dl.check_numbering("一、总体要求\n1. 指导思想"))


def test_numbering_reset_under_new_parent():
    text = "一、甲\n（一）子一\n（二）子二\n二、乙\n（一）子一"
    assert dl.check_numbering(text) == []


def test_shi_series_gap():
    assert dl.check_shi_series("一是强化推进；三是狠抓落实。")


def test_total_parts_mismatch():
    assert dl.check_total_parts("工作主要呈现三个特点：一是推进有力；二是成效显著；三是基础扎实；四是机制完善。")


def test_total_parts_match():
    assert dl.check_total_parts("主要体现在三个方面：一是甲，二是乙，三是丙。") == []


def test_corner_quotes_blocked():
    assert dl.check_quotes("严格执行「卷烟经营许可」制度")


def test_placeholder_only_in_final():
    assert dl.check_placeholder("销量[待补:销量]万箱", final=True)
    assert dl.check_placeholder("销量[待补:销量]万箱", final=False) == []


def test_dictionary_severity():
    rules = [
        {"kind": "禁用词", "term": "烟民数量", "source_id": "PW-203-02", "rule": {"severity": "禁止", "replace_with": ["消费者规模"]}},
        {"kind": "禁用词", "term": "所有", "source_id": "PW-201-03", "rule": {"severity": "禁止", "replace_with": ["主要"]}},
        {"kind": "搭配错误", "term": "制定规划", "source_id": "MM-301-01", "rule": {"correct": "编制规划"}},
        {"kind": "套话", "term": "与此同时", "source_id": "CP-401-04", "rule": {"suggested": "同时"}},
    ]
    sev = {f["msg"][:6]: f["severity"] for f in dl.check_dictionary("烟民数量；所有权；制定规划；与此同时", rules)}
    assert list(sev.values()) == ["block", "warn", "warn", "advice"]  # 搭配错误降为 warn：真实成稿实测误伤


def test_long_clause_density():
    long_clause = "通过系统梳理和深入研究国家局关于企业管理成熟度评价体系建设的系列指导文件和政策要求"
    assert dl.check_long_clauses((long_clause + "。") * 3 + "短句。" * 5)


# ---------------- 真实成稿实测（个人历史交付物 r5）抓到的误报 ----------------

def test_spaced_numeral_heading_recognized():
    assert dl.check_numbering("一 、充分肯定成效\n二、着力解决问题") == []


def test_list_restart_at_one_allowed():
    assert dl.check_numbering("（1）甲\n（2）乙\n正文段落\n（1）丙") == []


def test_run_in_heading_period_allowed():
    res = dl.check_title_punct("(二)高质量做好管理提升工作保障。一是要加强能力建设。")
    assert not [f for f in res if f["rule"].startswith("Q-068")]  # 句号不算违规
    assert [f["severity"] for f in res] == ["warn"]  # 标题14字>12，报长度 warn 是对的


def test_colon_heading_warn_not_block():
    assert [f["severity"] for f in dl.check_title_punct("1.硬件基础保障：")] == ["warn"]


def test_heading_degree_supported_in_section():
    text = "（四）专卖管理水平显著提升\n全年查处案件120起。\n其他情况说明。\n其他情况说明。\n（五）下一节"
    assert dl.check_baseline(text) == []


def test_heading_degree_unsupported_blocked():
    assert dl.check_baseline("（四）专卖管理水平显著提升\n各项工作扎实推进。\n（五）下一节")


def test_shenhua_gaige_not_flagged_by_real_dictionary():
    """"全面深化改革"是中央固定表述，官方词表 MM-004 自注"两词通用"，不得当错误搭配。"""
    assert not [f for f in dl.check_dictionary("全面深化改革，进行研究", dl.load_rules())
                if f["rule"] == "搭配错误"]


# ---------------- P3.3 落盘产物 ----------------

ROOT = Path(__file__).resolve().parents[2]
OUTLINE_TPL = (ROOT / ".claude/skills/gw-draft/templates/outline.md").read_text(encoding="utf-8")
REPORT_TPL = (ROOT / ".claude/skills/gw-review/templates/review_report.md").read_text(encoding="utf-8")

FILLED_OUTLINE = """# 大纲：汇报·物流提质
主旨句：物流三项指标达标的关键在于前置调度
## 骨架
一、前置调度使三项指标全部达标（核心判断：…｜素材：S-01｜字数：约600）
二、仍有两处短板需要补齐（核心判断：…｜素材：S-02｜字数：约300）
## 论点地图
| 编号 | 论点（一句话） | 唯一归属位置 | 素材 |
|---|---|---|---|
| P-01 | 前置调度缩短了在途时间 | 一、 | S-01 |
| P-02 | 夜间分拣人手不足 | 二、 | S-02 |
## 缺口
- [待补:夜间分拣人数]——需物流中心提供
"""


def test_blank_outline_template_is_blocked():
    """模板原样交上来不能过：论点地图没填、主旨句是占位。"""
    res = dl.lint("正文。", outline=OUTLINE_TPL, rules=[])
    assert any(f["rule"] == "W2-5 论点地图缺失" for f in res)


def test_filled_outline_passes():
    res = dl.lint("正文。", outline=FILLED_OUTLINE, rules=[])
    assert [f for f in res if f["severity"] == "block"] == []


def test_same_claim_registered_twice_blocked():
    bad = FILLED_OUTLINE.replace("| P-02 | 夜间分拣人手不足 | 二、 |", "| P-02 | 前置调度缩短了在途时间 | 二、 |")
    assert any(f["rule"] == "W2-5 论点多处登记" for f in dl.check_outline(bad))


def test_blank_report_template_is_blocked():
    rules = {f["rule"] for f in dl.check_report(REPORT_TPL)}
    assert "红线未过" in rules


def test_report_all_redlines_pass_and_resolved():
    rep = REPORT_TPL
    for g in ["政策引用层级零倒置", "零编造（数据、案例、判断可溯源，[待补]清零）", "文种要件齐全",
              "政治表述顺序与固定套语零差错", "待人工裁决项全部经 Jeffrey 明示处理"]:
        rep = re.sub(r"(\| " + re.escape(g) + r" \| \*\*红线\*\* \| [^|]+\| )[^|]*\|", r"\1✅ |", rep)
    assert not [f for f in dl.check_report(rep) if f["rule"] == "红线未过"]


def test_pending_decision_blocks():
    rep = REPORT_TPL.replace("| 1 | | | | 待裁决 |", "| 1 | 第3段 | 某项内部数据 | 内部数据 | 待裁决 |")
    assert any(f["rule"] == "R5 待裁决未处理" for f in dl.check_report(rep))


def test_three_rounds_failed_escalates():
    rep = REPORT_TPL.replace("| pass2 措辞审 | 分寸/大话降级/主语残缺/零信息句/25字 | 〔1/3〕 | |",
                             "| pass2 措辞审 | 分寸/大话降级/主语残缺/零信息句/25字 | 3/3 | 未过 |")
    assert any(f["rule"] == "3 轮上限" for f in dl.check_report(rep))


def test_placeholder_thesis_blocked():
    """模板占位说明里有"有"字，曾骗过谓语检测。"""
    assert any(f["rule"] == "W1-2 主旨句未填" for f in dl.lint("正文。", outline=OUTLINE_TPL, rules=[]))


def test_mece_compares_titles_not_run_in_body():
    """真实成稿回归：随文标题后的正文里碰巧都有"效率/效能"等近义字，不应判重叠。"""
    text = ("（一）生产调度一体化。打通信息共享，提高了调度效率。\n"
            "（二）车间生产协同化。实现跨部门沟通，有效提高工作效能。\n"
            "（三）流程控制标准化。减少人为错误，提高工作效率。")
    assert [f for g in dl.sibling_groups(text) for f in dl.check_mece(g)] == []


def test_shared_modifier_gaozhiliang_not_near_synonym():
    """真实成稿回归：两个标题都以"高质量"开头，曾被当成{质量,品质}近义重叠。"""
    text = "一、高质量建成一体化融合式综合管理体系\n二、高质量做好管理提升工作保障\n三、高质量抓好专项行动各项工作任务落实"
    assert [f for g in dl.sibling_groups(text) for f in dl.check_mece(g)] == []


# ---------------- 82 份真实成稿全量实测抽出的误报 ----------------

def test_toc_lines_not_headings():
    text = "一、诊断开展情况......1\n二、发现问题......5\n一、诊断开展情况\n二、发现问题"
    assert [f for g in dl.sibling_groups(text) for f in dl.check_mece(g)] == []
    assert dl.check_numbering(text) == []


def test_part_level_resets_groups():
    text = "第一部分 现状\n一、数据统计\n二、问题分析\n第二部分 规划\n一、数据统计\n二、目标设定"
    assert [f for g in dl.sibling_groups(text) for f in dl.check_mece(g)] == []


def test_enumeration_semicolon_not_title_punct():
    assert dl.check_title_punct("1.国家相关法律法规；\n2.行业相关政策要求；\n29.您认为资源配置是否合理？") == []


def test_title_period_block_only_at_level1():
    """一级带句号拦；二级多为随文标题（82 份实测 221 处）、三级多为列举，只报。"""
    sev = [f["severity"] for f in dl.check_title_punct("一、组织保障。\n（一）组织保障。\n1.成立领导小组。")]
    assert sev == ["block", "warn", "warn"]


def test_toc_with_tab_page_number():
    text = "一、组织结构诊断发现及建议\t4\n一、组织结构诊断发现及建议"
    assert dl.parse_headings(text)[0]["line"] == 2


def test_level3_skip_warn_level1_skip_block():
    sev = {f["severity"] for f in dl.check_numbering("一、甲\n1.子一\n3.子三\n三、丙")}
    assert sev == {"warn", "block"}


def test_two_shi_series_in_one_line_ok():
    assert dl.check_shi_series("一是甲，二是乙，三是丙。另外，一是丁，二是戊。") == []


def test_continuation_series_not_flagged_but_gap_is():
    assert dl.check_shi_series("三是丙；一是甲，二是乙。") == []
    assert dl.check_shi_series("一是甲，三是丙。")


def test_literal_duplicate_heading_is_warn_not_interchange():
    fs = [f for g in dl.sibling_groups("1、库存管理方面\n2、库存管理方面") for f in dl.check_mece(g)]
    assert [(f["rule"], f["severity"]) for f in fs] == [("重复标题", "warn")]



def test_single_char_difference_not_interchangeable():
    text = "（一）“诊”的方式方法\n（二）“断”的方式方法"
    assert [f for g in dl.sibling_groups(text) for f in dl.check_mece(g)] == []


def test_level_skip_heading_like_blocks_enumeration_warns():
    sev = [f["severity"] for f in dl.check_numbering("一、组织机构\n1.评价体系建设工作组")]
    assert sev == ["block"]
    sev = [f["severity"] for f in dl.check_numbering("一、编制依据\n1.国家相关法律法规。")]
    assert sev == ["warn"]


def test_continuous_numbering_across_parents_allowed():
    text = "第一篇 发展基础\n第一章 外部环境\n第二章 发展现状\n第二篇 总体要求\n第三章 指导思想"
    assert dl.check_numbering(text) == []
    text = "一、完善转化\n（一）甲\n（二）乙\n二、深化改革\n（三）丙"  # 二级跨一级连续编号
    assert dl.check_numbering(text) == []


def test_part_then_level1_not_level_skip():
    assert dl.check_numbering("第一部分 现状\n一、基本情况\n二、主要问题") == []


def test_real_gap_still_caught_after_continuation_rule():
    assert dl.check_numbering("一、甲\n（一）子一\n（三）子三")


def test_zuofeng_and_jilv_are_distinct_pillars():
    """作风建设、纪律建设是党的建设中并列两项，不是范畴重叠（曾因自拟反例 G-03 误判）。"""
    text = "一、打好作风建设持久战\n二、加强党的纪律建设"
    assert [f for g in dl.sibling_groups(text) for f in dl.check_mece(g)] == []


def test_different_domains_same_goal_word_not_overlap():
    text = "（一）推进集约化生产，着力提高生产组织效能\n（二）深化专业运作，着力提高物流保障效率"
    assert [f for g in dl.sibling_groups(text) for f in dl.check_mece(g)] == []


def test_long_clause_density_is_warn():
    """2026-09-25 拍板：真实成稿全部超标，降为 warn。"""
    long_clause = "通过系统梳理和深入研究国家局关于企业管理成熟度评价体系建设的系列指导文件和政策要求"
    assert [f["severity"] for f in dl.check_long_clauses((long_clause + "。") * 3)] == ["warn"]


# ---------------- R6 判断溯源（2026-09-29） ----------------

JUDGE_DRAFT = "一、总体情况\n试点暴露的问题主要是等级递进不清。原因在于编制人员对等级特征掌握不够系统。\n"


def _trace_report(rows):
    return "## 六、判断溯源表\n\n| # | 判断（原句摘录） | 出处（素材 + 原话） | 结论 |\n|---|---|---|---|\n" + rows + "\n## 七、知识库贡献分\n"


def test_trace_table_missing_blocks():
    assert any(f["rule"] == "R6 溯源表缺失" for f in dl.check_trace(JUDGE_DRAFT, "## 一、轮次记录\n"))


def test_unregistered_judgment_blocks():
    """模板原样（只有占位行）= 判断句全部未登记。"""
    rules = [f["rule"] for f in dl.check_trace(JUDGE_DRAFT, REPORT_TPL)]
    assert "R6 判断未溯源" in rules


def test_judgment_without_source_blocks():
    rep = _trace_report("| 1 | 原因在于编制人员对等级特征掌握不够系统 | | 无出处 |")
    assert any(f["rule"] == "R6 判断无出处" for f in dl.check_trace(JUDGE_DRAFT, rep))


def test_registered_judgments_pass():
    rep = _trace_report("| 1 | 试点暴露的问题主要是等级递进不清 | 素材5.2：各等级间递进路径不够清晰 | 有出处 |\n"
                        "| 2 | 原因在于编制人员对等级特征掌握不够系统 | 素材5.5：对理论体系、方法工具掌握不够系统 | 有出处 |")
    assert dl.check_trace(JUDGE_DRAFT, rep) == []


def test_ordinal_shi_not_flagged_as_judgment():
    """“二是……的保障要素”是序数列举，不是“是……的保障”判断句。"""
    assert dl.judgment_sentences("二是综合管理，聚焦支撑企业运行的保障要素。") == []


def test_final_without_report_blocks(tmp_path, capsys):
    draft = tmp_path / "终稿.md"
    draft.write_text("一、总体情况\n销量同比增长5%。\n", encoding="utf-8")
    assert dl.main([str(draft), "--final"]) == 1
    assert "R6 缺审校报告" in capsys.readouterr().out


# ---------------- 补齐 AUTO 项（2026-09-29） ----------------

def _rules(res):
    return {(f["rule"], f["severity"]) for f in res}


def test_policy_order_inversion_warns():
    res = dl.check_policy_order("认真贯彻全国烟草工作会议精神和习近平新时代中国特色社会主义思想，推动工作。")
    assert ("Q-017 指导思想顺序", "warn") in _rules(res)


def test_official_policy_formula_not_flagged():
    """国家局十四五规划原句：大会精神在前、思想在后，是正式句式。"""
    assert dl.check_policy_order("深入贯彻党的十九大精神，坚持以习近平新时代中国特色社会主义思想为指导，全面推进。") == []


def test_sige_order_is_advice_only():
    res = dl.check_sige("坚决做到“两个维护”，树牢“四个意识”，坚定“四个自信”。")
    assert _rules(res) == {("Q-018 固定组合顺序", "advice")}


def test_wrong_political_form_warns():
    assert ("Q-019/025 表述不规范", "warn") in _rules(dl.check_wrong_forms("推动公司高质量的发展。"))


def test_mixed_numbering_format_warns():
    assert dl.check_numbering_format("1、第一项内容\n2.第二项内容\n")[0]["rule"] == "Q-030 同层序号格式不一"
    assert dl.check_numbering_format("1.第一项内容\n2.第二项内容\n") == []


def test_percent_in_chinese_warns():
    assert dl.check_number_format("合格率达到百分之八十五。")
    assert dl.check_number_format("做到百分之百覆盖。") == []


def test_paragraph_over_500_without_items_warns():
    para = "公司持续推进管理体系建设工作取得了阶段成效" * 30 + "。"
    assert ("Q-041 长段无分条", "warn") in _rules(dl.check_long_paragraph(para))


def test_same_lead_verb_three_times_advice():
    res = dl.check_same_lead("一是坚持目标导向。二是坚持问题导向。三是坚持结果导向。")
    assert ("Q-054 领起词重复", "advice") in _rules(res)


def test_opening_metaphor_and_generic_ending_warn():
    text = "站在新的历史坐标系上，公司启动体系建设。\n正文。\n让我们携手并进，共创辉煌。\n"
    rules = _rules(dl.check_open_close(text))
    assert ("Q-055 开场铺垫", "warn") in rules and ("Q-056 通用结尾", "warn") in rules


def test_length_out_of_range():
    outline = "- 字数区间：5000–7000 字｜构建方向：自下而上"
    short = "字" * 3000
    assert dl.check_length(short, outline, final=True)[0]["severity"] == "block"
    assert dl.check_length(short, outline, final=False)[0]["severity"] == "warn"
    assert dl.check_length("字" * 4500, outline, final=True)[0]["severity"] == "warn"  # 超出不到 20%
    assert dl.check_length("字" * 6000, outline, final=True) == []


# ---------------- R7 逐段审表（2026-10-01） ----------------

PARA_A = "我们以端到端视角梳理核心业务流程，共识别一级流程〔数据〕条、二级流程〔数据〕条，形成覆盖全业务链条的流程清单，为后续标准编写打下基础。"
PARA_B = "流程长由业务分管领导担任，对流程绩效负总责；流程专员由业务骨干担任，负责流程文件起草和日常维护，确保每条流程都有人管、有人改。"
SEG_DRAFT = f"一、搭建流程框架\n现将主要做法介绍如下。\n{PARA_A}\n（一）明确流程责任\n{PARA_B}\n"
SEG_HEAD = "## 七、逐段审表\n\n| # | 位置 | 段首摘录 | 本段主旨 | 跑题句 | 与上下段衔接 | 概念/数据口径核对 | 结论 |\n|---|---|---|---|---|---|---|---|\n"
ROW_A = ("| 1 | 一 | 我们以端到端视角梳理核心业务 | 用端到端梳理建立覆盖全链条的流程清单 | 无 "
         "| 承接标题“搭建框架”，下接（一）责任落实 | 一级、二级流程数取自 2024-08 清单，口径一致 | 通过 |")
ROW_B = ("| 2 | 一（一） | 流程长由业务分管领导担任 | 流程长、流程专员两级责任分工 | 无 "
         "| 上段建清单、本段定责任，顺接 | “流程长”与四（二）用法一致 | 通过 |")


def _seg_report(rows):
    return SEG_HEAD + rows + "\n## 八、知识库贡献分\n"


def test_r7_table_missing_blocks():
    assert [f["rule"] for f in dl.check_paragraphs(SEG_DRAFT, "## 六、判断溯源表\n")] == ["R7 逐段审表缺失"]


def test_r7_template_placeholder_means_all_unreviewed():
    """模板原样（只有占位行）= 每段都未审。"""
    rules = [f["rule"] for f in dl.check_paragraphs(SEG_DRAFT, REPORT_TPL)]
    assert rules == ["R7 段落未审", "R7 段落未审"]


def test_r7_unregistered_paragraph_blocks():
    found = dl.check_paragraphs(SEG_DRAFT, _seg_report(ROW_A))
    assert [(f["rule"], f["line"]) for f in found] == [("R7 段落未审", 5)]


def test_r7_tick_only_blocks():
    lazy = ROW_B.replace("上段建清单、本段定责任，顺接", "✅").replace("“流程长”与四（二）用法一致", "无")
    found = dl.check_paragraphs(SEG_DRAFT, _seg_report(ROW_A + "\n" + lazy))
    assert [f["rule"] for f in found] == ["R7 只打勾未留痕"]
    assert "衔接" in found[0]["msg"] and "口径" in found[0]["msg"]


def test_r7_thesis_copying_heading_blocks():
    copied = ROW_B.replace("流程长、流程专员两级责任分工", "明确流程责任")
    found = dl.check_paragraphs(SEG_DRAFT, _seg_report(ROW_A + "\n" + copied))
    assert [f["rule"] for f in found] == ["R7 只打勾未留痕"] and "本段主旨" in found[0]["msg"]


def test_r7_failed_verdict_blocks():
    failed = ROW_B.replace("| 通过 |", "| 不通过 |")
    found = dl.check_paragraphs(SEG_DRAFT, _seg_report(ROW_A + "\n" + failed))
    assert [f["rule"] for f in found] == ["R7 段落审查未过"]


def test_r7_all_rows_filled_pass_and_short_transition_skipped():
    """“现将主要做法介绍如下。”不足 40 字，不要求登记。"""
    assert dl.check_paragraphs(SEG_DRAFT, _seg_report(ROW_A + "\n" + ROW_B)) == []


def test_r7_runs_only_in_final_with_report(tmp_path, capsys):
    d, r = tmp_path / "d.md", tmp_path / "r.md"
    d.write_text(SEG_DRAFT, encoding="utf-8")
    r.write_text(REPORT_TPL, encoding="utf-8")
    dl.main([str(d), "--report", str(r)])
    assert "R7" not in capsys.readouterr().out          # 非终验不触发
    dl.main([str(d), "--report", str(r), "--final"])
    assert "R7 段落未审" in capsys.readouterr().out


# ---------------- 公文体例（2026-10-03，P4 第 2 轮人工审 6 条全漏） ----------------

def test_two_subsections_warns():
    text = "一、坚持系统谋划，明确路径\n（一）锚定模式，确立主线\n（二）统筹要素，整体优化\n"
    assert ("Q-071 同级节数", "warn") in _rules(dl.check_section_count(text))


def test_three_subsections_pass():
    text = "一、坚持系统谋划，明确路径\n（一）锚定模式，确立主线\n（二）统筹要素，整体优化\n（三）健全机制，压实责任\n"
    assert dl.check_section_count(text) == []


def test_seven_level1_sections_warn():
    text = "".join(f"{c}、做好第{c}项工作\n" for c in "一二三四五六七")
    assert ("Q-071 同级节数", "warn") in _rules(dl.check_section_count(text))


def test_mixed_heading_form_warns_on_odd_one():
    text = "（一）锚定模式，确立主线\n（二）统筹要素，整体优化\n（三）六要素整体优化\n"
    res = dl.check_heading_form(text)
    assert [f["line"] for f in res] == [3] and res[0]["severity"] == "warn"


def test_uniform_heading_form_pass_and_run_in_title_ignored():
    text = "（一）锚定管控模式。公司实行母分公司体制，构建管理模式。\n（二）统筹六大要素\n（三）健全组织机制\n"
    assert dl.check_heading_form(text) == []


def test_table_in_report_genre_blocks_only_with_genre():
    draft = "正文。\n| 类别 | 数量 |\n|---|---|\n| 核心业务 | 16 |\n"
    assert ("Q-073 汇报类用了表格", "block") in _rules(dl.check_report_table(draft, "- 文种：经验交流材料｜依据：…"))
    assert dl.check_report_table(draft, "- 文种：实施方案｜依据：…") == []
    assert dl.check_report_table(draft, None) == []
    assert dl.check_report_table("正文。", "- 文种：汇报材料") == []


def test_table_rule_skips_outline_itself():
    outline = "- 文种：汇报材料｜依据：…\n## 论点地图\n| 编号 | 论点 |\n|---|---|\n| P-01 | 甲 |\n"
    assert dl.check_report_table(outline, outline) == []


# ---- Q-079 讲话复述方案（P4 第 6 轮）----

PLAN = "以标准化良好行为企业认证为突破口建立健全企业标准体系和工作机制开展识别谋共管宣贯聚共识运行促共用反馈求共进的四共活动"


def test_plan_copy_warns_when_later_parts_restate_plan():
    text = "一、认识\n" + PLAN + "\n二、重点\n" + PLAN + "\n三、落实\n要抓好领导带头这个关键。\n"
    res = dl.check_plan_copy(text, PLAN)
    assert [f["rule"] for f in res] == ["Q-079 讲话复述方案"]


def test_plan_copy_ignores_first_part_and_fresh_requirements():
    text = ("一、认识\n" + PLAN + "\n二、关键\n主要领导要当第一责任人，班子成员要当好指挥员，各单位明确一名分管负责人。\n"
            "三、落实\n做好进度表，做好设计图，做好施工图，每个节点倒排工期。\n")
    assert dl.check_plan_copy(text, PLAN) == []


def test_plan_copy_skips_text_without_second_level1_heading():
    assert dl.plan_copy_ratio("一、只有一部分\n" + PLAN, PLAN) is None


# ---- W2-0 范文对照表（2026-10-04）----

def _speech_outline(table_rows_text):
    return ("文种：领导讲话（启动部署）｜依据：会上口头部署\n\n## 范文对照表\n\n| 范文要件 | 本稿 | 位置 |\n|---|---|---|\n"
            + table_rows_text + "\n## 缺口\n")


def test_speech_outline_without_exemplar_table_warns():
    res = dl.check_outline(_speech_outline("| 〔开场交代分工（AR-0001）〕 | 具备 | 〔开场〕 |\n"))
    assert any(f["rule"] == "W2-0 范文对照表未填" for f in res)


def test_speech_outline_missing_item_warns_and_filled_passes():
    res = dl.check_outline(_speech_outline("| 部署段压实领导责任（AR-0012） | 缺 | — |\n"))
    assert any(f["rule"] == "W2-0 范文要件缺" for f in res)
    res = dl.check_outline(_speech_outline("| 部署段压实领导责任（AR-0012） | 具备 | 三（二） |\n"))
    assert not any(f["gate"] == "W2-0" for f in res)


def test_genre_without_exemplars_skips_exemplar_check():
    # 工作总结、请示等范文库未建的文种不查 W2-0
    for genre in ("工作总结", "请示"):
        assert not any(f["gate"] == "W2-0" for f in dl.check_outline(f"文种：{genre}｜依据：x\n")), genre


# ---- W2-0 扩到汇报、方案、规划、调研/诊断（2026-10-07，B-20261007-AR-02）----

def _genre_outline(genre, table_rows_text=""):
    return (f"文种：{genre}｜依据：x\n\n## 范文对照表\n\n| 范文要件 | 本稿 | 位置 |\n|---|---|---|\n"
            + table_rows_text + "\n## 缺口\n")


@pytest.mark.parametrize("genre", ["汇报材料（经验交流）", "实施方案", "工作方案", "发展规划", "调研报告", "管理诊断报告"])
def test_exemplar_genres_without_table_warn(genre):
    res = dl.check_outline(_genre_outline(genre, "| 〔开篇一句交代依据（AR-0201）〕 | 具备 | 〔开篇〕 |\n"))
    hits = [f for f in res if f["rule"] == "W2-0 范文对照表未填"]
    assert hits and hits[0]["severity"] == "warn"


@pytest.mark.parametrize("genre", ["汇报材料", "实施方案", "发展规划", "调研报告"])
def test_exemplar_genres_missing_item_warns_and_filled_passes(genre):
    res = dl.check_outline(_genre_outline(genre, "| 每阶段列标志性成果（AR-0203） | 缺 | — |\n"))
    assert any(f["rule"] == "W2-0 范文要件缺" for f in res)
    res = dl.check_outline(_genre_outline(genre, "| 每阶段列标志性成果（AR-0203） | 具备 | 三（一） |\n"))
    assert not any(f["gate"] == "W2-0" for f in res)


def test_exemplar_extension_does_not_extend_human_questions():
    # W2-6 人工两问只对讲话；汇报等文种不因 W2-0 扩展而被要求两问
    for genre in ("汇报材料", "实施方案", "发展规划", "调研报告"):
        assert not any(f["gate"] == "W2-6" for f in dl.check_outline(_genre_outline(genre))), genre


# ---- W2-6 确认点 2 人工两问（2026-10-06，P4 第 7 轮）----

SPEECH_OUTLINE_HEAD = "文种：领导讲话（工作报告之后的主要领导讲话）｜依据：年度工作会\n\n"
TWO_Q = ("## 确认点 2 人工两问\n\n| 问 | 起草方判断与依据 | 选项与推荐 | 人工答复 |\n|---|---|---|---|\n"
         "| Q1 分工：本稿与同场其他讲话、报告、方案怎么分工？ | 工作报告已部署明年任务；三（二）条目来自 S-02 报告备料 | A 只讲方向／B 照部署；推荐 A | {a1} |\n"
         "| Q2 问题分量：问题部分放多重？ | 位置 B；素材有思想、合力两层问题 | A 单列／B 并入；推荐 A | {a2} |\n")


def test_speech_outline_without_two_questions_blocked():
    rules = [f["rule"] for f in dl.check_outline(SPEECH_OUTLINE_HEAD) if f["severity"] == "block"]
    assert rules.count("确认点2 人工两问缺失") == 2


def test_speech_outline_placeholder_two_questions_blocked():
    tpl = (ROOT / ".claude/skills/gw-draft/templates/outline.md").read_text(encoding="utf-8")
    section = tpl[tpl.index("## 确认点 2 人工两问"):tpl.index("## 确认点 2\n")]
    assert any(f["rule"] == "确认点2 人工两问未填" for f in dl.check_outline(SPEECH_OUTLINE_HEAD + section))


def test_two_questions_pending_ok_before_final_but_blocked_at_final():
    outline = SPEECH_OUTLINE_HEAD + TWO_Q.format(a1="待确认", a2="待确认")
    assert not any(f["gate"] == "W2-6" for f in dl.check_outline(outline))
    res = dl.lint("正文。", outline=outline, final=True, rules=[])
    assert [f["rule"] for f in res if f["gate"] == "W2-6"] == ["确认点2 人工两问未答复"] * 2


def test_two_questions_self_answer_not_accepted():
    """起草方代答（没有“已确认（日期）”格式）不算数。"""
    outline = SPEECH_OUTLINE_HEAD + TWO_Q.format(a1="起草方选 A", a2="已确认：单列")
    assert len(dl.check_human_answers(outline)) == 2


def test_two_questions_answered_passes_final():
    outline = SPEECH_OUTLINE_HEAD + TWO_Q.format(a1="已确认（2026-10-06）：A", a2="已确认（2026-10-06）：单列，约三成")
    assert dl.check_human_answers(outline) == [] and not any(f["gate"] == "W2-6" for f in dl.check_outline(outline))


def test_two_questions_not_required_for_report():
    assert dl.check_human_answers("文种：汇报材料｜依据：x\n") == []
    assert not any(f["gate"] == "W2-6" for f in dl.check_outline("文种：汇报材料｜依据：x\n"))
