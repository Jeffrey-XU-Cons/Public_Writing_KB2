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
            "尹薛闫段雷侯龙史陶黎贺顾毛郝龚邵万钱严覃武戴莫孔向汤常温康施文牛樊葛邢安齐易乔伍庞颜倪庄聂章鲁岳翟殷詹申欧耿关兰焦俞左柳甘祝包宁尚符舒阮柯纪梅童凌毕单季裴霍涂成苗谷盛曲翁冉骆蓝路游辛靳管柴蒙鲍华喻祁蒲房滕屈饶解牟艾尤阳时穆农司卓古吉缪简车项连芦麦褚娄窦戚岑景党宫费卜冷晏席卫米柏宗瞿桂全佟应臧闵苟邬边卞姬师和仇栾隋商刁沙荣巫寇桑郎甄丛仲虞敖巩明佘池查麻苑迟邝阚郜茹訾眭隗蔺郗"
            "傅阎洪钮荆谈揭贝郁鞠储芮綦谌郦逯汲")  # 阚郜茹：r7 名单里的真名，原表缺；傅洪等：r10 人员表漏网（2026-10-07），
# 海原居封权都花薄井植等同时是常用字的姓不收，误伤面太大
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
PLACE_RE = re.compile("(" + "|".join(PLACES) + ")(省|市|县|区)?(?!精神|会议|起义|整风|时期|道路|额)")  # “确保定额”里的“保定”不是地名（r9 实测误伤）
# 无地名前缀的烟草企业名（r7 结构扫描抽到）。品牌"红塔山"不动，只认后接烟草/集团/公司
COMPANY_RE = re.compile(r"(红塔|红云红河|红云|白沙|黄鹤楼|芙蓉王|娇子)(?=烟草|集团|公司|卷烟厂)")
# 卷烟品牌能直接反推是哪家中烟（“黄金叶”= 某省中烟），按单位名同等处理（2026-10-04 范文标注发现 r9 漏网）。
# 口径变更：2026-09-26 起曾有意保留品牌（测试 test_brand_names_kept），未见 Jeffrey 裁定记录；单位名已脱敏而
# 品牌照留，等于把单位名换个说法留着，故改为替换。品牌分析类内容需要具体品牌时由 Jeffrey 裁定是否回退。
# 这些词单独出现即为品牌；“黔彩”“湘村”是省级营销平台/品牌名，同样能反推省份。
BRANDS = ["黄金叶", "贵烟", "真龙", "云烟", "芙蓉王", "黄鹤楼", "利群", "苏烟", "娇子", "七匹狼", "好猫",
          "宽窄", "黔锋", "黔彩", "双喜", "湘村", "红塔山"]
BRAND_RE = re.compile("|".join(BRANDS))
# 与普通词、地名同形的品牌：须在引号里或后接规格括号/“品牌”“卷烟”才算（“中华民族”“泰山挑山工”不动）
BRAND_CTX_RE = re.compile(r"(?:中华|泰山|钻石|南京|白沙|玉溪|红河)(?=”|（|\(|品牌|卷烟|系列)")
# 无地名前缀的其他企业（投资公司、合资企业、行业直属公司、合作银行），名单逐批补
EXTRA_UNITS = ["中烟商务物流有限责任公司", "中烟商务物流公司", "中烟商务物流", "中维资本", "中维公司", "金福公司",
               "双维公司", "双维投资", "双维伊士曼", "国电双维", "中维"]
EXTRA_UNIT_RE = re.compile("|".join(sorted(EXTRA_UNITS, key=len, reverse=True)))
BANK_RE = re.compile(r"(?:中信|招商|浦发|民生|光大|华夏|兴业|平安|邮储)银行")
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
                "南流江", "翠湖宾馆", "王林", "涞源", "竹山", "竹溪", "日照四地市", "金州",
                "湘阴", "衡山", "平坝", "常张"]  # 2026-10-04 范文标注时发现的 r9 残留  # 王林 = 玉林的 OCR 错字（“王林市局”“大王林”）
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
# r8 复查（2026-10-03）抽到的两类漏网：
#   文号与平台里的省份简称：“陕烟工办〔2023〕”“渝烟局办”“黔府发〔2019〕”“智慧渝烟”“浙烟专有云”——能直接认出省份。
#   不收“苏烟”“云烟”“贵烟”（品牌，2026-09-25 拍板不脱敏），也不收“黑烟”“青烟”“新烟”“宁烟”“藏烟”这类普通词。
DOCNO_ABBR = "渝浙陕黔滇湘鄂豫川粤桂闽赣皖鲁冀晋辽吉蒙甘琼"
DOCNO_ABBR_RE = re.compile("[" + DOCNO_ABBR + "](?:烟(?=[局工办发〔（(专方案平台”\"字商]|$)|(?:府|政)办?(?:发|函))")
#   PDF 封面逐字加空格：“雄 安 烟 草 专 卖 局”“南 宁 卷 烟”“黔 烟 办 通 报”，字间有空格就躲过了全部规则。
#   只在去掉空格后能命中地名、单位名或文号简称时才合并，表格碎片“务 工 商 在 获”之类原样保留。
SPACED_RUN_RE = re.compile(r"(?:[一-龥（）][ 　]+){3,}[一-龥（）]")
# 合并后地名须紧跟机构/行政字样才算（表格碎片“条 的 简 款 通 化 预 知”拼出的“通化”不算）
SPACED_HIT_RE = re.compile("(?:" + "|".join(PLACES) + ")(?=[烟卷市省县区局公（]|$)")
DATA_RE = re.compile(
    r"\d+(?:\.\d+)?\s*(万箱|万条|亿支|万支|万元|亿元|万担|个百分点|百分点|%|％|箱|担|吨|元|万)")
