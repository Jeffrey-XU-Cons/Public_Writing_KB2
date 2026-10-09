from deidentify import deidentify


def _new(text):
    return deidentify(text)[0]


# --- 首批试跑抓到的 4 个误报，逐条做成回归 ---

def test_zongti_not_a_name():
    assert _new("工作与公司总体部署相衔接") == "工作与公司总体部署相衔接"


def test_fu_zong_ze_not_a_name():
    assert _new("主要负责人负总责") == "主要负责人负总责"


def test_generic_tongzhi_kept():
    assert _new("各单位主要负责同志要亲自抓") == "各单位主要负责同志要亲自抓"


def test_guangda_tongzhi_kept():
    assert "广大同志" in _new("希望广大同志再接再厉")


# --- 首批试跑的正确命中，保证改规则后不丢 ---

def test_name_with_tongzhi():
    assert _new("刘明同志代表工作专班作了报告") == "〔姓名〕同志代表工作专班作了报告"


def test_name_with_juzhang():
    assert "陈志强" not in _new("陈志强局长强调")


def test_signature_line():
    assert deidentify("王 建 华", known_names=["王建华"])[0] == "〔姓名〕"


def test_table_fragment_not_signature():
    """全量首跑误伤：表格碎片"管理""车辆""成品库"被当成署名行。"""
    assert _new("管理\n车辆\n成品库\n解 型") == "管理\n车辆\n成品库\n解 型"


def test_short_title_name():
    assert _new("何总在会上指出") == "〔姓名〕总在会上指出"


def test_units_numbered_consistently():
    out = _new("威海厂、泰安厂作了发言。威海厂经验值得推广。")
    assert out == "〔A厂〕、〔B厂〕作了发言。〔A厂〕经验值得推广。"


def test_business_data_keeps_unit():
    assert _new("销量达到52.3万箱，同比增长8.6%") == "销量达到〔数据〕万箱，同比增长〔数据〕%"


def test_year_not_treated_as_data():
    assert _new("2024年4月16日") == "2024年4月16日"


# --- 混合首批（5份）人工复核抓到的漏检，逐条做成回归 ---

def test_full_legal_company_name():
    out = _new("山东省泰安烟草物流有限责任公司成立于2015年")
    assert "泰安" not in out and "山东" not in out
    assert out.startswith("〔A省公司〕")


def test_province_bureau_keeps_level():
    assert _new("由湖南省烟草专卖局主导") == "由〔A省局〕主导"


def test_city_company_keeps_level():
    out = _new("长沙市烟草公司联合株洲市烟草公司")
    assert out == "〔A市公司〕联合〔B市公司〕"


def test_standalone_region_name():
    out = _new("地处长株潭两型社会试验区中心地带")
    assert "长株潭" not in out


def test_brand_names_masked():
    # 2026-10-04 口径变更：品牌能反推是哪家中烟，按单位名同等替换
    assert _new("完成黄金叶（天叶细支）开发") == "完成〔品牌〕（〔规格〕）开发"  # 2026-10-07 规格名也能反推品牌
    assert _new("玉溪品牌表现良好，南京品牌") == "〔品牌〕品牌表现良好，〔品牌〕品牌"
    assert _new("实现中华民族伟大复兴，发扬“泰山挑山工”精神") == "实现中华民族伟大复兴，发扬“泰山挑山工”精神"


def test_operational_counts_kept():
    assert _new("覆盖124个网点，配送时长由2.5小时缩短") == "覆盖124个网点，配送时长由2.5小时缩短"


def test_bare_name_caught_with_known_list():
    out = deidentify("王建华强调，要抓落实", known_names=["王建华"])[0]
    assert out == "〔姓名〕强调，要抓落实"


def test_harvest_from_title_signature_and_filename():
    from deidentify import harvest_names
    names = harvest_names([
        ("刘明同志作了报告\n王 建 华\n主要负责同志要抓", "2019年烟草 行业工作会 陈志强.md"),
    ])
    assert {"刘明", "王建华", "陈志强"} <= names
    assert "主要负责" not in names


def test_fu_title_not_swallowed_into_name():
    assert _new("赵文副局长作总结讲话") == "〔姓名〕副局长作总结讲话"


