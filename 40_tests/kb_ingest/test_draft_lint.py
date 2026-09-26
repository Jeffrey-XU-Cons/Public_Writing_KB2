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
    for g in ["政策引用层级零倒置", "零编造（数据案例可溯源，[待补]清零）", "文种要件齐全",
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