NAME_TITLE_RE = re.compile(
    "(?<![一-龥])([" + SURNAMES + "])((?!副)[一-龥]{1,2}?)(" + "|".join(TITLES) + ")")  # 名字取短且不以"副"开头
SHORT_NAME_RE = re.compile(
    "(?:(?<![一-龥0-9０-９])|(?<=[和与及、]))([" + SURNAMES + "])(" + "|".join(SHORT_TITLES) + ")(?![体结部量额计裁统部监机法令空置理于罚])")
# 置理于罚 / 数字后：r10 实测“及时处置”→“及〔姓名〕处置”（时 是姓）、“17项处于”→“17〔姓名〕处于”（项 是姓），2026-10-07 修
SIGNATURE_RE = re.compile(r"^[" + SURNAMES + r"][ 　]*[一-龥](?:[ 　]*[一-龥])?$")
# 名字里的生僻字转写成私用区字符（U+E000–F8FF），NAME_TITLE_RE 的 [一-龥] 匹配不到，整名漏网
# （2026-10-04 r9 实测：国家局副局长名“徐”+私用区字，正文 6 处、文件名 1 处）。姓 + 私用区字即视为人名。
PUA_NAME_RE = re.compile("[" + SURNAMES + r"][-]+")


PLACE_CODES = "甲乙丙丁戊己庚辛壬癸"


def unit_letters(n):
    """0->A … 25->Z, 26->AA, 27->AB …（r10 以前用 chr(ord('A')+n)，超过 Z 后溢出成〔[中烟〕〔\\厂〕〔c公司〕）"""
    s, n = "", n + 1
    while n:
        n, r = divmod(n - 1, 26)
        s = chr(65 + r) + s
    return s


# 溢出占位：Z 之后的 ASCII 字符（[ \ ] ^ _ ` a-z）。按原序号换回字母编号，同一文件内映射不变
OVERFLOW_RE = re.compile(r"〔([\[\\\]^_`a-z])((?:省|市|县|区)?(?:有限责任公司|公司|局|厂|中心|园区|中烟))〕")


def fix_overflow(m):
    return f"〔{unit_letters(ord(m.group(1)) - 65)}{m.group(2)}〕"


# ===== 2026-10-07 r10→r11：B-20261007-AR-02 四个标注者读 r10 原文报出的漏网，按类型做成通用规则 =====
# 每条规则只在行内替换，不增删换行（范文记录按行号引用脱敏批次）。r11_rules() 同时被 deidentify()、
# 迁移脚本和 deid_scan（“规则还能改动的地方 = 硬泄露”）调用，所以每条规则都必须幂等。

# 省份单字简称。不收京津沪（京津冀、京沪是国家战略和线路名），不收新（新产品、新中烟里的“新”）
PROV_ABBR = "冀晋蒙辽吉黑苏浙皖闽赣鲁豫鄂湘粤桂琼川蜀渝黔贵滇云藏陕秦甘陇青宁"
PHONE_RE = re.compile(r"(?<![\d\-])1[3-9]\d(?:[ \-]?\d{4}){2}(?!\d)")
SOFTREG_RE = re.compile(r"\d{4}SR\d{5,9}")  # 软件著作权登记号，可检索到权利人
# 地方政府网址（域名带省份），中央政府网 www.gov.cn 不动
GOV_URL_RE = re.compile(r"https?://(?!www\.gov\.cn)[^\s）)\]】]*\.gov\.cn[^\s）)\]】，。]*")
# 公司名里的省份拉丁字母简称：“SX中烟”；作者自己写的“XX中烟”“XXX烟草”不动
LATIN_PROV_RE = re.compile(r"(?<![A-Za-z〔])(?=[A-Z]*[A-WYZ])[A-Z]{2,3}(?=中烟|烟草|烟厂)")
# 省份简称组合：两省合作平台“滇桂、苏桂战略合作”，“浙渝链盟”，旧称“川渝中烟”，“鲁产烟”“鄂产品规”，“闽烟文化”“闽商营销”
_P = "[" + PROV_ABBR + "]"
PROV_PAIR_RE = re.compile(_P + _P + r"(?=[、，]" + _P + _P + "|战略|合作|协作|平台|链盟|两省|毗邻|对口|结对|区域|片区)")
PROV_ZY_RE = re.compile("(?:(?<![一-龥])|(?<=[前原与和及、]))" + _P + "{1,2}中烟")
PROV_CHAN_RE = re.compile(_P + r"产(?=烟|卷烟|品规)")
PROV_YAN_RE = re.compile("[" + DOCNO_ABBR + r"](?:烟(?=文化|智慧|精神|模式|经验|品牌)|商(?=营销))")
# 江河流域、山脉（“乌江流域”“娄山山脉”）能反推省份；长江、黄河、珠江是国家层面表述不动
RIVER_RE = re.compile(r"(?!长江|黄河|珠江)[一-龥][江河]流域")
MOUNTAIN_RE = re.compile(r"[一-龥]{2}山脉")
# 发文字号：发文机关已脱敏（〔某省〕烟工办）时，年份 + 序号仍能反查原文；国务院文号与脱敏地名同句出现时同理
DOCNO_YEAR_RE = re.compile(r"(〔某省〕[一-龥]{1,6})〔\d{4}〕\s*\d+\s*号")
STATE_DOCNO_RE = re.compile(r"(国发|国函|国办发|国办函)〔\d{4}〕\s*\d+\s*号")
PLACE_PH = r"〔[甲乙丙丁戊己庚辛壬癸某](?:地|省|市|县|区)〕"  # 天干不是连续码位，不能写[甲-癸]
# 名单里的人名被地名规则吃掉一半：“张〔戊地〕”
NAME_UNIT_RE = re.compile("[" + SURNAMES + "](?:" + PLACE_PH + "|[一-龥]{1,2})")
# 人名形状的常用词（列表项、括注里常见），不当人名
COMMON_NAMEISH = set(NAME_FP) | {
    "安全", "成本", "管理", "项目", "计划", "党建", "文化", "金融", "程序", "高效", "高层", "高管", "管控", "成果",
    "宣传", "财务", "信息", "车辆", "司机", "司法", "沙盘", "华为", "钱款", "龙头", "牛皮", "江苏", "方案", "方法",
    "向上", "常规", "常务", "明确", "应急", "时间", "时效", "关键", "单位", "全面", "全员", "全局", "包装", "柏油",
    "景区", "宁波", "林业", "石油", "邮政", "严格", "苗木", "曲线", "路线", "游客", "童装", "梅花", "顾客", "商务",
    "商业", "史料", "毛利", "田间", "黄金", "白色", "红色", "蓝色", "金额", "金牌", "武装", "方面", "雷达", "韩国",
    "孙子", "成员", "成效", "武汉", "汤料", "冷链", "冷库", "车间", "车型", "车组", "公司", "部门", "科室", "处室",
    "中心", "协会", "邵阳", "党委", "党支部", "项目组", "工作组", "领导", "组长", "副组长", "成都", "师傅", "卫生",
    "安全员", "管理员", "质量", "解决", "解读", "简介", "简要", "简化", "连续", "连接", "包括", "危险",
}
_ORG_END = set("组部处室办局厂司会队院所站")  # 科、员等名字里也常见，不收