def test_si_short_title():
    assert _new("张司在培训班上讲话") == "〔姓名〕司在培训班上讲话"


def test_siji_not_a_name():
    assert _new("由方司机负责，王司法所配合") == "由方司机负责，王司法所配合"


# --- 个人历史交付物全量首跑（82份）抽出的误伤与漏检 ---

def test_quanju_chachu_not_names():
    assert _new("，全局性谋划。严肃查处。") == "，全局性谋划。严肃查处。"


def test_common_title_phrases_not_names():
    for s in ["党组书记", "项目经理", "安全部主任", "向客户经理"]:
        assert _new(s) == s


def test_public_figure_kept():
    assert _new("赵乐际同志多次强调") == "赵乐际同志多次强调"


def test_surname_only_fu_title():
    assert _new("徐副局长讲话") == "〔姓名〕副局长讲话"


def test_benchmark_unit_in_shanghai():
    out = _new("可参考上海烟草集团有限责任公司")
    assert "上海" not in out


def test_hubei_factories_caught():
    out = _new("襄阳卷烟厂、红安卷烟厂、恩施卷烟厂、三峡卷烟厂")
    assert not any(x in out for x in ["襄阳", "红安", "恩施", "三峡"])


def test_political_place_phrases_kept():
    assert _new("弘扬延安精神，重温遵义会议") == "弘扬延安精神，重温遵义会议"


def test_yanan_factory_still_caught():
    assert "延安" not in _new("以延安卷烟厂为试点")


def test_enterprise_standard_code():
    out = _new("基于Q/SZY 1073-2023《物流管理诊断程序》和GB/T 19580")
    assert "SZY" not in out and "GB/T 19580" in out


def test_county_ziyun():
    assert "紫云" not in _new("紫云经营业务用房项目")


def test_filename_and_body_share_codes(tmp_path, monkeypatch):
    import deidentify as d
    src = tmp_path / "src"
    src.mkdir()
    f = src / "附件6 宝鸡卷烟厂物流诊断.md"
    f.write_text("陕西中烟工业有限责任公司\n宝鸡卷烟厂物流诊断", encoding="utf-8")
    monkeypatch.setenv("KBRAG_ROOT", str(tmp_path))
    out = tmp_path / "out"
    assert d.main([str(out), str(f)]) == 0
    produced = [p for p in out.glob("*.md")]
    assert len(produced) == 1
    code = produced[0].stem.split("附件6 ")[1][:4]  # 例如〔A厂〕
    assert code in produced[0].read_text(encoding="utf-8")


def test_money_and_volume_still_replaced():
    assert _new("实现税利12.6亿元，销量8万箱") == "实现税利〔数据〕亿元，销量〔数据〕万箱"


def test_factory_abbreviation():
    """P3 机检实测抽到：“以高质量建设现代化南烟为目标”。"""
    assert "南烟" not in _new("以高质量建设现代化南烟为目标")


def test_abbreviation_lookalikes_kept():
    assert _new("南烟区烟叶质量好，马上烟叶收购") == "南烟区烟叶质量好，马上烟叶收购"


def test_ambiguous_abbreviations_need_institution_suffix():
    """个人历史交付物实测误伤：仓库作业"上烟口"、"正常烟箱"、"雄安烟…"。"""
    for s in ["人工备货上烟口屏幕太小", "增大上烟信息字体", "回收烟箱/正常烟箱"]:
        assert _new(s) == s, s
    # 雄安本身是地名（应编码），这里只验证"安烟"简称规则没有误触发
    assert "〔某厂〕" not in _new("对雄安烟草市场调查")
    assert "上烟" not in _new("上烟集团坚决执行") and "龙烟" not in _new("龙烟物流制度文件")


# --- r6 文件名漏检（表外地名）+ 同名常用词/品牌 ---

def test_hebei_guangxi_jiangsu_units():
    for s in ["唐山烟草物流中心管理诊断报告", "承德烟草物流中心", "沧州烟草物流中心", "衡水烟草物流中心",
              "邢台烟草物流中心", "雄安烟草物流中心", "玉林烟草管理诊断报告", "南通烟滤嘴有限责任公司"]:
        out = _new(s)
        assert not any(c in out for c in ["唐山", "承德", "沧州", "衡水", "邢台", "雄安", "玉林", "南通"]), out


