"""De-identification pass for corpus text (CLAUDE.md §4.2, 11章 P2.3).

Rules-based first pass, three categories:
  单位名   place name + institution suffix -> 〔A厂〕〔B局〕…  (numbered per document, decision 11章§五②)
  经营数据 number + business unit            -> 〔数据〕万箱 … (unit kept: 量纲与对比关系保留)
  人名     common surname + given name next to a title, or a standalone signature line

Known gap: a bare name not adjacent to a title word (e.g. "王建华强调") is NOT caught —
there is no NER model here. Output must be human-reviewed before anything leaves the machine.

CLI: python deidentify.py OUT_DIR FILE [FILE ...]
Writes de-identified copies + deid_changes.jsonl (contains ORIGINAL names — local only, gitignored).
Never writes into 10_source.
"""

import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import common

# 全国地级市（2026-09-25 由零散补表改为全量：r6 文件名里唐山/承德/沧州/衡水/邢台/雄安/玉林/南通
# 八处漏检，此前几轮残留检查都用同一张表扫，表外地名永远扫不出来）
CITIES = """
石家庄 唐山 秦皇岛 邯郸 邢台 保定 张家口 承德 沧州 廊坊 衡水 雄安 定州 辛集 高碑店
太原 阳泉 晋城 朔州 晋中 运城 忻州 临汾 吕梁
呼和浩特 包头 乌海 赤峰 通辽 鄂尔多斯 呼伦贝尔 巴彦淖尔 乌兰察布
沈阳 大连 鞍山 抚顺 本溪 丹东 锦州 营口 阜新 辽阳 盘锦 铁岭 葫芦岛
长春 辽源 通化 松原 白城 延边 延吉
哈尔滨 齐齐哈尔 鸡西 鹤岗 双鸭山 大庆 伊春 佳木斯 七台河 牡丹江 黑河 绥化
无锡 徐州 常州 苏州 南通 连云港 淮安 淮阴 盐城 扬州 镇江 泰州 宿迁 宜兴
杭州 宁波 温州 嘉兴 湖州 绍兴 金华 衢州 舟山 台州 丽水
合肥 芜湖 蚌埠 淮南 马鞍山 淮北 铜陵 安庆 滁州 阜阳 宿州 六安 亳州 池州 宣城
福州 厦门 莆田 泉州 漳州 南平 龙岩 宁德
南昌 景德镇 萍乡 九江 新余 鹰潭 赣州 吉安 宜春 抚州 上饶 广丰 瑞金
济南 青岛 淄博 枣庄 东营 烟台 潍坊 济宁 泰安 威海 临沂 德州 聊城 滨州 菏泽 滕州
郑州 开封 洛阳 平顶山 安阳 鹤壁 新乡 焦作 濮阳 许昌 漯河 三门峡 南阳 商丘 信阳 周口 驻马店 济源
武汉 黄石 十堰 宜昌 襄阳 襄樊 鄂州 荆门 孝感 荆州 黄冈 咸宁 随州 恩施 仙桃 潜江 天门 三峡 红安 广水
长沙 株洲 湘潭 衡阳 邵阳 岳阳 常德 张家界 益阳 郴州 永州 怀化 娄底 湘西 吉首 零陵
广州 韶关 深圳 珠海 汕头 佛山 江门 湛江 茂名 肇庆 惠州 梅州 汕尾 河源 阳江 清远 东莞 潮州 揭阳 云浮 南雄
南宁 柳州 桂林 梧州 北海 防城港 钦州 贵港 玉林 百色 贺州 河池 崇左
海口 三亚
成都 自贡 攀枝花 泸州 德阳 绵阳 广元 遂宁 内江 乐山 南充 眉山 宜宾 广安 达州 雅安 巴中 资阳 凉山 甘孜 阿坝 西昌 什邡
黔江 涪陵 万州
贵阳 六盘水 遵义 安顺 毕节 铜仁 黔西南 黔东南 黔南 紫云 贵定
昆明 曲靖 保山 昭通 丽江 临沧 楚雄 文山 西双版纳 大理 德宏 怒江 迪庆 会泽
西安 铜川 宝鸡 咸阳 渭南 延安 汉中 榆林 商洛 旬阳 澄城
兰州 嘉峪关 金昌 天水 武威 张掖 平凉 酒泉 庆阳 定西 陇南 临夏 甘南
西宁 海东 银川 石嘴山 固原 中卫 乌鲁木齐 克拉玛依 吐鲁番 哈密 拉萨
北京 上海 天津 重庆
""".split()
# 同时是常用词/品牌/人名的地名：只在后接机构词（卷烟厂/烟草公司…）时替换，单独出现不动。
# 各位来宾、日照时数、三明治、朝阳产业、四平八稳、长治久安、大同小异、白银饰品、吴忠（人名）、
# 玉溪/南京/红河/黄山（品牌，拍板不脱敏）、中山（孙中山）、安康、普洱（茶）、白山、吉林（省市同名，按省处理）
UNIT_ONLY = """来宾 日照 三明 朝阳 四平 长治 大同 白银 吴忠 玉溪 南京 红河 黄山 中山 安康 普洱 白山""".split()
REGIONS = ["长株潭", "粤桂", "梵净山"]  # 梵净山为地标，T2 复核漏检
PROVINCES = ["河北", "山西", "内蒙古", "辽宁", "吉林", "黑龙江", "江苏", "浙江", "安徽", "福建", "江西",
             "山东", "河南", "湖北", "湖南", "广东", "广西", "海南", "四川", "贵州", "云南", "西藏",
             "陕西", "甘肃", "青海", "宁夏", "新疆", "重庆"]