def _is_name(core):
    flat = re.sub(r"[ 　]+", "", core)
    return (NAME_UNIT_RE.fullmatch(flat) is not None and flat not in COMMON_NAMEISH
            and flat not in PUBLIC_FIGURES and flat[-1] not in _ORG_END)


_TOKEN_RE = re.compile(r"[^\s、，,；;《》“”\"]+")
_ANNOT_RE = re.compile(r"[（(][^）)]{0,24}[）)]$")
_ANNOT_ORG_RE = re.compile(r"〔|局|公司|厂|中心|处|部|室|大学|学院|研究")


def _units(seg):
    """切出列表单元：先按分隔符/空白切 token，再把“杨  瑞”“李 琦”这类拆开的单姓 + 单字并回一个名字。"""
    toks = [[m.start(), m.end(), m.group(0)] for m in _TOKEN_RE.finditer(seg)]
    out, i = [], 0
    while i < len(toks):
        s, e, t = toks[i]
        if (len(t) == 1 and t in SURNAMES and i + 1 < len(toks) and re.fullmatch(r"[一-龥]{1,2}(?:[（(].*)?", toks[i + 1][2])
                and re.fullmatch(r"[ 　]{1,3}", seg[e:toks[i + 1][0]])):
            out.append([s, toks[i + 1][1]])
            i += 2
            continue
        out.append([s, e])
        i += 1
    return out


def _mask_units(seg, units, changes, tag, need_annot=False):
    """对每个单元去掉尾部括注后判断是不是人名，是就换成〔姓名〕。need_annot：只认带单位括注的单元。"""
    for s, e in reversed(units):
        unit = seg[s:e]
        annot = _ANNOT_RE.search(unit)
        core = unit[:annot.start()] if annot else unit
        if need_annot and not (annot and _ANNOT_ORG_RE.search(annot.group(0))):
            continue
        if _is_name(core):
            changes.append({"type": tag, "orig": core, "new": "〔姓名〕"})
            seg = seg[:s] + "〔姓名〕" + seg[s + len(core):]
    return seg


# 角色词逐字允许夹空格（“组  员：”“成  员：”）
LIST_ROLE = "|".join("[ 　]*".join(w) for w in (
    "参与人 责任人 制表人 制表 填表人 作者 课题成员 主要成员 评价组 诊断组 专家组 工作组 ".split()
    + ROLE_WORDS.replace("\\s*", "").split("|")))
# 角色词或科室/处室/公司名后接冒号的名单：“副组长：…”“省局物流处：…”“〔A厂〕工艺质量科：周某”
LIST_HEAD_RE = re.compile("(?:" + LIST_ROLE + r"|[一-龥〕]{1,10}(?:科|处|部|室|办公室|公司|中心|小组|团队))[ 　]*[：:][ 　]*")


def mask_name_lists(line, changes):
    # 1) 冒号名单：冒号后到句末的各单元
    out, pos = [], 0
    for m in LIST_HEAD_RE.finditer(line):
        if m.start() < pos:
            continue
        end = re.search(r"[。；;]|$", line[m.end():]).start() + m.end()
        seg = line[m.end():end]
        new = _mask_units(seg, _units(seg), changes, "人名(名单)")
        out.append(line[pos:m.end()] + new)
        pos = end
    line = "".join(out) + line[pos:]
    # 2) 行首名单续行 / 作者行：行首连续 ≥2 个单元都是〔姓名〕或人名，且至少一个〔姓名〕
    units = _units(line)
    run = []
    for s, e in units:
        u = re.sub(_ANNOT_RE, "", line[s:e])
        if u == "〔姓名〕" or _is_name(u):
            run.append([s, e])
        else:
            break
    if len(run) >= 2 and any(line[s:e].startswith("〔姓名〕") for s, e in run) and not line[:run[0][0]].strip():
        line = _mask_units(line, run, changes, "人名(名单续行)")
    # 3) 带单位括注的名单行：“周某（〔丙地〕）  张  某（〔丁地〕）”——整行只有这样的单元才动
    units = _units(line)
    if units and all(_ANNOT_RE.search(line[s:e]) or line[s:e] == "〔姓名〕" for s, e in units) and not line[:units[0][0]].strip():
        line = _mask_units(line, units, changes, "人名(括注名单)", need_annot=True)
    return line