def test_place_names_that_are_common_words_kept():
    for s in ["各位来宾，同志们", "年日照时数充足", "三明治", "发展朝阳产业", "四平八稳", "长治久安",
              "大同小异", "孙中山"]:
        assert _new(s) == s, s


def test_ambiguous_place_with_institution_coded():
    assert "玉溪" not in _new("玉溪卷烟厂") and "日照" not in _new("日照市烟草公司")


def test_company_without_place_prefix():
    out = _new("对标红塔烟草集团，学习红塔山品牌经验")
    assert out == "对标〔某企业〕烟草集团，学习〔品牌〕品牌经验"  # 品牌按 2026-10-04 口径一并替换


# --- r7 残留扫描（2026-09-30）抽到的整类漏网，逐类做成回归 ---

def test_member_list_names():
    assert _new("诊断组成员：王一凡、曹文静 指导老师：陈立新") == "诊断组成员：〔姓名〕、〔姓名〕 指导老师：〔姓名〕"


def test_role_word_with_spaces_and_inspector():
    assert _new("诊断员：史国平  组  长：黄明") == "诊断员：〔姓名〕  组  长：〔姓名〕"


def test_personnel_table_row():
    assert _new("项目实施 黄子轩 男 本科 政工师") == "项目实施 〔姓名〕 男 本科 政工师"


def test_known_name_with_inner_spaces():
    assert deidentify("运行线：邹  岚（计划处）", known_names=["邹岚"])[0] == "运行线：〔姓名〕（计划处）"


def test_rare_surname_caught_in_list():
    assert "阚" not in _new("业务联系人：阚志远")


def test_same_factory_full_and_short_share_code():
    out = _new("南阳卷烟厂与南阳厂，另有许昌卷烟厂")
    assert out == "〔A厂〕与〔A厂〕，另有〔B厂〕"


def test_county_level_places_and_landmarks():
    for text in ["同德县", "绥芬河市", "贵安新区", "金沙江、雅砻江", "以宁乡片区为例", "王林市局（公司）"]:
        assert "〔某地〕" in _new(text), text


def test_autonomous_prefecture_does_not_eat_brackets():
    assert _new("〔癸地〕藏族自治州同德县和果洛藏族自治州") == "〔癸地〕〔某自治州〕〔某地〕和〔某地〕〔某自治州〕"


def test_province_abbr_direction():
    assert _new("烟草滇东南工商区域物流中心") == "烟草〔某区域〕工商区域物流中心"
    assert _new("〔乙地〕粤东要保持打假力度") == "〔乙地〕〔某区域〕要保持打假力度"


def test_abbr_direction_lookalikes_kept():
    assert _new("京东物流、新中国成立、渠道县级市场") == "京东物流、新中国成立、渠道县级市场"


def test_surname_title_after_conjunction():
    assert _new("重大任务和凌局长在讲话中") == "重大任务和〔姓名〕局长在讲话中"


# --- r8 复查（2026-10-03）抽到的漏网 ---

def test_province_abbr_in_doc_numbers_and_platforms():
    assert _new("《实施方案》（陕烟工办〔2024〕3号）") == "《实施方案》（〔某省〕烟工办〔文号〕）"  # 2026-10-07 年份序号一并打码
    assert "黔" not in _new("《意见》（黔府发〔2019〕12号）")
    assert "渝" not in _new("以“智慧渝烟”为基础平台")


def test_brand_and_common_words_not_masked_as_province():
    # 品牌按 2026-10-04 口径替换成〔品牌〕，但不得被当成省份简称替换成〔某省〕
    assert _new("苏烟、云烟、贵烟品牌") == "〔品牌〕、〔品牌〕、〔品牌〕品牌"
    assert _new("一缕青烟，黑烟排放") == "一缕青烟，黑烟排放"


def test_letter_spaced_cover_unit_is_caught():
    out = _new("衡 水 烟 草 专 卖 局 （ 公 司 ）")
    assert "衡" not in out and "水" not in out