PLACES = sorted(set(PROVINCES + CITIES + REGIONS), key=len, reverse=True)          # 单独出现也替换
UNIT_PLACES = sorted(set(PLACES + UNIT_ONLY), key=len, reverse=True)               # 后接机构词才替换
# 后缀 -> 层级标签（CLAUDE.md §4.2：单位名脱敏但保留行政层级）
SUFFIX_LEVEL = [
    ("有限责任公司", "公司"), ("烟草公司", "公司"), ("分公司", "公司"), ("公司", "公司"),
    ("烟草专卖局", "局"), ("专卖局", "局"), ("市局", "局"), ("县局", "局"), ("局", "局"),
    ("卷烟厂", "厂"), ("厂", "厂"), ("物流中心", "中心"), ("中心", "中心"),
    ("物流园", "园区"), ("中烟", "中烟"),
]
LEVEL_OF = dict(SUFFIX_LEVEL)
# 卷烟品牌不脱敏（2026-09-25 拍板；2026-09-30 复议维持：已知“贵烟”“泰山”等品牌可反推省份，仍不脱敏，
# deid_scan 不把品牌列为漏网）。

SURNAMES = ("王李张刘陈杨黄赵吴周徐孙马朱胡郭何高林罗郑梁谢宋唐许韩冯邓曹彭曾肖田董袁潘"
            "于蒋蔡余杜叶程苏魏吕丁任沈姚卢姜崔钟谭陆汪范金石廖贾夏韦付方白邹孟熊秦邱江"
            "尹薛闫段雷侯龙史陶黎贺顾毛郝龚邵万钱严覃武戴莫孔向汤常温康施文牛樊葛邢安齐易乔伍庞颜倪庄聂章鲁岳翟殷詹申欧耿关兰焦俞左柳甘祝包宁尚符舒阮柯纪梅童凌毕单季裴霍涂成苗谷盛曲翁冉骆蓝路游辛靳管柴蒙鲍华喻祁蒲房滕屈饶解牟艾尤阳时穆农司卓古吉缪简车项连芦麦褚娄窦戚岑景党宫费卜冷晏席卫米柏宗瞿桂全佟应臧闵苟邬边卞姬师和仇栾隋商刁沙荣巫寇桑郎甄丛仲虞敖巩明佘池查麻苑迟邝阚郜茹訾眭隗蔺郗")  # 阚郜茹：r7 名单里的真名，原表缺
TITLES = ["副总经理", "总经理", "董事长", "秘书长", "副局长", "局长", "副厂长", "厂长",
          "副主任", "主任", "书记", "经理", "总监", "处长", "科长", "部长", "同志"]