# 职务在前、人名在后：“由局长（经理）蒋某担任组长，副经理孟某担任副组长”
TITLE_BEFORE_NAME_RE = re.compile(
    r"((?:副)?(?:局长|经理|厂长|主任|书记|处长|科长|部长|总监))((?:（[^）]{1,6}）)?)([" + SURNAMES
    + r"][一-龥]{1,2}?)(?=担任|兼任|任组长|任副组长|同志|主持|牵头|带队)")
# 只有姓 + 全称职务，前面是“特别是”“向”这类字：“在国家局特别是李局长的指导下”
_PREP_SURNAMES = set("向和于时成万全常应党关")
SURNAME_TITLE_RE = re.compile(
    r"(?<=[是对请了、，。；：“\s])([" + SURNAMES + r"])(副?(?:局长|厂长|处长|主任|书记|总经理|司长))(?![期远效久])")
# 人员表行，允许名字中间有空格：“洪 波 男 硕士”
NAME_TABLE2_RE = re.compile(r"(?<![一-龥])([" + SURNAMES + r"](?:[ 　]?(?![男女])[一-龥]){1,2})(?=[ 　]*[|\s][ 　]*[男女](?:[\s|]|$))")
# 以人名冠名的工作室：“邵某工匠室”“邵某某技能大师工作室”“张某物流创新工作室”
WORKSHOP_RE = re.compile(r"(?:(?<=[“\"了立以在、\s])|^)([" + SURNAMES + r"][一-龥]{1,2}?)"
                         r"(?=(?:物流|技术|技能|劳模|创新|大师|技能大师){0,2}(?:工作室|工匠室))", re.M)
# 占位后的“（简称××）”：简称是真名，全文同步换成同一个占位
ABBR_DEF_RE = re.compile(r"(〔[^〕\n]{1,8}〕)[（(](?:以下)?简称[：:]?[“\"]?([一-龥A-Za-z]{2,8}?)[”\"]?[）)]")
# 品牌已换成〔品牌〕，括号里的规格名（“（中支凌云）”）仍能反推品牌；只有“硬/软/细支”之类通用词的保留
BRAND_SPEC_RE = re.compile(r"〔品牌〕([ 　]*\n?[ 　]*[（(][ 　]*)([^）)\n]{1,14}?)([ 　]*[）)])")
BRAND_NUM_RE = re.compile(r"(?<=〔品牌〕)\d{3,4}(?![\d年万亿%％])")  # “古田1929”“黄鹤楼1916”这类带数字的规格
GENERIC_SPEC_RE = re.compile(r"[硬软细中支长短粗嘴红黄蓝白金银黑绿紫新版品盒条装\s]+")
CTX_BRANDS = ["中南海", "王冠", "好日子", "白沙", "黄果树", "前门", "金桥"]
BRAND_CTX2_RE = re.compile("(?:(?<=〔品牌〕[、，])|(?<=地〕))(?:" + "|".join(CTX_BRANDS) + ")"
                           "|(?:" + "|".join(CTX_BRANDS) + r")(?=[（(]|[、，]〔品牌〕|专线|品牌|卷烟|烟标)"
                           r"|(?:中华|泰山|钻石|南京|白沙|玉溪|红河)(?=专线|牌|烟标)|长城(?=[（(])|泰山(?=微课|梦)")
# 县以下地名：已脱敏地名后括号里的乡镇列表（“〔某地〕东南部（甲、乙、丙）”）、“甲、乙、丙等标准化烟叶站”、
# 已脱敏县区后紧跟的乡镇/烟叶站名（“〔某地〕区新场烟叶站”）
PLACE_SUBLIST_RE = re.compile(r"(" + PLACE_PH + r"[东西南北中部]{1,4}[（(])((?:[一-龥]{2,3}、)+[一-龥]{2,3})(?=[）)])")
STATION_LIST_RE = re.compile(r"((?:[一-龥]{2}、)+[一-龥]{2})(?=等[一-龥]{0,6}(?:烟叶站|烟站|烟叶工作站))")
STATION_RE = re.compile(r"(" + PLACE_PH + r"[区县]?\s{0,4})([一-龥]{2})(?=烟叶站|烟站|烟叶工作站|乡|镇)")
# 与常用词同形的地名（UNIT_ONLY）夹在已脱敏地名的列表里：“〔甲地〕、中山、〔丁地〕”
UNIT_ONLY_LIST_RE = re.compile("(?<!孙)(?:(?<=〕[、，])(?:" + "|".join(UNIT_ONLY) + ")(?=[、，〔（(])|(?:"
                               + "|".join(UNIT_ONLY) + ")(?=[、，]〔))")
# 规模数（CLAUDE.md 4.2 经营数据）：2026-09-25 拍板“运营计数不算经营数据”的口径不变（网点数、时长照留），
# 只收能反推单位规模的几类——案件、审计、帮扶、人员编制、客户规模、库存周转、占地、资产。按关键词锚定
SCALE_KW = ("案件|大要案|审计项目|帮扶|贫困村|贫困户|员工|职工|(?<![使运采应备])用工(?!作)|定编|在岗|从业人员|客户经理|零售户|零售客户|"
            "经营客户|服务客户|客户数|周转次数|周转天数|在库天数|库存天数|占地|土地|面积|配车|送货户数|资产|出口")