def test_letter_spaced_table_fragment_kept():
    assert _new("条 的 简 款 通 化 预 知") == "条 的 简 款 通 化 预 知"


def test_known_name_with_title_keeps_title():
    out = deidentify("落实凌局长思考，刚才志成同志传达", known_names=["凌局长", "志成同志"])[0]
    assert out == "落实〔姓名〕局长思考，刚才〔姓名〕同志传达"


def test_rare_char_name_in_private_use_area():
    # 生僻字转写成私用区字符的人名（r9 实测“徐”+U+E052），姓 + 私用区字整体替换
    text, _, _ = deidentify("副局长徐\ue052同志亲临会议，徐\ue052副局长讲话")
    assert "\ue052" not in text and "徐" not in text
    assert text.count("〔姓名〕") == 2


def test_scan_flags_rare_char_name_in_filename_and_body(tmp_path):
    import deid_scan
    (tmp_path / "〔姓名〕徐\ue052同志的发言.md").write_text("正文徐\ue052副局长强调。", encoding="utf-8")
    hard, _, _ = deid_scan.scan(tmp_path)
    assert {h["type"] for h in hard} == {"生僻字人名残留（文件名）", "生僻字人名残留（正文）"}


# --- 2026-10-07 r10→r11（B-20261007-AR-02 标注者报出的漏网与工具缺陷），每条规则一正一反 ---
# 例句里的人名、单位名均为虚构

from deidentify import r11_rules, unit_letters


def _r11(text, specs=()):
    return r11_rules(text, specs)[0]


def test_unit_letters_past_z():
    assert [unit_letters(i) for i in (0, 25, 26, 27, 51, 52)] == ["A", "Z", "AA", "AB", "AZ", "BA"]


def test_unit_code_no_overflow_after_26_units():
    text = "、".join(f"{c}卷烟厂" for c in d_cities(28))
    out = _new(text)
    assert "〔AA厂〕" in out and "〔AB厂〕" in out
    assert not any(ch in out for ch in "[\\]^_`")


def d_cities(n):
    import deidentify as d
    return [c for c in d.CITIES if len(c) == 2][:n]


def test_overflow_placeholder_repaired_and_letters_kept():
    assert _r11("〔[中烟〕、〔\\厂〕、〔c公司〕、〔d省公司〕") == "〔AA中烟〕、〔AB厂〕、〔AI公司〕、〔AJ省公司〕"
    assert _r11("〔A中烟〕、〔Z厂〕") == "〔A中烟〕、〔Z厂〕"


def test_jishi_not_eaten_by_surname_rule():
    assert _new("发现不合格品及时处置，数据及时处理") == "发现不合格品及时处置，数据及时处理"
    assert _new("有3项达到先进，17项处于平均水平") == "有3项达到先进，17项处于平均水平"
    # 反例：真正的“姓 + 处”简称仍要换
    assert _new("请和王处联系") == "请和〔姓名〕处联系"


def test_mobile_number():
    assert _r11("（联系人：〔姓名〕，联系电话：13912345678）") == "（联系人：〔姓名〕，联系电话：〔手机号〕）"
    assert _r11("电话：139 1234 5678") == "电话：〔手机号〕"
    # 反例：日期串、长编号、带区号固话不动
    for s in ["编号20240311123456", "立项号 2024103112", "0851-12345678"]:
        assert _r11(s) == s, s


def test_name_list_spaced_after_placeholders():
    assert _r11("副组长：〔姓名〕、〔姓名〕、柳  谷、尤 飞") == "副组长：〔姓名〕、〔姓名〕、〔姓名〕、〔姓名〕"
    assert _r11("组  员：苗晓军  〔姓名〕  柏 辉") == "组  员：〔姓名〕  〔姓名〕  〔姓名〕"


def test_name_list_with_unit_annotation():
    assert _r11("成  员：〔姓名〕（〔H市局〕）、骆春花（〔F局〕）") == "成  员：〔姓名〕（〔H市局〕）、〔姓名〕（〔F局〕）"
    # 姓被留下、名被地名规则吃掉：“张〔戊地〕”
    assert _r11("成  员：〔姓名〕（〔H市局〕）、张〔戊地〕（〔I局〕）") == "成  员：〔姓名〕（〔H市局〕）、〔姓名〕（〔I局〕）"