SHORT_TITLES = ["副局长", "副主任", "副处长", "副厂长", "副总",  # 徐副局长 类（只有姓）
                "总", "局", "厂长", "处", "书记", "司"]  # 何总、李局、张司 类简称
GENERIC_BEFORE_TOUZHI = {"负责", "主要负责", "有关", "广大", "各位", "全体", "老", "相关", "分管", "年轻"}
# 个人历史交付物全量首跑（2026-09-25）的误伤，逐条收进停用表
SHORT_FP = {"全局", "查处", "高处", "何处", "时局", "党总", "万局", "成局", "方处"}
NAME_FP = {"党组", "党委", "项目", "安全部", "向客户", "全体", "全部", "成员", "管理", "高碑店"}
# 公开讲话引用的国家领导人不属于客户保密信息，删了还会破坏政治表述（05章红线1）
PUBLIC_FIGURES = {"习近平", "李强", "赵乐际", "王沪宁", "蔡奇", "丁薛祥", "李希",
                  "李克强", "栗战书", "汪洋", "韩正", "王岐山"}

UNIT_RE = re.compile(
    "(" + "|".join(UNIT_PLACES) + ")(省|市|县|区)?([一-龥]{0,8}?)("
    + "|".join(s for s, _ in SUFFIX_LEVEL) + ")")
# 延安精神/遵义会议/南昌起义 等固定政治表述不替换（05章红线1）
PLACE_RE = re.compile("(" + "|".join(PLACES) + ")(省|市|县|区)?(?!精神|会议|起义|整风|时期|道路)")
# 无地名前缀的烟草企业名（r7 结构扫描抽到）。品牌"红塔山"不动，只认后接烟草/集团/公司
COMPANY_RE = re.compile(r"(红塔|红云红河|红云|白沙|黄鹤楼|芙蓉王|娇子)(?=烟草|集团|公司|卷烟厂)")
# 卷烟厂简称（P3 机检实测时抽到"建设现代化南烟"漏检）。"贵烟"与品牌同名不收；
# 后接叶/草/丝/农/区/田/苗等时是"南烟区""上烟叶"之类，不是简称
# 独立出现即可认定的简称（实测："建设现代化南烟""许烟经验""昆烟制丝"）
LOOSE_ABBR = ["郑烟", "洛烟", "许烟", "南烟", "驻烟", "郴烟", "昆烟", "玉烟", "曲烟", "遵烟", "毕烟",
              "宝烟", "襄烟", "杭烟", "厦烟"]
# 有歧义、须后接机构词才算（实测误伤："人工上烟口""正常烟箱""雄安烟…"）
STRICT_ABBR = ["上烟", "常烟", "安烟", "长烟", "延烟", "汉烟", "宁烟", "龙烟"]
ABBR_RE = re.compile(
    "(?<![卷香吸抽戒])(?:(" + "|".join(LOOSE_ABBR) + ")(?![叶草丝农区田苗碱气花民站株箱])"
    "|(" + "|".join(STRICT_ABBR) + ")(?=集团|公司|厂|物流|工业))")
# 经营数据 = 销量/金额/比率类。运营计数（个/家/项/人/小时…）不算，保留原数字（2026-09-25 拍板）。
# 年/月/日不在列表里，日期不受影响
# 企业标准号的企业代码能直接对应到具体中烟公司（抽查发现 Q/SZY）；国标 GB/T、行标 YC/T 不动
QSTD_RE = re.compile(r"Q/[A-Z]{2,8}")
# r7 残留扫描（2026-09-30，deid_scan.py）抽到的县级地名、地标、OCR 错字。地名长尾靠“扫描候选 + 人工筛”
# 逐批补进这里，不指望一张表穷尽。两字县名一律带“县/市”后缀才认，避免误伤普通词。
EXTRA_PLACES = ["五峰县", "东光县", "滦平县", "湘阴县", "新化县", "水城县", "同德县", "龙里县", "河间县",
                "盐山县", "孟村县", "吴桥县", "澧县", "蠡县", "任丘县", "任丘市", "泊头市", "绥芬河市", "儋州",
                "红河州", "贵安新区", "郑东新区", "果洛", "宁乡", "北仑", "金沙江", "雅砻江", "安宁河", "鲁南山",
                "南流江", "翠湖宾馆", "王林", "涞源", "竹山", "竹溪", "日照四地市"]  # 王林 = 玉林的 OCR 错字（“王林市局”“大王林”）