# 核查补（2026-10-07）：“5个维度”“124个小类”是概念计数，不是规模
NOT_CONCEPT = r"(?!维度|方面|指标|环节|阶段|步骤|小类|大类|类别|模块|版块|等级|位次)"
SCALE_UNIT = r"(?:余|多)?(?:平方米|万平方米|万户|万人|亿元|万元|亿|起|件|个|项|人|名|户|次|天|辆|台|亩|㎡)(?!次)" + NOT_CONCEPT  # 户次、人次是作业量，不是规模
SCALE_RE = re.compile("(" + SCALE_KW + r")((?:〔(?!数据)[^〕\n]{1,6}〕|(?!时间|时长|座谈|工作日|小时|分钟|选取|抽取|抽样|奖|专利|课题|论文|率|中心)[^。；，,、\n\d〔]){0,10}?)(\d+(?:\.\d+)?)(\s*"
                      + SCALE_UNIT + ")")
SCALE_REV_RE = re.compile(r"(?<![\d.〕])(?<!至少)(?<!至少.)(?<!至少..)(?<!不少于)(\d+(?:\.\d+)?)(\s*(?:余|多)?(?:个|起|户|人|名|亩))(?=[^。；，、\n]{0,8}(?:贫困村|贫困户|案件|土地|烟农|帮扶))")


TARGET_WORDS_RE = re.compile(r"每个|每年|至少|不少于|力争|确保")


def _scale_rev(m):
    """“破获1起案件”式倒装规模数。所在分句是目标、要求（“每个市州局破获1起…”“至少”“力争”）时不打码（核查补，2026-10-07）。"""
    head = m.string[:m.start()]
    clause = head[max(head.rfind("。"), head.rfind("；"), head.rfind(";")) + 1:]
    return m.group(0) if TARGET_WORDS_RE.search(clause) else "〔数据〕" + m.group(2)


def _scale_sentence(line, changes):
    """规模数：关键词后第一个数打码；同一分句里同一量纲的其他数（“最低为〔乙地〕18.07次，最高为〔甲地〕23.07次”）一并打码。"""
    out = []
    for sent in re.split(r"(?<=[。；;])", line):
        while True:  # 一个分句里可能有几个关键词，逐个处理到没有可打码的为止（幂等）
            m = SCALE_RE.search(sent)
            if not m:
                break
            unit = re.escape(re.sub(r"^\s*(?:余|多)?", "", m.group(4)))
            rx = re.compile(r"(?<![\d.])\d+(?:\.\d+)?(?=\s*(?:余|多)?\s*" + unit + NOT_CONCEPT + ")")
            head, tail = sent[:m.start()], sent[m.start():]

            def repl(n):
                changes.append({"type": "经营数据(规模数)", "orig": n.group(0), "new": "〔数据〕"})
                return "〔数据〕"
            sent = head + rx.sub(repl, tail)
        out.append(sent)
    return "".join(out)


# 县以下地名、地标的长尾（同 EXTRA_PLACES 的做法：扫描候选 + 标注者报出，逐批补）。都是公开地理名，不是客户名单
R11_PLACES = ["西秀", "普定", "东肖", "新郑", "淉河", "黄骅", "黄果树", "杭甬", "巩义", "登封", "新密", "金水区", "管城区",
              # 核查补（2026-10-07）：配送表与正文里的县级地名、OCR 异体字地名、县级市
              "赞皇", "正定", "鹿泉", "栾城", "藁城", "晋州", "元氏", "赵县", "行唐", "平山", "灵寿", "高邑",
              "深泽", "井陉", "阜平", "髙碑店", "琼海", "井冈山", "(?<![创更焕])新乐", "无极(?!限)"]
# 井冈山精神、井冈山会师等固定政治表述不动（同 PLACE_RE）
R11_PLACE_RE = re.compile("(?:" + "|".join(sorted(R11_PLACES, key=len, reverse=True)) + ")(?!精神|会议|会师|斗争|时期|道路|根据地)")
# 省简称 + 方位 + 城市群/经济区（“黔中城市群”）
ABBR_DIR2_RE = re.compile(_ABBR_DIR + r"(?=城市群|经济区|经济圈|经济带)")
# 大区片区名（“中南片区最大的集散中心”）可缩小省份范围
REGION_PIECE_RE = re.compile(r"(?:东北|华北|华东|华中|华南|西南|西北|中南|东南)片区")
# 与地名同句的“援藏/援疆”能把已脱敏的地名反推回去（“技术援藏项目，向〔丁地〕全区推广”）
AID_RE = re.compile(r"援[藏疆](?!族)")
# 金额、规模的“余/多”写法与美元、单箱消耗：“下降2000余万元”“出口总额1亿美元”“排放2.56克/箱”
DATA_YU_RE = re.compile(r"\d+(?:\.\d+)?(\s*(?:余|多)\s*(?:万元|亿元|万箱|万担|万吨|万|亿))")
# 数字在行尾、量纲被 OCR 断到下一行行首：“入库卷烟67.71⏎万箱”
DATA_CROSS_RE = re.compile(r"(?<![\d.〕])\d+(?:\.\d+)?(?=[ 　]*\n[ 　]*(?:万箱|万条|亿支|万支|万元|亿元|万担|%|％)(?![一-龥]))")  # 表格里下一行是“万箱终端送货费用”这类指标名，不算
DATA_USD_RE = re.compile(r"\d+(?:\.\d+)?(\s*(?:万|亿)?美元)")
DATA_PERBOX_RE = re.compile(r"\d+(?:\.\d+)?(\s*(?:克|千克|公斤|kg|千瓦时|kWh|立方米|吨)\s*/\s*(?:箱|万支|大箱))")
# 顿号列表里有已脱敏地名时，同列表里地名形状的项也是地名（“金水区、管城区、〔某地〕以及新郑、巩义等地区”“青县、〔某地〕”）
_ENUM_RE = re.compile(r"(?:[^\s、，,。；;：:（）()“”]{1,8}(?:、|以及|及|和))+[^\s、，,。；;：:（）()“”]{1,8}")
_PLACE_SHAPED_RE = re.compile(r"[一-龥]{1,3}(?:区|县|旗)|[一-龥]{2,3}(?:镇|乡)")
_GENERIC_AREAS = {"高新区", "经开区", "开发区", "新区", "城区", "主城区", "老城区", "市区", "园区", "郊区", "辖区", "片区",
                  "该县", "全县", "各县", "本县", "全区", "各区", "本区", "山区", "库区", "厂区", "景区", "社区", "烟区",
                  "产区", "矿区", "林区", "牧区", "灾区", "边区", "城乡", "乡镇", "城镇", "重点镇"}