def test_department_colon_list_and_non_names_kept():
    assert _r11("省局物流处：芮向辉、鞠红娟。") == "省局物流处：〔姓名〕、〔姓名〕。"
    assert _r11("参与人：处室领导、〔姓名〕、曹小波。") == "参与人：处室领导、〔姓名〕、〔姓名〕。"
    # 反例：冒号后是业务词，不是人名
    for s in ["财务部：安全、质量、成本", "组长：由分管领导担任", "参与人：处室领导"]:
        assert _r11(s) == s, s


def test_continuation_and_author_lines():
    assert _r11("申小龙  卓家森  穆红科  〔姓名〕") == "〔姓名〕  〔姓名〕  〔姓名〕  〔姓名〕"
    assert _r11("〔姓名〕 〔姓名〕 郜宏伟《物流诊断方法》在《某刊》发表") == "〔姓名〕 〔姓名〕 〔姓名〕《物流诊断方法》在《某刊》发表"
    # 反例：没有〔姓名〕打底的普通行、只有一个单元的行不动
    for s in ["安全  质量  成本", "〔姓名〕 同志讲话"]:
        assert _r11(s) == s, s


def test_bracket_annotated_name_rows():
    assert _r11("周某君（〔丙地〕）  张  斌（〔丁地〕）") == "〔姓名〕（〔丙地〕）  〔姓名〕（〔丁地〕）"
    assert _r11("管理（试行）  安全（暂行）") == "管理（试行）  安全（暂行）"


def test_title_before_name():
    assert _r11("小组由局长（经理）蒋某民担任组长，副经理孟某新担任副组长") == "小组由局长（经理）〔姓名〕担任组长，副经理〔姓名〕担任副组长"
    assert _r11("由主任委员负责，经理负责制") == "由主任委员负责，经理负责制"


def test_surname_with_full_title_after_particle():
    assert _r11("在国家局特别是李局长的指导下，饱含了李局长的心血") == "在国家局特别是〔姓名〕局长的指导下，饱含了〔姓名〕局长的心血"
    # 反例：“向书记汇报”的向是介词；“全局长期”不是人
    assert _r11("，向书记汇报，，全局长期稳定") == "，向书记汇报，，全局长期稳定"


def test_personnel_table_spaced_name_and_new_surnames():
    assert _r11("傅某天 男 本科 经济师") == "〔姓名〕 男 本科 经济师"
    assert _r11("洪 波 男 硕士 工程师") == "〔姓名〕 男 硕士 工程师"
    assert _r11("安全 男 女 比例") == "安全 男 女 比例"


def test_workshop_named_after_person():
    assert _r11("以“邵某工匠室”为主阵地，建立了邵某铭技能大师工作室，建立张某物流创新工作室") == \
        "以“〔姓名〕工匠室”为主阵地，建立了〔姓名〕技能大师工作室，建立〔姓名〕物流创新工作室"
    for s in ["建立了技术创新工作室", "以“安全生产工匠室”为载体", "建设科学家工作室"]:
        assert _r11(s) == s, s


def test_abbreviation_definition_follows_placeholder():
    out = _r11("〔c公司〕（简称安泰物流）是控股企业。图23 安泰物流网络")
    assert "安泰" not in out and out.count("〔AI公司〕") == 3
    # 反例：普通术语的简称不动
    s = "生产经营管理一体化平台（简称一体化平台）建设"
    assert _r11(s) == s


def test_brand_spec_names():
    assert _r11("新开发的〔品牌〕（中支凌云）、〔品牌〕(硬奇景)") == "新开发的〔品牌〕（〔规格〕）、〔品牌〕(〔规格〕)"
    # 同文其他位置的规格名一并替换（括号或引号里）
    assert _r11("〔品牌〕（海韵）好评。\n（ 海韵 ）商销增长") == "〔品牌〕（〔规格〕）好评。\n（〔规格〕 ）商销增长"
    # 批次级规格名：引号里、“培育”后
    assert _r11("举办“起源”陈列大赛，培育起源时", specs={"起源"}) == "举办“〔规格〕”陈列大赛，培育〔规格〕时"
    # 反例：通用包装词保留；规格名作普通词时不动
    assert _r11("〔品牌〕（硬）、〔品牌〕（细支）") == "〔品牌〕（硬）、〔品牌〕（细支）"
    assert _r11("良好运行，起源于", specs={"好运", "起源"}) == "良好运行，起源于"
    assert _r11("优化〔品牌〕1929研发") == "优化〔品牌〕〔规格〕研发"