EXTRA_PLACE_RE = re.compile("(?<![渠街频轨])道县|" + "|".join(sorted(EXTRA_PLACES, key=len, reverse=True)))
# “X自治州/自治县”（含民族名）：果洛藏族自治州、黔南布依族苗族自治州……
AUTONOMOUS_RE = re.compile(r"[^\s，。、；和与及〔〕]{0,4}?(?:[一-龥]{1,3}族){1,3}自治(?:州|县)")
# 省份简称 + 方位（滇东南、粤东、鲁南）：后接区域类词才认；京/沪/津/新不收（京东、新中国）
_ABBR_DIR = r"[滇黔豫湘鄂川渝桂粤闽赣皖鲁冀晋陕甘宁青藏蒙辽吉黑苏浙琼](?:东南|西南|东北|西北|东|南|西|北|中)"
# 后接区域类词才认；或紧跟在已替换的地名之后（“〔乙地〕粤东要……”）
ABBR_DIRECTION_RE = re.compile(
    "(?:(?<=〕)" + _ABBR_DIR + "|" + _ABBR_DIR + r"(?=工商|区域|片区|地区|一带|烟区|产区|[、，。；]))")
# 名单与人员表（r7 漏网约 90 个真名的两个语境）：
#   “诊断组成员：王一凡、曹文静”“指导老师：陈立新”——角色词后的冒号名单
#   “项目实施 黄子轩 男 本科 政工师”——姓名后紧跟性别的人员表行
ROLE_WORDS = ("成\\s*员|组\\s*长|副组长|组员|指导老师|老师|负责人|联系人|编写|编制|审核|批准|起草|执笔|撰稿|"
              "主持人|参与人员|项目经理|顾问|专家|讲师|记录人|汇报人|诊断员|评价员|审核员|内审员|调研员|联络员")
NAME_TOKEN = "[" + SURNAMES + "][一-龥]{1,2}"
NAME_LIST_RE = re.compile("((?:" + ROLE_WORDS + r")[：:]\s*)((?:" + NAME_TOKEN + r"[、，,\s]*)+)")
NAME_TABLE_RE = re.compile(r"(?<![一-龥])(" + NAME_TOKEN + r")(?=\s*[|\s]\s*[男女](?:[\s|]|$))")
DATA_RE = re.compile(
    r"\d+(?:\.\d+)?\s*(万箱|万条|亿支|万支|万元|亿元|万担|个百分点|百分点|%|％|箱|担|吨|元|万)")
NAME_TITLE_RE = re.compile(
    "(?<![一-龥])([" + SURNAMES + "])((?!副)[一-龥]{1,2}?)(" + "|".join(TITLES) + ")")  # 名字取短且不以"副"开头
SHORT_NAME_RE = re.compile(
    "(?:(?<![一-龥])|(?<=[和与及、]))([" + SURNAMES + "])(" + "|".join(SHORT_TITLES) + ")(?![体结部量额计裁统部监机法令空])")
SIGNATURE_RE = re.compile(r"^[" + SURNAMES + r"][ 　]*[一-龥](?:[ 　]*[一-龥])?$")


PLACE_CODES = "甲乙丙丁戊己庚辛壬癸"


FILENAME_NAME_RE = re.compile(
    r"(?:^|[ 　_\-—（(])([" + SURNAMES + r"][一-龥]{1,2})(?=$|[ 　_\-—）)]|同志|在|讲话|批示)")


def harvest_names(texts_and_names):
    """Pass 1: names seen next to a title / on a signature line / as a filename token."""
    names = set()
    for text, filename in texts_and_names:
        for m in NAME_TITLE_RE.finditer(text):
            cand = m.group(1) + m.group(2)
            if not (m.group(3) == "同志" and cand in GENERIC_BEFORE_TOUZHI):
                names.add(cand)
        for line in text.splitlines():
            s = line.strip()
            if s and SIGNATURE_RE.match(s):
                names.add(re.sub(r"[ 　]", "", s))
        names.update(m.group(1) for m in FILENAME_NAME_RE.finditer(Path(filename).stem))
    return names