def _mask_place_enum(line, changes):
    def repl(m):
        items = re.split(r"(、|以及|及|和)", m.group(0))
        if not any(re.fullmatch(PLACE_PH, it) for it in items[::2]):
            return m.group(0)
        tail = line[m.end():m.end() + 4]
        listy = tail.startswith("等") and re.match(r"等(?:地区|地|县|区县|市县|乡镇)", tail)
        out = []
        head = re.search(r"(?<=[为在于是：:])[一-龥]{2}[区县]$", items[0])  # 首项常连着前文：“调查地点为金牛区”
        if head and head.group(0) not in _GENERIC_AREAS:
            changes.append({"type": "地名(列表)", "orig": head.group(0), "new": "〔某地〕"})
            items[0] = items[0][:head.start()] + "〔某地〕"
        for i, it in enumerate(items):
            if i % 2 == 0 and it not in _GENERIC_AREAS and not it.startswith("〔") and (
                    _PLACE_SHAPED_RE.fullmatch(it) or it in UNIT_ONLY or (listy and re.fullmatch(r"[一-龥]{2}", it))):
                changes.append({"type": "地名(列表)", "orig": it, "new": "〔某地〕"})
                it = "〔某地〕"
            out.append(it)
        return "".join(out)
    return _ENUM_RE.sub(repl, line)


def _crossline(text, words, new, tag, changes, tail="", keep_tail=False):
    """OCR 把专名拆在两行（中间可隔空行）：“…广\\n\\n西中烟”。换成占位，换行原样保留，行数不变。"""
    for w in words:
        sep = r"(?:[ 　]*\n[ 　]*)*"
        rx = re.compile(sep.join(map(re.escape, w)) + "(" + sep + "(?:" + tail + "))" if tail else
                        sep.join(map(re.escape, w)))

        def repl(m):
            if "\n" not in m.group(0):
                return m.group(0)
            changes.append({"type": tag, "orig": m.group(0).replace("\n", "⏎"), "new": new})
            kept = m.group(1) if (keep_tail and tail) else ""
            return new + "\n" * (m.group(0).count("\n") - kept.count("\n")) + kept
        text = rx.sub(repl, text)
    return text


def harvest_specs(text):
    """〔品牌〕后括号里的规格名（非通用词），供同文/同批次其他位置同步替换。"""
    specs = set()
    for m in BRAND_SPEC_RE.finditer(text):
        spec = re.sub(r"〔品牌〕|[ 　]", "", m.group(2))
        if spec and "〔" not in spec and not GENERIC_SPEC_RE.fullmatch(spec):
            specs.add(spec)
    return specs