def test_context_brands():
    assert _r11("中南海(5mg)、王冠（原味1号）、中华专线、中华牌卷烟、短支前门烟标") == \
        "〔品牌〕(〔规格〕)、〔品牌〕（〔规格〕）、〔品牌〕专线、〔品牌〕牌卷烟、短支〔品牌〕烟标"
    for s in ["中华民族伟大复兴", "长城脚下", "王冠上的明珠", "前门大街"]:
        assert _r11(s) == s, s


def test_province_abbreviation_combinations():
    assert _r11("充分利用滇桂、苏桂战略合作平台，浙桂合作生产平台") == "充分利用〔某区域〕、〔某区域〕战略合作平台，〔某区域〕合作生产平台"
    assert _r11("与前川渝中烟互设") == "与前〔某中烟〕互设"
    assert _r11("销售鲁产烟，鄂产品规6个") == "销售〔某省〕产烟，〔某省〕产品规6个"
    assert _r11("传承闽烟文化，开展闽商营销，提供浙烟智慧") == "传承〔某省〕烟文化，开展〔某省〕商营销，提供〔某省〕烟智慧"
    assert _r11("黔中城市群建设") == "〔某区域〕城市群建设"
    # 反例：京津冀、新产品规范、国产烟、云贵高原（无合作语境）
    for s in ["京津冀协同发展", "新产品规范", "国产烟", "云贵高原", "苏宁易购"]:
        assert _r11(s) == s, s


def test_latin_province_abbreviation():
    assert _r11("SX中烟工业有限责任公司") == "〔某省〕中烟工业有限责任公司"
    assert _r11("XX中烟物流、XXX烟草物流、〔AA中烟〕") == "XX中烟物流、XXX烟草物流、〔AA中烟〕"


def test_ocr_split_province_zhongyan_keeps_lines():
    out = _r11("重要支撑。广\n\n\n\n西中烟探索建设")
    assert out == "重要支撑。〔某中烟〕\n\n\n\n探索建设"
    assert _r11("〔癸地〕红塔\n卷烟有限责任公司") == "〔癸地〕〔某企业〕\n卷烟有限责任公司"
    assert _r11("广西\n壮族") == "广西\n壮族"  # 不接“中烟”的不动（广西由 PLACE_RE 处理）


def test_rivers_mountains_and_region_piece():
    assert _r11("以乌江流域、娄山山脉等为重点，打造中南片区物流中心") == "以〔某流域〕、〔某山脉〕等为重点，打造〔某片区〕物流中心"
    for s in ["长江流域", "黄河流域生态保护", "全省物流域核心系统", "西南地区"]:
        assert _r11(s) == s, s


def test_town_and_station_names():
    assert _r11("〔某地〕东南部（甲场、乙武、丙堡），〔某地〕西南部（白云、十字）") == \
        "〔某地〕东南部（〔某地〕、〔某地〕、〔某地〕），〔某地〕西南部（〔某地〕、〔某地〕）"
    assert _r11("完成十字、白云、黄土等标准化烟叶站的维修") == "完成〔某地〕、〔某地〕、〔某地〕等标准化烟叶站的维修"
    assert _r11("完成〔某地〕区新场烟叶站征收") == "完成〔某地〕区〔某地〕烟叶站征收"
    # 反例：没有已脱敏地名打底的普通列表
    for s in ["（党委、纪委、工会）", "合理优化烟叶站点布局", "完成安全、质量等标准化建设"]:
        assert _r11(s) == s, s