def deidentify(text: str, known_names=()):
    changes, unit_map, place_map, key_map = [], {}, {}, {}
    for name in sorted(known_names, key=len, reverse=True):
        # 字间允许空白：PDF 转写常把“邹岚”排成“邹  岚”（r7 名单实测）
        rx = re.compile(r"[ 　]*".join(map(re.escape, name)))
        hits = rx.findall(text)
        if hits:
            changes.extend({"type": "人名(已知名单)", "orig": h, "new": "〔姓名〕"} for h in hits)
            text = rx.sub("〔姓名〕", text)

    def unit_repl(m):
        # 同一单位的全称与简称共用一个编号：“南阳卷烟厂/南阳厂”“河南中烟/河南中烟工业有限责任公司”
        # （r7 实测一份报告里同一个厂被编成〔A厂〕〔C厂〕两个号）。键 = 地名 + 行政级 + 去掉通用词的中缀 + 层级
        full = m.group(0)
        middle = m.group(3) or ""
        level = "中烟" if "中烟" in middle else LEVEL_OF[m.group(4)]
        key = (m.group(1), m.group(2) or "", re.sub("中烟|工业|卷烟|烟草|有限责任|专卖", "", middle), level)
        if key not in key_map:
            letter = chr(ord("A") + len(key_map))
            key_map[key] = f"〔{letter}{m.group(2) or ''}{level}〕"
        unit_map[full] = key_map[key]
        changes.append({"type": "单位名", "orig": full, "new": unit_map[full]})
        return unit_map[full]

    def place_repl(m):
        full = m.group(0)
        if full not in place_map:
            code = PLACE_CODES[len(place_map) % len(PLACE_CODES)]
            place_map[full] = f"〔{code}{m.group(2) or '地'}〕"
        changes.append({"type": "地名", "orig": full, "new": place_map[full]})
        return place_map[full]

    def data_repl(m):
        new = f"〔数据〕{m.group(1)}"
        changes.append({"type": "经营数据", "orig": m.group(0), "new": new})
        return new

    def name_repl(m):
        surname, given, title = m.groups()
        cand = surname + given
        if cand in NAME_FP or cand in PUBLIC_FIGURES or (title == "同志" and cand in GENERIC_BEFORE_TOUZHI):
            return m.group(0)
        new = f"〔姓名〕{title}"
        changes.append({"type": "人名", "orig": m.group(0), "new": new})
        return new

    def short_repl(m):
        if m.group(0) in SHORT_FP:
            return m.group(0)
        new = f"〔姓名〕{m.group(2)}"
        changes.append({"type": "人名(简称)", "orig": m.group(0), "new": new})
        return new

    # 署名行只认"去掉空格后恰为已确认姓名"——2026-09-25 全量首跑时，宽松规则把"管理""车辆"等
    # 表格碎片行当成署名，59 处只对 6 处。候选收集仍用 SIGNATURE_RE（见 harvest_names），替换只认名单。
    known_set = set(known_names)
    out = []
    for line in text.splitlines():
        stripped = line.strip()
        if stripped and re.sub(r"[ 　]", "", stripped) in known_set and re.search(r"[ 　]", stripped):
            changes.append({"type": "人名(署名行)", "orig": stripped, "new": "〔姓名〕"})
            out.append("〔姓名〕")
            continue
        def list_repl(m):
            names = re.sub(NAME_TOKEN, "〔姓名〕", m.group(2))
            if names != m.group(2):
                changes.append({"type": "人名(名单)", "orig": m.group(2).strip(), "new": names.strip()})
            return m.group(1) + names
        line = NAME_LIST_RE.sub(list_repl, line)
        for m in NAME_TABLE_RE.finditer(line):
            changes.append({"type": "人名(人员表)", "orig": m.group(1), "new": "〔姓名〕"})
        line = NAME_TABLE_RE.sub("〔姓名〕", line)
        line = UNIT_RE.sub(unit_repl, line)
        for m in COMPANY_RE.finditer(line):
            changes.append({"type": "企业名", "orig": m.group(0), "new": "〔某企业〕"})
        line = COMPANY_RE.sub("〔某企业〕", line)
        for m in ABBR_RE.finditer(line):
            changes.append({"type": "单位简称", "orig": m.group(0), "new": "〔某厂〕"})
        line = ABBR_RE.sub("〔某厂〕", line)
        line = PLACE_RE.sub(place_repl, line)
        for rx, tag, new in ((EXTRA_PLACE_RE, "地名(县级/地标)", "〔某地〕"), (AUTONOMOUS_RE, "地名(自治州县)", "〔某自治州〕"),
                             (ABBR_DIRECTION_RE, "地名(省简称方位)", "〔某区域〕")):
            for m in rx.finditer(line):
                changes.append({"type": tag, "orig": m.group(0), "new": new})
            line = rx.sub(new, line)
        line = DATA_RE.sub(data_repl, line)
        for m in QSTD_RE.finditer(line):
            changes.append({"type": "企标代号", "orig": m.group(0), "new": "Q/〔企业〕"})
        line = QSTD_RE.sub("Q/〔企业〕", line)
        line = NAME_TITLE_RE.sub(name_repl, line)
        line = SHORT_NAME_RE.sub(short_repl, line)
        out.append(line)
    return "\n".join(out), changes, unit_map