def r11_rules(text, known_specs=()):
    """2026-10-07 补的规则，作用于已脱敏文本（也被 deidentify() 末尾调用）。返回 (新文本, changes)。"""
    changes = []

    def sub(rx, new, tag, s):
        def repl(m):
            val = new(m) if callable(new) else new
            if val != m.group(0):
                changes.append({"type": tag, "orig": m.group(0), "new": val})
            return val
        return rx.sub(repl, s)

    text = sub(OVERFLOW_RE, fix_overflow, "占位溢出修正", text)
    text = _crossline(text, PROVINCES, "〔某中烟〕", "单位名(跨行拆字)", changes, tail="中烟")
    text = _crossline(text, ["红塔", "红云红河", "红云", "白沙", "黄鹤楼", "芙蓉王", "娇子"], "〔某企业〕",
                      "企业名(跨行拆字)", changes, tail="烟草|集团|公司|卷烟", keep_tail=True)
    # 核查补（2026-10-07）：三字以上地名、品牌被拆在两行（“秦皇⏎岛”“红⏎河(软 99)”）
    text = _crossline(text, [c for c in CITIES if len(c) >= 3] + ["髙碑店"], "〔某地〕", "地名(跨行拆字)", changes)
    # 二字地名只认“行尾一个字＋下一行只有另一个字”的图表碎片（“…、黄⏎石⏎”），正文换行不认
    text = _crossline(text, [c for c in CITIES if len(c) == 2], "〔某地〕", "地名(跨行拆字)", changes,
                      tail=r"[ 　]*(?=\n|$)", keep_tail=True)
    text = _crossline(text, BRANDS, "〔品牌〕", "品牌(跨行拆字)", changes)
    text = _crossline(text, ["中华", "泰山", "钻石", "南京", "白沙", "玉溪", "红河", "长城"] + CTX_BRANDS, "〔品牌〕",
                      "品牌(跨行拆字)", changes, tail=r"[（(]", keep_tail=True)
    # 简称与规格名：先从本文收集，再全文同步替换
    abbrs = {}
    for m in ABBR_DEF_RE.finditer(text):
        val = m.group(2)
        if "〔" not in val and not re.fullmatch(r"[A-Za-z]+", val) and val not in COMMON_NAMEISH:
            abbrs[val] = m.group(1)
    for val, ph in sorted(abbrs.items(), key=lambda kv: -len(kv[0])):
        text = sub(re.compile(re.escape(val)), ph, "单位简称(简称定义)", text)
    text = sub(BRAND_CTX2_RE, "〔品牌〕", "品牌", text)  # 先换品牌，规格括号才认得出（“中南海(5mg)”）
    specs = set(known_specs) | harvest_specs(text)
    text = sub(BRAND_NUM_RE, "〔规格〕", "品牌规格", text)
    text = sub(BRAND_SPEC_RE, lambda m: m.group(0) if (GENERIC_SPEC_RE.fullmatch(m.group(2)) or m.group(2) == "〔规格〕")
               else f"〔品牌〕{m.group(1)}〔规格〕{m.group(3)}", "品牌规格", text)
    for spec in sorted(specs, key=len, reverse=True):
        if len(spec) < 2:
            continue
        body = r"[ 　]*".join(map(re.escape, spec))
        rx = re.compile(r"(?:(?<=[“”\"（(])[ 　]*|(?<=培育)|(?<=细支|中支|粗支|短支))" + body + r"|" + body
                        + r"(?=[ 　]*[”\"）)]|品规|规格|陈列|二维码|卷烟|系列|投放)")
        text = sub(rx, "〔规格〕", "品牌规格(同文)", text)
    text = sub(DATA_CROSS_RE, "〔数据〕", "经营数据(跨行)", text)
    out = []
    for line in text.split("\n"):
        line = sub(R11_PLACE_RE, "〔某地〕", "地名(县级/地标)", line)
        line = mask_name_lists(line, changes)
        line = sub(TITLE_BEFORE_NAME_RE, lambda m: m.group(1) + m.group(2) + "〔姓名〕", "人名(职务在前)", line)
        line = sub(SURNAME_TITLE_RE, lambda m: m.group(0) if m.group(1) in _PREP_SURNAMES else "〔姓名〕" + m.group(2),
                   "人名(姓+职务)", line)
        line = sub(NAME_TABLE2_RE, lambda m: m.group(0) if re.sub(r"[ 　]", "", m.group(1)) in COMMON_NAMEISH
                   else "〔姓名〕", "人名(人员表)", line)
        line = sub(WORKSHOP_RE, lambda m: m.group(0) if m.group(1) in COMMON_NAMEISH else "〔姓名〕",
                   "人名(工作室冠名)", line)
        for rx, new, tag in ((PHONE_RE, "〔手机号〕", "手机号"), (SOFTREG_RE, "〔登记号〕", "软著登记号"),
                             (GOV_URL_RE, "〔网址〕", "地方政府网址"), (LATIN_PROV_RE, "〔某省〕", "省份简称(拉丁字母)"),
                             (PROV_ZY_RE, "〔某中烟〕", "单位名(简称中烟)"), (PROV_PAIR_RE, "〔某区域〕", "省份简称组合"),
                             (PROV_CHAN_RE, "〔某省〕产", "省份简称(X产烟)"),
                             (PROV_YAN_RE, lambda m: "〔某省〕" + m.group(0)[1:], "省份简称(X烟)"),
                             (RIVER_RE, "〔某流域〕", "地名(流域/山脉)"), (MOUNTAIN_RE, "〔某山脉〕", "地名(流域/山脉)"),
                             (UNIT_ONLY_LIST_RE, "〔某地〕", "地名(列表)"),
                             (PLACE_SUBLIST_RE, lambda m: m.group(1) + re.sub(r"[一-龥]{2,3}", "〔某地〕", m.group(2)),
                              "地名(乡镇列表)"),
                             (STATION_LIST_RE, lambda m: re.sub(r"[一-龥]{2}", "〔某地〕", m.group(1)), "地名(烟叶站列表)"),
                             (STATION_RE, lambda m: m.group(1) + "〔某地〕", "地名(乡镇/烟叶站)"),
                             (DOCNO_YEAR_RE, lambda m: m.group(1) + "〔文号〕", "发文字号"),
                             (ABBR_DIR2_RE, "〔某区域〕", "地名(省简称方位)"),
                             (REGION_PIECE_RE, "〔某片区〕", "地名(片区)"),
                             (SCALE_REV_RE, _scale_rev, "经营数据(规模数)"),
                             (DATA_YU_RE, lambda m: "〔数据〕" + m.group(1), "经营数据"),
                             (DATA_USD_RE, lambda m: "〔数据〕" + m.group(1), "经营数据"),
                             (DATA_PERBOX_RE, lambda m: "〔数据〕" + m.group(1), "经营数据(单耗)")):
            line = sub(rx, new, tag, line)
        line = _mask_place_enum(line, changes)
        line = _scale_sentence(line, changes)
        if re.search(PLACE_PH, line):
            line = sub(STATE_DOCNO_RE, lambda m: m.group(1) + "〔文号〕", "发文字号(与地名同句)", line)
            line = sub(AID_RE, "援〔某省〕", "地名(援藏援疆)", line)
        out.append(line)
    return "\n".join(out), changes