def test_place_enumeration_with_masked_neighbor():
    assert _r11("调查地点为金牛区、〔某地〕以及新郑、巩义等地区") == "调查地点为〔某地〕、〔某地〕以及〔某地〕、〔某地〕等地区"
    assert _r11("城区、青县、〔某地〕、沧县") == "城区、〔某地〕、〔某地〕、〔某地〕"
    assert _r11("选定了〔甲地〕、中山、〔丁地〕") == "选定了〔甲地〕、〔某地〕、〔丁地〕"
    assert _r11("高新区、经开区、〔某地〕") == "高新区、经开区、〔某地〕"
    assert _r11("全县、各区、乡镇") == "全县、各区、乡镇"


def test_doc_number_year_and_sequence():
    assert _r11("（〔某省〕烟工办〔2024〕58号）") == "（〔某省〕烟工办〔文号〕）"
    assert _r11("国务院出台国发〔2022〕2号文件，支持〔丁地〕发展") == "国务院出台国发〔文号〕文件，支持〔丁地〕发展"
    # 反例：国家局文号、无地名同句的国务院文号不动
    for s in ["（国烟办〔2019〕126号）", "国发〔2022〕2号文件精神"]:
        assert _r11(s) == s, s


def test_scale_numbers_keyword_anchored():
    assert _r11("累计查处案件1410起，其中大要案件119起") == "累计查处案件〔数据〕起，其中大要案件〔数据〕起"
    assert _r11("全省库存周转次数最低为〔乙地〕18.07次，最高为〔甲地〕23.07次。") == \
        "全省库存周转次数最低为〔乙地〕〔数据〕次，最高为〔甲地〕〔数据〕次。"
    assert _r11("现有员工15000多人，占地面积1213亩，待开发400余亩土地") == "现有员工〔数据〕多人，占地面积〔数据〕亩，待开发〔数据〕余亩土地"
    assert _r11("总资产规模达到25亿；合同金额下降2000余万元；出口总额1亿美元；排放2.56克/箱") == \
        "总资产规模达到〔数据〕亿；合同金额下降〔数据〕余万元；出口总额〔数据〕亿美元；排放〔数据〕克/箱"
    # 反例：2026-09-25 拍板的运营计数照留；“使用工作条例”不是用工；时长、座谈次数不算规模
    for s in ["覆盖124个网点，配送时长由2.5小时缩短", "使用工作条例》等6项", "零售客户的办证时间由24个工作日缩短",
              "员工层座谈 15 次", "2023年5月10日", "检查卷烟零售户1234户次", "每个县级局至少破获1起烟叶网络案件",
              "从卷烟零售客户中选取220户"]:
        assert _r11(s) == s, s


def test_gov_url_softreg_aid_phrase():
    assert _r11("见 http://www.hunan.gov.cn/a/b.html") == "见 〔网址〕"
    assert _r11("登记号：2024SR0752373。") == "登记号：〔登记号〕。"
    assert _r11("技术援藏项目，向〔丁地〕推广") == "技术援〔某省〕项目，向〔丁地〕推广"
    for s in ["http://www.gov.cn/zhengce", "做好援藏工作"]:
        assert _r11(s) == s, s


def test_typed_entries_in_names_file(tmp_path):
    from deidentify import load_names_file
    f = tmp_path / "names_confirmed.txt"
    f.write_text("# 注释\n王某某\n〔某企业〕某某信\n", encoding="utf-8")
    items = load_names_file(f)
    assert items == [("王某某", None), ("某某信", "〔某企业〕")]
    out = deidentify("某某信公司派出王 某某", known_names=items)[0]
    assert out == "〔某企业〕公司派出〔姓名〕"


def test_r11_rules_idempotent_and_keep_line_count():
    text = ("副组长：〔姓名〕、柳  谷\n联系电话：13912345678\n〔[中烟〕与鲁产烟\n"
            "累计查处案件1410起\n〔品牌〕（中支凌云）\n广\n\n西中烟")
    once = _r11(text)
    assert once.count("\n") == text.count("\n")
    assert r11_rules(once)[1] == []