def main(argv):
    """python deidentify.py [--names NAMES.txt] [--harvest] OUT_DIR FILE ...
    --harvest  只做第一遍：收集姓名候选写到 OUT_DIR/names_candidates.txt，供人工核对后作 --names 用
    --names    第二遍：核对过的姓名名单（一行一个），在全批次里不论位置一律替换
    输出文件名也脱敏（原文件名常带讲话人姓名）。"""
    names_file, harvest_only = None, False
    while argv and argv[0].startswith("--"):
        flag = argv.pop(0)
        if flag == "--names":
            names_file = Path(argv.pop(0))
        elif flag == "--harvest":
            harvest_only = True
    out_dir, files = Path(argv[0]), [Path(f) for f in argv[1:]]
    source_root = (common.project_root() / "10_source").resolve()
    if out_dir.resolve() == source_root or source_root in out_dir.resolve().parents:
        print("拒绝写入 10_source")
        return 1
    out_dir.mkdir(parents=True, exist_ok=True)
    texts = [(p.read_text(encoding="utf-8"), p.name) for p in files]

    if harvest_only:
        cands = sorted(harvest_names(texts))
        (out_dir / "names_candidates.txt").write_text("\n".join(cands) + "\n", encoding="utf-8")
        print(f"姓名候选 {len(cands)} 个 -> {out_dir / 'names_candidates.txt'}（含真名，已 gitignore，人工核对后用 --names）")
        return 0

    known = []
    if names_file:
        known = [n.strip() for n in names_file.read_text(encoding="utf-8").splitlines() if n.strip()]
    used = set()
    with (out_dir / "deid_changes.jsonl").open("w", encoding="utf-8") as lf:
        for (text, name), p in zip(texts, files):
            # 文件名当第一行一起处理，编号与正文共用一套（否则文件名〔A厂〕、正文同一个厂成了〔B厂〕）
            combined, all_changes, _ = deidentify(p.stem + "\n" + text, known)
            new_name, new_text = combined.split("\n", 1)
            changes, name_changes = all_changes, []
            base, i = new_name, 1
            while new_name in used:  # 各文件名独立编号，不同单位可能都变成〔A中烟〕
                i += 1
                new_name = f"{base}（{i}）"
            used.add(new_name)
            (out_dir / (new_name + p.suffix)).write_text(new_text, encoding="utf-8")
            for c in changes + name_changes:
                lf.write(json.dumps({"file": name, **c}, ensure_ascii=False) + "\n")
            print(f"{new_name}: {len(changes)} 处")
    return 0


if __name__ == "__main__":
    common.force_utf8_stdout()
    sys.exit(main(sys.argv[1:]))