def load_names_file(path):
    """names_confirmed.txt：一行一个。人名直接写；非人名的专名写成“〔占位〕专名”（如“〔某企业〕某某咨询”），
    批次内不论位置一律替换成该占位。返回 [(专名, 占位或 None)]。"""
    items = []
    for raw in Path(path).read_text(encoding="utf-8").splitlines():
        s = raw.strip()
        if not s or s.startswith("#"):
            continue
        m = re.match(r"^(〔[^〕]+〕)\s*(.+)$", s)
        items.append((m.group(2).strip(), m.group(1)) if m else (s, None))
    return items



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


def apply_known_names(text, known_names):
    """已确认名单在全文不论位置替换。条目是人名字符串，或 (专名, 占位) 二元组（见 load_names_file）。"""
    changes = []
    items = [(n, None) if isinstance(n, str) else tuple(n) for n in known_names]
    for name, placeholder in sorted(items, key=lambda kv: len(kv[0]), reverse=True):
        # 字间允许空白：PDF 转写常把“邹岚”排成“邹  岚”（r7 名单实测）
        rx = re.compile(r"[ 　]*".join(map(re.escape, name)))
        if placeholder:
            new, tag = placeholder, "专名(已知名单)"
        else:
            # 名单里带职务的条目（“凌局长”“志成同志”）只替换人名，职务保留（4.2：删人名、留职务）
            title = next((t for t in sorted(TITLES + SHORT_TITLES, key=len, reverse=True)
                          if name.endswith(t) and len(name) > len(t)), "")
            new, tag = "〔姓名〕" + title, "人名(已知名单)"
        hits = rx.findall(text)
        if hits:
            changes.extend({"type": tag, "orig": h, "new": new} for h in hits)
            text = rx.sub(new, text)
    return text, changes


def deidentify(text: str, known_names=(), known_specs=()):
    changes, unit_map, place_map, key_map = [], {}, {}, {}
    text, changes = apply_known_names(text, known_names)

    for m in PUA_NAME_RE.finditer(text):
        changes.append({"type": "人名(生僻字)", "orig": m.group(0), "new": "〔姓名〕"})
    text = PUA_NAME_RE.sub("〔姓名〕", text)

    def unit_repl(m):
        # 同一单位的全称与简称共用一个编号：“南阳卷烟厂/南阳厂”“河南中烟/河南中烟工业有限责任公司”
        # （r7 实测一份报告里同一个厂被编成〔A厂〕〔C厂〕两个号）。键 = 地名 + 行政级 + 去掉通用词的中缀 + 层级
        full = m.group(0)
        middle = m.group(3) or ""
        level = "中烟" if "中烟" in middle else LEVEL_OF[m.group(4)]
        key = (m.group(1), m.group(2) or "", re.sub("中烟|工业|卷烟|烟草|有限责任|专卖", "", middle), level)
        if key not in key_map:
            letter = unit_letters(len(key_map))  # 超过 Z 接 AA、AB（r10 溢出成〔[中烟〕）
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
    known_set = {n if isinstance(n, str) else n[0] for n in known_names}
    out = []
    for line in text.splitlines():
        stripped = line.strip()
        if stripped and re.sub(r"[ 　]", "", stripped) in known_set and re.search(r"[ 　]", stripped):
            changes.append({"type": "人名(署名行)", "orig": stripped, "new": "〔姓名〕"})
            out.append("〔姓名〕")
            continue
        def spaced_repl(m):
            joined = re.sub(r"[ 　]+", "", m.group(0))
            if any(rx.search(joined) for rx in (SPACED_HIT_RE, UNIT_RE, DOCNO_ABBR_RE)):
                changes.append({"type": "空格拆字合并", "orig": m.group(0), "new": joined})
                return joined
            return m.group(0)
        line = SPACED_RUN_RE.sub(spaced_repl, line)

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
        for rx, tag, new in ((EXTRA_UNIT_RE, "企业名(无地名)", "〔某企业〕"), (BANK_RE, "银行名", "〔某银行〕"),
                             (BRAND_RE, "品牌", "〔品牌〕"), (BRAND_CTX_RE, "品牌", "〔品牌〕")):
            for m in rx.finditer(line):
                changes.append({"type": tag, "orig": m.group(0), "new": new})
            line = rx.sub(new, line)
        for m in ABBR_RE.finditer(line):
            changes.append({"type": "单位简称", "orig": m.group(0), "new": "〔某厂〕"})
        line = ABBR_RE.sub("〔某厂〕", line)
        line = PLACE_RE.sub(place_repl, line)
        for rx, tag, new in ((EXTRA_PLACE_RE, "地名(县级/地标)", "〔某地〕"), (AUTONOMOUS_RE, "地名(自治州县)", "〔某自治州〕"),
                             (ABBR_DIRECTION_RE, "地名(省简称方位)", "〔某区域〕")):
            for m in rx.finditer(line):
                changes.append({"type": tag, "orig": m.group(0), "new": new})
            line = rx.sub(new, line)
        for m in DOCNO_ABBR_RE.finditer(line):
            changes.append({"type": "省份简称(文号/平台)", "orig": m.group(0), "new": "〔某省〕" + m.group(0)[1:]})
        line = DOCNO_ABBR_RE.sub(lambda m: "〔某省〕" + m.group(0)[1:], line)
        line = DATA_RE.sub(data_repl, line)
        for m in QSTD_RE.finditer(line):
            changes.append({"type": "企标代号", "orig": m.group(0), "new": "Q/〔企业〕"})
        line = QSTD_RE.sub("Q/〔企业〕", line)
        line = NAME_TITLE_RE.sub(name_repl, line)
        line = SHORT_NAME_RE.sub(short_repl, line)
        out.append(line)
    text, more = r11_rules("\n".join(out), known_specs)
    changes.extend(more)
    return text, changes, unit_map


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
        known = load_names_file(names_file)
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