def test_scan_reports_r11_leaks_and_rejects_empty_dir(tmp_path):
    import deid_scan
    (tmp_path / "a.md").write_text("联系电话：13912345678\n副组长：〔姓名〕、柳  谷\n及〔姓名〕处置", encoding="utf-8")
    hard, _, _ = deid_scan.scan(tmp_path)
    kinds = {h["type"] for h in hard}
    assert {"手机号（正文）", "人名(名单)（正文）", "人名规则误伤"} <= kinds
    empty = tmp_path / "empty"
    empty.mkdir()
    assert deid_scan.main([str(empty)]) == 2
    assert deid_scan.main([str(tmp_path / "missing")]) == 2
    assert deid_scan.main([str(tmp_path)]) == 1


def test_number_split_from_unit_across_lines():
    assert _r11("工商共库入库卷烟67.71\n万箱，出库") == "工商共库入库卷烟〔数据〕\n万箱，出库"
    assert _r11("建成2号库\n仓库面积") == "建成2号库\n仓库面积"
    assert _r11("标杆值 7.67\n万箱终端送货配送费用") == "标杆值 7.67\n万箱终端送货配送费用"
    assert _r11("第三章\n2024年") == "第三章\n2024年"


# ---- 2026-10-07 r11 独立核查补的规则：漏网与误伤 ----

def test_audit_crossline_city_and_brand():
    assert _r11("全省标杆值（秦皇\n岛）高了") == "全省标杆值（〔某地〕\n）高了"
    assert _r11("其中〔品牌〕\n(夜西湖)〔数据〕%、红\n河(软 99)〔数据〕%") == "其中〔品牌〕\n(〔规格〕)〔数据〕%、〔品牌〕\n(〔规格〕)〔数据〕%"
    # 反例：二字地名不做跨行（“确定\n州市”之类会误伤）；普通词跨行不动
    assert _r11("确定\n州市") == "确定\n州市"
    assert _r11("红\n色文化") == "红\n色文化"


def test_audit_more_context_brands_and_specs():
    assert _r11("长城(醇雅薄荷)〔数据〕%、金桥（蓝牌）75 件") == "〔品牌〕(〔规格〕)〔数据〕%、〔品牌〕（〔规格〕）75 件"
    assert _r11("雪茄细支荷花出库", specs={"荷花"}) == "雪茄细支〔规格〕出库"
    assert _r11("创新打造泰山微课，实现“泰山梦”") == "创新打造〔品牌〕微课，实现“〔品牌〕梦”"
    for s in ["长城脚下", "荷花池", "泰山挑山工", "金桥工程", "生命重于泰山"]:
        assert _r11(s, specs={"荷花"}) == s, s


def test_audit_county_places_and_political_phrases():
    assert _r11("〔M中烟〕井冈山卷烟厂") == "〔M中烟〕〔某地〕卷烟厂"
    assert _r11("在平山、井陉、赞皇、行唐、灵寿、元氏 6 个山区") == "在〔某地〕、〔某地〕、〔某地〕、〔某地〕、〔某地〕、〔某地〕 6 个山区"
    assert _r11("髙碑店对接点 2 2") == "〔某地〕对接点 2 2"
    for s in ["弘扬井冈山精神", "无极限", "创新乐园"]:
        assert _r11(s) == s, s


def test_audit_scale_misfires_fixed():
    # 概念计数、奖项专利、比率、机构名、顿号后的下一项、目标数，不是规模数
    for s in ["从成本和资产管理5个维度评价，再将5个维度的指数加权",
              "获得职工优秀创新成果奖1项，科技进步奖1项",
              "将零售户细分为124个小类",
              "实现案件查办率和举报处理率2个100%",
              "被国家烟草职工培训中心选定为全行业2个信用监管案例之一",
              "万名从业人员高价值发明专利拥有量0件",
              "出入库操作工3人，备用工2人，带班长1人",
              "确定重点改善点31个，包括营销5个、物流13个、专卖8个、烟农服务4个",
              "每个市州局破获1起假烟网络案件、1起真品卷烟案件和1—2起互联网涉烟重点案件，全省破获1—2起督办案件。"]:
        assert _r11(s) == s, s
    # 正例不受影响
    assert _r11("查办1410起案件；物流从业人员494名，其中管理人员85名") == "查办〔数据〕起案件；物流从业人员〔数据〕名，其中管理人员〔数据〕名"
