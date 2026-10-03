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


def test_brand_names_kept():
    assert _new("完成黄金叶（天叶细支）开发") == "完成黄金叶（天叶细支）开发"


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
              "大同小异", "孙中山", "玉溪品牌表现良好", "南京品牌"]:
        assert _new(s) == s, s


def test_ambiguous_place_with_institution_coded():
    assert "玉溪" not in _new("玉溪卷烟厂") and "日照" not in _new("日照市烟草公司")


def test_company_without_place_prefix():
    out = _new("对标红塔烟草集团，学习红塔山品牌经验")
    assert "红塔烟草" not in out and "红塔山" in out


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
    assert _new("《实施方案》（陕烟工办〔2024〕3号）") == "《实施方案》（〔某省〕烟工办〔2024〕3号）"
    assert "黔" not in _new("《意见》（黔府发〔2019〕12号）")
    assert "渝" not in _new("以“智慧渝烟”为基础平台")


def test_brand_and_common_words_not_masked_as_province():
    assert _new("苏烟、云烟、贵烟品牌") == "苏烟、云烟、贵烟品牌"
    assert _new("一缕青烟，黑烟排放") == "一缕青烟，黑烟排放"


def test_letter_spaced_cover_unit_is_caught():
    out = _new("衡 水 烟 草 专 卖 局 （ 公 司 ）")
    assert "衡" not in out and "水" not in out


def test_letter_spaced_table_fragment_kept():
    assert _new("条 的 简 款 通 化 预 知") == "条 的 简 款 通 化 预 知"


def test_known_name_with_title_keeps_title():
    out = deidentify("落实凌局长思考，刚才志成同志传达", known_names=["凌局长", "志成同志"])[0]
    assert out == "落实〔姓名〕局长思考，刚才〔姓名〕同志传达"
