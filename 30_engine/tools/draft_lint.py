"""W5-1 machine check + code-level hard gates (10章 W5-1 / §4.1, 11章 P3.1-3.2).

Severity: block (hard gate, must fix) / warn (report, human decides) / advice (style suggestion).
Exit code 1 if any block finding.

Gates:
  W1-2 判断句   check_thesis      topic-phrase patterns + no-predicate detection
  W2-4 MECE     check_mece        sibling headings identical after stripping filler / empty / near-synonym
  W3-2 数据基准 check_baseline    change-numbers without a baseline; degree adverbs without a number
  R6   判断溯源 check_trace       --final: judgment sentences must be registered with a source in report
  R7   逐段审   check_paragraphs  --final: every body paragraph must have a filled row in report 逐段审表
                                  (主旨/跑题句/衔接/口径 written out, not just ticked; 结论 not 不通过)
  W5-1 机检     machine checks    quotes, numbering, 总分, long clauses, delete-list, title punctuation,
                                  dictionary rules (terms.jsonl kind 禁用词/搭配错误/套话), [待补] residue
                                  + 2026-09-29: Q-017/018/019/030/032/039/041/048/054/055/056 and 字数区间
                                  (levels calibrated on 82 real docs; see gw-review quality-checklist 机检实现状态)

W1-2 and W2-4 are semantic by nature: the code gate is NECESSARY, not sufficient — it blocks clear
violations; gw-review's LLM pass covers the rest.

CLI: python draft_lint.py DRAFT.md [--outline OUTLINE.md] [--report REVIEW_REPORT.md] [--final] [--json]
"""

import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import common

# 纯标准库（11章风险表：机检/校验类脚本两台机器都要能直接跑，不装依赖）

CN_NUM = "一二三四五六七八九十"
HANZI_RE = re.compile(r"[一-鿿]")


def cn2int(s):
    if s.isdigit():
        return int(s)
    if s == "十":
        return 10
    if s.startswith("十"):
        return 10 + CN_NUM.index(s[1]) + 1
    if "十" in s:
        a, _, b = s.partition("十")
        return (CN_NUM.index(a) + 1) * 10 + (CN_NUM.index(b) + 1 if b else 0)
    return CN_NUM.index(s) + 1


def finding(rule, line, msg, severity="block", gate="W5-1"):
    return {"gate": gate, "rule": rule, "line": line, "msg": msg, "severity": severity}


# ---------------- 标题解析 ----------------

# 允许序号内有空格：PDF 转 Markdown 常产生"一 、"（真实成稿实测）
HEADING_PATTERNS = [
    # 外层结构：篇/部分 包含 章（82 份实测：不识别这一级，不同部分的小标题被并成一组）
    (-1, re.compile(r"^第([一二三四五六七八九十]+)(?:部分|篇)")),
    (0, re.compile(r"^第([一二三四五六七八九十]+)章")),
    (1, re.compile(r"^([一二三四五六七八九十]+)\s*、")),
    (2, re.compile(r"^[（(]\s*([一二三四五六七八九十]+)\s*[）)]")),
    (3, re.compile(r"^(\d+)\s*[.．、](?!\d)")),
    (4, re.compile(r"^[（(]\s*(\d+)\s*[）)]")),
]


def clean_line(line):
    return re.sub(r"^\s*#+\s*", "", line).replace("**", "").strip()


TOC_RE = re.compile(r"(?:\.{3,}|…{2,}|·{3,}|-{4,}|\t|\s{3,})\s*\d+\s*$")  # 目录行"诊断开展情况……1"


def parse_headings(text):
    out = []
    for no, raw in enumerate(text.splitlines(), 1):
        line = clean_line(raw)
        if TOC_RE.search(line):
            continue
        for level, pat in HEADING_PATTERNS:
            m = pat.match(line)
            if m:
                out.append({"line": no, "level": level, "num": cn2int(m.group(1)),
                            "text": line, "body": line[m.end():].strip()})
                break
    return out


def check_numbering(text):
    """Q-029 层级跳级 + 同级序号跳号（G-08）。"""
    res, expected, depth, last_seen = [], {}, None, {}
    for h in parse_headings(text):
        lv = h["level"]
        if lv <= 0:  # 篇/部分/章是外层结构，"第一部分"下直接接"一、"很常见，不参与跳级检查
            depth = None
        elif depth is not None and lv > depth + 1:
            # 短、无句末标点 = 标题式，跳级要拦；句子式（长或以句号/分号结尾）多是正文列举，只报
            heading_like = len(HANZI_RE.findall(h["body"])) <= 20 and not re.search(r"[。；;！？?]$", h["body"])
            res.append(finding("Q-029 层级跳级", h["line"], f"「{h['text'][:12]}」从第{depth}级直接跳到第{lv}级",
                               "block" if heading_like else "warn"))
        for deeper in [k for k in expected if k > lv]:
            del expected[deeper]
        want = expected.get(lv, 1)
        # 重新从 1 开始 = 新列表；接着全文上一个同级号连续编（"第十七章"跨篇、"（十八）"跨"七、"）
        # 也是公文惯例（82 份实测）；只报真正的跳号和倒序
        continued = h["num"] == last_seen.get(lv, 0) + 1
        if h["num"] != want and h["num"] != 1 and not continued:
            # 一二级是结构性标题，跳号要拦；三四级多是正文列举（访谈记录、问卷），82 份实测噪音大，只报不拦
            res.append(finding("序号跳号", h["line"], f"「{h['text'][:12]}」序号应为{want}，实为{h['num']}",
                               "block" if lv <= 2 else "warn"))
        expected[lv] = h["num"] + 1
        last_seen[lv] = h["num"]
        depth = lv if lv > 0 else None
    return res


def check_shi_series(text):
    """段内"一是/二是"序列连续性。"""
    res = []
    for no, line in enumerate(text.splitlines(), 1):
        nums = [cn2int(m) for m in re.findall(r"([一二三四五六七八九十]+)是", line)
                if re.search(m + "是[^否非]", line)]
        nums = [n for n in nums if n <= 10]
        # 按"从一是重新开始"切成多组（PDF 常把两段并成一行）；行首不从一开始的那组可能是上一行的延续，不查
        runs, cur = [], []
        for n in nums:
            if n == 1 and cur:
                runs.append(cur)
                cur = []
            cur.append(n)
        runs.append(cur)
        for run in runs:
            if run and run[0] == 1 and run != list(range(1, len(run) + 1)):
                res.append(finding("序号跳号", no, f"段内「X是」序列为{run}，不连续"))
    return res


CLAIM_RE = re.compile(r"(?:体现在|表现在|做好|呈现|存在|包括|围绕|从|抓好|突出)(?:以下)?([一二三四五六七八九十两])(?:个|项|条|点)"
                      r"(?:方面|工作|特点|问题|维度|角度|任务|措施|原则|目标|方向|重点|环节)")


def check_total_parts(text):
    """Q-005 总分数量：总括"X个方面"与后续"一是…"条数不符。只核对同段及紧随的列举行。"""
    res, lines = [], text.splitlines()
    for i, line in enumerate(lines):
        for m in CLAIM_RE.finditer(line):
            claim = 2 if m.group(1) == "两" else cn2int(m.group(1))
            seg = line[m.end():]
            j = i + 1
            while j < len(lines) and re.match(r"^\s*(?:[一二三四五六七八九十]+是|[（(][一二三四五六七八九十]+[）)]|\d+[.．、])", clean_line(lines[j])):
                seg += "\n" + lines[j]
                j += 1
            parts = set(re.findall(r"([一二三四五六七八九十]+)是", seg)) or \
                set(re.findall(r"^\s*[（(]([一二三四五六七八九十]+)[）)]", seg, re.M))
            if parts and len(parts) != claim:
                res.append(finding("Q-005 总分数量", i + 1, f"总括说{m.group(1)}项，实际展开{len(parts)}项"))
    return res


def check_quotes(text):
    """CLAUDE.md §4.3：英文直引号、「」『』零容忍。"""
    res = []
    for no, line in enumerate(text.splitlines(), 1):
        if HANZI_RE.search(line) and re.search(r"[\"']", line):
            res.append(finding("直引号", no, "中文文本含英文直引号，须用“”‘’"))
        if re.search(r"[「」『』]", line):
            res.append(finding("直角引号", no, "含「」『』，须用“”‘’"))
    return res


def check_long_clauses(text, limit=25, per_k=2):
    """Q-052 / 门禁 L5：超 25 字未断的长句每千字≤2。"""
    body = "\n".join(l for l in text.splitlines() if not parse_headings(l))
    clauses = re.split(r"[，。；！？、：,;!?:\n]", body)
    long_ = [c for c in clauses if len(HANZI_RE.findall(c)) > limit]
    total = len(HANZI_RE.findall(body))
    if total and len(long_) / (total / 1000) > per_k:
        # warn 不拦（2026-09-25 拍板）：82 份真实成稿中正文足量的 35 份全部超标，阈值对真实公文过严，待 P4 实测再定
        return [finding("Q-052 长句密度", None,
                        f"超{limit}字未断长句 {len(long_)} 处/{total}字，每千字{len(long_) / (total / 1000):.1f}>{per_k}；"
                        f"例：{long_[0].strip()[:20]}…", "warn")]
    return []


DELETE_LIST = ["用一句话概括", "简而言之", "这正是", "我们也清醒地认识到", "诚意所在", "深度参与", "拨冗莅临"]


def check_delete_list(text):
    """Q-064 删除清单。"""
    return [finding("Q-064 删除清单", no, f"「{w}」类表述应直接删除")
            for no, line in enumerate(text.splitlines(), 1) for w in DELETE_LIST if w in line]


def check_title_punct(text):
    """Q-068 标题末尾不加标点；Q-067 长度（建议）。"""
    res = []
    for h in parse_headings(text):
        run_in = re.search(r"[。；！？].+", h["body"])  # "（二）标题。正文…"随文标题，标题后句号是规范写法
        m = re.search(r"[。，；：！？.,;:!?]$", h["text"])
        # 82 份实测：结尾分号/逗号/问号的编号行是正文列举、问卷题或 PDF 折行，不是标题标点问题
        if m and not run_in and len(h["body"]) <= 30 and m.group(0) not in "；;，,？?、":
            if m.group(0) in "：:" or h["level"] >= 2:
                # 冒号引出列举；二级"（三）优化烟草物流布局。"在烟草系统多为随文标题（PDF 把正文折到下一行，
                # 看不出原是随文）——82 份实测 221 处全是这种；三四级多是句子式列举。只有一级带句号才拦
                sev = "warn"
            else:
                sev = "block"
            res.append(finding("Q-068 标题末尾标点", h["line"], f"「{h['text'][:12]}」末尾不应有标点", sev))
        cap = {1: 16, 2: 12}.get(h["level"])
        title = re.split(r"[。；！？]", h["body"])[0]  # 随文标题只算句号前的标题部分
        n = len(HANZI_RE.findall(title))
        if cap and n > cap and len(title) <= 40:
            res.append(finding("Q-067 标题长度", h["line"], f"{h['level']}级标题{n}字，建议≤{cap}", "warn"))
    return res


VAGUE_TIME = ["年内", "近期", "适时", "择机", "尽快"]


def check_vague_time(text):
    """Q-033 时间节点不接受模糊词（部署语境；背景叙述里也可能出现，故只报 warn）。"""
    return [finding("Q-033 时间模糊", no, f"「{w}」——部署须精确到月", "warn")
            for no, line in enumerate(text.splitlines(), 1) for w in VAGUE_TIME if w in line]


def check_placeholder(text, final):
    """红线 R3：[待补] 不得进终稿。"""
    if not final:
        return []
    return [finding("R3 待补残留", no, "终稿不得保留[待补]占位")
            for no, line in enumerate(text.splitlines(), 1) if re.search(r"[\[【]待补", line)]


# ---------------- 补齐 AUTO 项（2026-09-29，quality-checklist 标 AUTO 但此前未实现的） ----------------
# 严重级别原则：判据清楚、误报近零才 block；其余 warn/advice，由 82 份真实成稿基线校准。

def is_heading(raw):
    """markdown 标题，或带编号且不超过 40 字的短标题行。"""
    return raw.lstrip().startswith("#") or any(p.match(clean_line(raw)) and len(clean_line(raw)) <= 40
                                               for _, p in HEADING_PATTERNS)


def body_paragraphs(text):
    """正文段落 = 一个非空物理行（跳过 markdown 标题、表格、编号短标题）：[(行号, 段落文本)]。
    不按空行拼段：转换来的成稿段间常无空行，拼段会把多段误判成超长段（82 份实测 452 条误报）。"""
    paras = []
    for no, raw in enumerate(text.splitlines(), 1):
        line = raw.strip()
        if line and not line.startswith("|") and not is_heading(raw):
            paras.append((no, line))
    return paras


# Q-017 指导思想引用顺序——只做预筛（warn），R1 红线终判在人工：
# 82 份实测，国家局正式文件既有“贯彻党的十九大精神，坚持以……思想为指导”，也有“以……思想为指导，贯彻党的二十大精神”，
# 故“思想”与“党的X大”视为同级；“省委省政府”与“国家局”的先后 legacy 两处规格矛盾，不查。
POLICY_RANK = [(r"习近平新时代中国特色社会主义思想", 1), (r"党的[一二三四五六七八九十]+大", 1),
               (r"中央经济工作会议", 2), (r"全国烟草工作会议|国家局党组|国家烟草专卖局党组", 3)]


def check_policy_order(text):
    res = []
    for no, para in body_paragraphs(text):
        for sent in re.split(r"(?<=[。；！？])", para):
            hits = sorted((m.start(), rank) for pat, rank in POLICY_RANK for m in [re.search(pat, sent)] if m)
            ranks = [r for _, r in hits]
            if any(a > b for a, b in zip(ranks, ranks[1:])):
                res.append(finding("Q-017 指导思想顺序", no, f"「{sent.strip()[:30]}」高层级引用排在低层级之后，人工核", "warn"))
    return res


# Q-018 “四个意识/四个自信/两个维护”顺序——只提示（advice）：国家局讲话原文就有“坚决做到‘两个维护’……树牢‘四个意识’”
# 的倒序用法，“两个维护”单用也常见，legacy“不可拆开、不可调换”对真实文本不成立。
def check_sige(text):
    res = []
    for no, para in body_paragraphs(text):
        pos = [(para.find(k), k) for k in ("四个意识", "四个自信", "两个维护") if k in para]
        if not pos:
            continue
        if [k for _, k in sorted(pos)] != [k for _, k in pos]:
            res.append(finding("Q-018 固定组合顺序", no, "“四个意识、四个自信、两个维护”非标准顺序，确认是否有意", "advice"))
    return res


# Q-019 政治套语改写；Q-025/026/028 术语错写（清单原文的小表，词典 t4_contrast 建成后迁过去）
WRONG_FORMS = [("高质量的发展", "高质量发展", "warn"), ("现代化的建设", "现代化建设", "warn"),
               ("成熟度考核", "成熟度评价", "warn"), ("下属单位", "直属单位（烟草系统口径）", "advice")]
# “省公司→省局（公司）”未纳入：工业公司与正式文件里“省公司”是正常说法，82 份实测多为误报


def check_wrong_forms(text):
    res = []
    for no, line in enumerate(text.splitlines(), 1):
        for wrong, right, sev in WRONG_FORMS:
            if wrong in line:
                res.append(finding("Q-019/025 表述不规范", no, f"「{wrong}」→「{right}」", sev))
    return res


# Q-030/031 同层序号格式唯一、全文一致
def check_numbering_format(text):
    fmts = {}
    for no, raw in enumerate(text.splitlines(), 1):
        line = clean_line(raw)
        for key, pat in (("三级", r"^\d+\s*([.．、])(?!\d)"), ("二级", r"^([（(])\s*[一二三四五六七八九十]+\s*[）)]"),
                         ("四级", r"^([（(])\s*\d+\s*[）)]")):
            m = re.match(pat, line)
            if m:
                fmts.setdefault(key, {}).setdefault(m.group(1).replace("．", "."), no)
    return [finding("Q-030 同层序号格式不一", min(v.values()), f"{k}序号混用「{'」「'.join(v)}」", "warn")
            for k, v in fmts.items() if len(v) > 1]


# Q-032 数字表述：百分数用阿拉伯数字
def check_number_format(text):
    return [finding("Q-032 百分数写法", no, "百分数用阿拉伯数字（如 85.7%）", "warn")
            for no, line in enumerate(text.splitlines(), 1)
            if re.search(r"百分之(?!百)[零〇一二三四五六七八九十点]+", line)]


# Q-039 连续 3 句无数据（汇总成一条 advice，逐句报会淹没真问题）
def check_data_density(text):
    runs = 0
    for _, para in body_paragraphs(text):
        streak = 0
        for s in re.split(r"(?<=[。；！？])", para):
            streak = 0 if re.search(r"\d", s) else streak + 1
            if streak == 3:
                runs += 1
    return [finding("Q-039 连续无数据", None, f"{runs} 处连续 3 句以上无数据（成效段需补数据，其余可忽略）", "advice")] if runs else []


# Q-041 超长段无分条（tobacco-style：一般 ≤300 字，禁止 >500 字无分条；清单 200 字偏严，按 style 取值）
def check_long_paragraph(text):
    """>500 字无分条逐段 warn（style 的“禁止”线）；300–500 字汇总一条 advice。
    82 份真实成稿实测 >300 字无分条 298 处，与 Q-052 长句一样，规范比交付实际严，不逐条刷屏。"""
    res, mid = [], 0
    for no, para in body_paragraphs(text):
        n = len(HANZI_RE.findall(para))
        if n <= 300 or re.search(r"[一二三四五六七八九十]是|（[一二三四五六七八九十]）|第[一二三四五六七八九十]，", para):
            continue
        if n > 500:
            res.append(finding("Q-041 长段无分条", no, f"段落 {n} 字未分条（>500 字须用一是/二是展开）", "warn"))
        else:
            mid += 1
    if mid:
        res.append(finding("Q-041 长段偏长", None, f"{mid} 段 300–500 字未分条，可考虑拆分", "advice"))
    return res


# Q-048 节奏断点：连续 4 句字数相差不超过 3 字（汇总 advice）
def check_rhythm(text):
    hits = 0
    for _, para in body_paragraphs(text):
        lens = [len(HANZI_RE.findall(s)) for s in re.split(r"[，。；！？]", para) if len(HANZI_RE.findall(s)) >= 6]
        hits += sum(1 for i in range(len(lens) - 3) if max(lens[i:i + 4]) - min(lens[i:i + 4]) <= 3)
    return [finding("Q-048 节奏单调", None, f"{hits} 处连续 4 个分句字数相近，可用长短句交错", "advice")] if hits else []


# Q-054 句式重复：“一是X…二是X…三是X”领起词相同
def check_same_lead(text):
    res = []
    for no, para in body_paragraphs(text):
        leads = re.findall(r"[一二三四五六七八九十]是(?:要)?([一-鿿]{2})", para)
        for w in {w for w in leads if leads.count(w) >= 3}:
            res.append(finding("Q-054 领起词重复", no, f"「{w}」连续作领起词 {leads.count(w)} 次，交替使用不同动词", "advice"))
    return res


# Q-055 开场、Q-056 结尾（首段/末段 ≤200 字；开场禁比喻铺垫；结尾禁通用号召）
OPENING_BAN = re.compile(r"坐标系|里程碑|新征程上|大潮|浪潮|号角")
ENDING_GENERIC = re.compile(r"让我们.{0,20}(?:携手|凝心聚力|共同努力|一起|同心协力)|奋力谱写.{0,10}新篇章")


def check_open_close(text):
    paras = body_paragraphs(text)
    if not paras:
        return []
    res = []
    (no1, first), (no2, last) = paras[0], paras[-1]
    if len(HANZI_RE.findall(first)) > 200:
        res.append(finding("Q-055 开场过长", no1, f"开场 {len(HANZI_RE.findall(first))} 字，须 ≤200 字直切主题", "warn"))
    if OPENING_BAN.search(first):
        res.append(finding("Q-055 开场铺垫", no1, f"开场用了「{OPENING_BAN.search(first).group(0)}」类比喻铺垫", "warn"))
    if len(paras) > 1 and len(HANZI_RE.findall(last)) > 200:
        res.append(finding("Q-056 结尾过长", no2, f"结尾 {len(HANZI_RE.findall(last))} 字，须 ≤200 字", "advice"))
    if ENDING_GENERIC.search(last):
        res.append(finding("Q-056 通用结尾", no2, f"「{ENDING_GENERIC.search(last).group(0)}」可移植到任何文章", "warn"))
    return res


# 字数区间（outline「字数区间：X–Y 字」）：终稿超出区间 20% 以上 block，其余超区间 warn
def check_length(text, outline, final):
    m = re.search(r"字数区间[:：]\s*([\d,，]+)\s*[–\-~～至]\s*([\d,，]+)", outline or "")
    if not m:
        return []
    lo, hi = (int(re.sub(r"[,，]", "", g)) for g in m.groups())
    n = len(re.sub(r"\s", "", text))
    if lo <= n <= hi:
        return []
    far = n < lo * 0.8 or n > hi * 1.2
    return [finding("字数超区间", None, f"全文 {n} 字，大纲区间 {lo}–{hi} 字", "block" if final and far else "warn", gate="W3-4")]


# ---------------- 词典规则（terms.jsonl，单一来源） ----------------

def load_rules(root=None):
    path = (root or common.project_root()) / "20_knowledge/terms/terms.jsonl"
    if not path.exists():
        return []
    return [r for r in (json.loads(l) for l in path.read_text(encoding="utf-8").splitlines())
            if r.get("kind") in ("禁用词", "搭配错误", "套话")]


def check_dictionary(text, rules):
    """禁用词：行业禁忌(PW-203 禁止)→block；绝对化/俗语(PW-201/202)与谨慎词→warn——"所有""完全"
    等在"所有权""完全成本"里正常出现，硬拦会大量误报。搭配错误→block；套话→advice。"""
    res = []
    for no, line in enumerate(text.splitlines(), 1):
        for r in rules:
            term, rule = r["term"], r["rule"]
            if term.replace("...", "") and "..." not in term and term in line:
                if r["kind"] == "搭配错误":
                    # warn 不拦：真实成稿实测，"强化管理"等在正式文件里常见，这张表多是风格偏好
                    res.append(finding("搭配错误", no, f"「{term}」→「{rule.get('correct')}」", "warn"))
                elif r["kind"] == "禁用词":
                    sev = "block" if rule.get("severity") == "禁止" and r["source_id"].startswith("PW-203") else "warn"
                    alt = "/".join(rule.get("replace_with") or []) or rule.get("condition", "")
                    res.append(finding("禁用词", no, f"「{term}」→{alt}", sev))
                else:
                    res.append(finding("套话", no, f"「{term}」→「{rule.get('suggested')}」", "advice"))
    return res


# ---------------- 硬闸 W1-2：判断句 ----------------

TOPIC_RE = re.compile(r"^关于|的(?:若干|几点)?(?:思考|体会|探讨|研究|认识|思路|浅析|初探|调研|情况|问题|建议|意见)$"
                      r"|几点(?:体会|思考|认识|建议)|^浅谈|^浅析|^初探|^刍议|^试论"
                      r"|(?:工作|推进|开展|进展|落实)?(?:情况|总结|汇报|报告|方案|规划|计划|要点|通知)$")
# 谓语词表；首测漏了"已从…进入…"，补了"已/进入/迈向"一族
PREDICATE_RE = re.compile(r"在于|关键|必须|需要|应当|要|能够|才能|已经|已|取得|实现|提升|提高|推动|成为|决定|"
                          r"离不开|有赖于|取决于|不能|就是|得益于|源于|体现|带来|导致|制约|是|有|达到|超过|完成|构建|形成|"
                          r"进入|迈向|迈入|走向|转向|步入|跨入|迈上|走出|打开|扭转|突破|增长|下降|提速|领先|落后")


def check_thesis(sentence):
    s = re.sub(r"^(主旨句|主旨)[:：]\s*", "", sentence.strip()).strip("。")
    if not s or "〔" in s:  # 模板占位说明里带"有""是"，会骗过谓语检测
        return [finding("W1-2 主旨句未填", None, "主旨句为空或仍是模板占位", gate="W1-2")]
    if TOPIC_RE.search(s):
        return [finding("W1-2 话题句", None, f"「{s}」是话题句，须改成带判断的句子", gate="W1-2")]
    if PREDICATE_RE.search(s):
        return []
    return [finding("W1-2 无判断", None, f"「{s}」找不到判断/谓语成分", gate="W1-2")]


# ---------------- 硬闸 W2-4：MECE ----------------

FILLER = set("加强 抓好 做好 严明 推进 推动 提升 提高 持续 深化 强化 切实 全面 进一步 着力 坚持 突出 聚焦 完善 健全 "
             "落实 工作 管理 建设 要求 水平 能力 有力 扎实 不断 大力 积极 更加 实现 确保 构建 打造 进行 开展 "
             "不断 务必 努力 全力 统筹 有效 主要 相关 方面 高质量".split())
# 近义重叠不在代码闸里判（2026-09-25 撤掉近义词表）：原表 {作风,纪律,规矩} 是为迎合本会话自拟的反例
# G-03 加的——作风建设、纪律建设是党的建设中并列的两项，82 份实测误伤；{效率,效能} 误伤"生产组织效能/
# 物流保障效率"。近义层面是语义判断，交 gw-review 的 LLM 审。代码闸只判"去套话后相同/都只剩套话"。
NEAR_SYN = []


FILLER_SORTED = sorted(FILLER, key=len, reverse=True)


def core_words(heading_body):
    """剥掉标点和套话词后剩下的完整字符串。不再丢单字片段——82 份实测："'诊'的方式方法"与
    "'断'的方式方法"只差一个字，丢掉单字后被误判互换无差别。空集 = 只剩套话。"""
    rest = re.sub(r"[，。、；：,.;:\s“”‘’\"'（）()]+", "", heading_body)
    for w in FILLER_SORTED:
        rest = rest.replace(w, "")
    return {rest} if len(rest) >= 2 else set()


def near_synonym(ta, tb):
    """两个标题分别用了同一近义组里的**不同**词（一个"作风"、一个"纪律"）才算近义重叠；
    两边都含同一个词（如都以"高质量"开头）不算——真实成稿回归抓到的误报。"""
    for g in NEAR_SYN:
        ka, kb = {k for k in g if k in ta}, {k for k in g if k in tb}
        if ka and kb and not (ka & kb):
            return True
    return False


def check_mece(headings):
    """同一父级下的同级标题两两比：去套话后相同 → 互换测试不成立；都只剩套话 → 无法区分；近义 → 重叠。"""
    res = []
    for i in range(len(headings)):
        for j in range(i + 1, len(headings)):
            a, b = headings[i], headings[j]
            # 只比标题：随文标题"（一）标题。正文…"取句号前（此前拿整段正文比，子串匹配后误报）
            ta, tb = (re.split(r"[。；！？]", h["body"])[0] for h in (a, b))
            a, b = dict(a, body=ta), dict(b, body=tb)
            ca, cb = core_words(ta), core_words(tb)
            where = a.get("line")
            if not ca and not cb:
                res.append(finding("W2-4 维度不成立", where, f"「{a['body']}」「{b['body']}」去掉套话后都无实质内容", gate="W2-4"))
            elif ta.strip() == tb.strip():
                # 一字不差的重复多是复制/表格注释重复，不是分类维度问题
                res.append(finding("重复标题", where, f"「{ta[:20]}」同级出现两次", "warn", gate="W2-4"))
            elif ca and ca == cb:
                res.append(finding("W2-4 互换测试", where, f"「{a['body']}」「{b['body']}」互换后无差别（核心词都是{sorted(ca)}）", gate="W2-4"))
            elif near_synonym(ta, tb):
                res.append(finding("W2-4 范畴重叠", where, f"「{a['body']}」「{b['body']}」核心词近义，范畴重叠", gate="W2-4"))
    return res


def sibling_groups(text):
    groups, stack = [], {}
    for h in parse_headings(text):
        lv = h["level"]
        for deeper in [k for k in stack if k > lv]:
            groups.append(stack.pop(deeper))
        stack.setdefault(lv, []).append(h)
    groups.extend(stack.values())
    return [g for g in groups if len(g) >= 2]


# ---------------- 硬闸 W3-2：数据基准 ----------------

CHANGE_NUM_RE = re.compile(r"(?:增长|提升|提高|下降|减少|增加|降低|上升|增幅)(?:了)?\s*\d+(?:\.\d+)?\s*(?:%|％|个百分点|倍)")
BASELINE_RE = re.compile(r"同比|环比|较|比上年|比去年|相比|超额?|目标|计划|历史|排名|位居|第[一二三四五六七八九十\d]|高于|低于|"
                         r"完成率|由[^，。]*?(?:提升|提高|增长|下降|降低|减少)至|从[^，。]*?到")
DEGREE_RE = re.compile(r"(?:大幅度?|显著|明显|翻倍|跃升|长足|极大)(?:地)?(?:的)?(?:提升|提高|增长|改善|下降|减少|增强|好转|进步|上升)")


def section_after(sents, k):
    """标题句的支撑在整节正文里：取到下一个同级或更高级标题为止。"""
    lv = next((lv for lv, p in HEADING_PATTERNS if p.match(clean_line(sents[k]))), None)
    out = []
    for s in sents[k + 1:]:
        nxt = next((l for l, p in HEADING_PATTERNS if p.match(clean_line(s))), None)
        if nxt is not None and nxt <= lv:
            break
        out.append(s)
    return "".join(out)


def check_baseline(text):
    res = []
    sents = [s for s in re.split(r"(?<=[。！？；\n])", text) if s.strip()]
    for k, s in enumerate(sents):
        if CHANGE_NUM_RE.search(s) and not BASELINE_RE.search(s):
            res.append(finding("W3-2 无对比基准", None, f"「{s.strip()[:30]}」有增减数字但无同比/目标/历史等基准", gate="W3-2"))
        if DEGREE_RE.search(s):
            is_heading = any(p.match(clean_line(s)) for _, p in HEADING_PATTERNS)
            support = section_after(sents, k) if is_heading else "".join(sents[k:k + 3])
            if not re.search(r"\d", support):
                where = "整节正文" if is_heading else "3句内"
                res.append(finding("W3-2 程度副词无数字", None, f"「{s.strip()[:30]}」用了程度副词，{where}无数字印证", gate="W3-2"))
    return res


# ---------------- 落盘产物：outline.md / review_report.md（P3.3 模板） ----------------

PLACEHOLDER_RE = re.compile(r"〔[^〕]*〕")


def table_rows(text, section):
    """返回某个 ## 小节下 Markdown 表格的数据行（去掉表头和分隔行）。"""
    m = re.search(r"^##\s*[一二三四五六七八九十、\s]*" + section + r".*?$(.*?)(?=^##\s|\Z)", text, re.M | re.S)
    if not m:
        return None
    rows = [l for l in m.group(1).splitlines() if l.strip().startswith("|")]
    return [[c.strip() for c in l.strip().strip("|").split("|")] for l in rows[2:]]


def check_outline(outline):
    res = []
    rows = table_rows(outline, "论点地图")
    filled = [r for r in (rows or []) if r and r[0] and not PLACEHOLDER_RE.fullmatch(r[1] if len(r) > 1 else "〔〕")]
    if not filled:
        res.append(finding("W2-5 论点地图缺失", None, "outline 没有已填写的论点地图（W5-3 核销依据）", gate="W2-4"))
    ids = [r[0] for r in filled]
    for dup in {i for i in ids if ids.count(i) > 1}:
        res.append(finding("W2-5 论点编号重复", None, f"{dup} 重复登记", gate="W2-4"))
    claims = [r[1] for r in filled if len(r) > 1]
    for dup in {c for c in claims if claims.count(c) > 1}:
        res.append(finding("W2-5 论点多处登记", None, f"「{dup[:20]}」登记了多个位置——设计阶段就已流窜", gate="W2-4"))
    for r in filled:
        if len(r) < 3 or not r[2] or PLACEHOLDER_RE.fullmatch(r[2]):
            res.append(finding("W2-5 论点无归属", None, f"{r[0]} 未写唯一归属位置", gate="W2-4"))
    left = [l.strip() for l in outline.splitlines() if PLACEHOLDER_RE.search(l) and "待补" not in l and not l.strip().startswith("<!--")]
    if left:
        res.append(finding("模板占位未填", None, f"{len(left)} 行仍有〔…〕占位，例：{left[0][:30]}", "warn"))
    return res


def check_report(report):
    """review_report：红线零容忍、待裁决不得呈报（R5）、3 轮上限暂停上报（10章§六②）。"""
    res = []
    gates = table_rows(report, "20 条硬门禁") or []
    if not gates:
        res.append(finding("报告缺门禁表", None, "review_report 未找到 20 条硬门禁表", gate="W5-4"))
    for r in gates:
        if len(r) >= 5 and "红线" in r[2] and "✅" not in r[4]:
            res.append(finding("红线未过", None, f"红线「{r[1]}」判定为「{r[4] or '空'}」——零容忍，不得呈报", gate="W5-4"))
    for r in table_rows(report, "待人工裁决项") or []:
        if r and r[-1] == "待裁决" and any(c for c in r[1:-1]):
            res.append(finding("R5 待裁决未处理", None, f"第{r[0]}项仍为待裁决，须 Jeffrey 明示处理", gate="W5-4"))
    for r in table_rows(report, "轮次记录") or []:
        if len(r) >= 4 and re.search(r"3\s*/\s*3", r[2]) and "未过" in r[3]:
            res.append(finding("3 轮上限", None, f"{r[0]} 已 3 轮未过——暂停上报人工裁决，问题多半在上层", gate="W5-2"))
    return res


# ---------------- R6 判断溯源（2026-09-29，P4 两轮头号漏检） ----------------
# 机器只做两件事：①把带因果/定性标记的句子全部挑出来；②核对每句都在 review_report「判断溯源表」
# 里登记且写了出处。出处对不对是人工的事，机器保证“逐条过、留痕、可抽查”。

JUDGE_RE = re.compile(
    # 因果
    r"原因在于|根因(?:是|在于)|根源在于|归因于|导致|造成了|致使|使得|从而|因此|因而|所以|由于|得益于"
    r"|表明|说明了|证明|可见"
    # 成效定性
    r"|解决了|破解了|奠定了|打下了|夯实了|实现了.{0,12}转变|有了|确保了|大多数|普遍"
    r"|关键在于|前提是|(?<![一二三四五六七八九十])是[^，。；]{1,16}的(?:关键|前提|基础|保障|根本|抓手)(?!举措)"
    # 问题定性（对单位现状的负面判断，最容易编）
    r"|不足|缺少|缺乏|不够|差距|不一致|不清晰|不统一|不齐|滞后|薄弱|偏少|偏低"
    r"|完整(?!性)|显著|有效(?!性|期)")
NORM_RE = re.compile(r"[^一-鿿0-9A-Za-z]")


def judgment_sentences(text):
    """正文里带因果/定性标记的句子（跳过标题和表格行）。"""
    body = "\n".join(l for l in text.splitlines() if not re.match(r"^\s*(#|\|)", l))
    return [s.strip() for s in re.split(r"(?<=[。！？；])|\n", body) if s.strip() and JUDGE_RE.search(s)]


def check_trace(text, report):
    """R6：每句判断都要在「判断溯源表」登记、有出处；结论为“无出处”的不得进终稿。"""
    rows = table_rows(report, "判断溯源")
    if rows is None:
        return [finding("R6 溯源表缺失", None, "review_report 没有「判断溯源表」小节", gate="W5-4")]
    res, keys = [], []
    for r in rows:
        if len(r) < 4 or not r[1] or PLACEHOLDER_RE.fullmatch(r[1]):
            continue
        if not r[2] or PLACEHOLDER_RE.fullmatch(r[2]) or "无出处" in r[3]:
            res.append(finding("R6 判断无出处", None, f"「{r[1][:30]}」没有素材出处——删除或改写后重登", gate="W5-4"))
        keys.append(NORM_RE.sub("", r[1])[:12])
    for s in judgment_sentences(text):
        norm = NORM_RE.sub("", s)
        if not any(k and k in norm for k in keys):
            res.append(finding("R6 判断未溯源", None, f"「{s[:30]}」含因果/定性判断，未在判断溯源表登记", gate="W5-4"))
    return res


# ---------------- R7 逐段审表（2026-10-01，P4 第 2 轮 8 处段落层漏检） ----------------
# 门禁表里“段首句可还原主线 ✅”一行打勾就过，模型自评即放行；R6 强制逐句填表后当轮就抓出主语偷换。
# R7 与 R6 同构：机器只核对“每段都有一行、四列写实、结论不是不通过”，写得对不对由人抽查。

R7_MIN_PARA = 40       # 去标点后不足 40 字的过渡句（“现将主要做法介绍如下”）不要求登记
R7_KEY_LEN = 10        # 段首摘录去标点后取前 10 字，须是段落的前缀
R7_TICK_RE = re.compile(r"^[\s✅✓√☑无—\-－/／、，,。.]*$")
HEAD_NUM_RE = re.compile(r"^(?:第[一二三四五六七八九十]+(?:部分|篇|章)|[一二三四五六七八九十]+\s*、"
                         r"|[（(]\s*[一二三四五六七八九十\d]+\s*[）)]|\d+\s*[.．、](?!\d))\s*")


def paragraphs_with_heading(text):
    """[(行号, 段落文本, 所在最近一级标题的正文)]，段落口径同 body_paragraphs。"""
    out, heading = [], ""
    for no, raw in enumerate(text.splitlines(), 1):
        line = raw.strip()
        if not line or line.startswith("|"):
            continue
        if is_heading(raw):
            heading = HEAD_NUM_RE.sub("", clean_line(raw))
            continue
        out.append((no, line, heading))
    return out


def check_paragraphs(text, report):
    """R7：正文每段（≥40 字）都要在「逐段审表」登记一行，主旨/跑题句/衔接/口径四列写实，结论不得为“不通过”。
    表列：# | 位置 | 段首摘录 | 本段主旨 | 跑题句 | 与上下段衔接 | 概念/数据口径核对 | 结论"""
    rows = table_rows(report, "逐段审")
    if rows is None:
        return [finding("R7 逐段审表缺失", None, "review_report 没有「逐段审表」小节", gate="W5-4")]
    res, filled = [], []
    for r in rows:
        if len(r) < 8 or not r[2] or PLACEHOLDER_RE.search(r[2]):
            continue
        filled.append((NORM_RE.sub("", r[2])[:R7_KEY_LEN], r))
    for no, para, heading in paragraphs_with_heading(text):
        norm = NORM_RE.sub("", para)
        if len(norm) < R7_MIN_PARA:
            continue
        hit = next((r for key, r in filled if len(key) == R7_KEY_LEN and norm.startswith(key)), None)
        if hit is None:
            res.append(finding("R7 段落未审", no, f"「{para[:20]}」未在逐段审表登记", gate="W5-4"))
            continue
        thesis, offtopic, link, caliber, verdict = (c.strip() for c in hit[3:8])
        if "不通过" in verdict:
            res.append(finding("R7 段落审查未过", no, f"「{para[:20]}」逐段审结论为不通过——改稿后重审", gate="W5-4"))
        lazy = []
        thesis_norm = NORM_RE.sub("", thesis)
        if len(thesis_norm) < 8 or (heading and thesis_norm == NORM_RE.sub("", heading)):
            lazy.append("本段主旨")
        if not offtopic:
            lazy.append("跑题句")
        if R7_TICK_RE.match(link):
            lazy.append("衔接")
        if R7_TICK_RE.match(caliber):
            lazy.append("口径")
        if lazy:
            res.append(finding("R7 只打勾未留痕", no, f"「{para[:20]}」的{'、'.join(lazy)}列没有写实（不许只打勾或照抄标题）",
                               gate="W5-4"))
    return res


# ---------------- 汇总 ----------------

def lint(text, outline=None, final=False, rules=None):
    rules = load_rules() if rules is None else rules
    res = (check_quotes(text) + check_numbering(text) + check_shi_series(text) + check_total_parts(text)
           + check_long_clauses(text) + check_delete_list(text) + check_title_punct(text)
           + check_vague_time(text) + check_placeholder(text, final) + check_dictionary(text, rules)
           + check_baseline(text)
           + check_policy_order(text) + check_sige(text) + check_wrong_forms(text) + check_numbering_format(text)
           + check_number_format(text) + check_data_density(text) + check_long_paragraph(text) + check_rhythm(text)
           + check_same_lead(text) + check_open_close(text))
    for g in sibling_groups(text):
        res += check_mece(g)
    if outline:
        thesis = next((l for l in outline.splitlines() if re.match(r"^\s*#*\s*\**\s*主旨", l)), None)
        if thesis:
            res += check_thesis(clean_line(thesis))
        else:
            res.append(finding("W1-2 缺主旨句", None, "outline 未找到「主旨句：」行", gate="W1-2"))
        for g in sibling_groups(outline):
            res += check_mece(g)
        res += check_outline(outline)
        res += check_length(text, outline, final)
    return res


def main(argv):
    args = list(argv)
    outline_path = None
    final = "--final" in args
    as_json = "--json" in args
    args = [a for a in args if a not in ("--final", "--json")]
    report_path = None
    for flag in ("--outline", "--report"):
        if flag in args:
            i = args.index(flag)
            if flag == "--outline":
                outline_path = Path(args[i + 1])
            else:
                report_path = Path(args[i + 1])
            del args[i:i + 2]
    text = Path(args[0]).read_text(encoding="utf-8")
    outline = outline_path.read_text(encoding="utf-8") if outline_path else None
    res = lint(text, outline, final)
    if report_path:
        report = report_path.read_text(encoding="utf-8")
        res += check_report(report)
        if final:
            res += check_trace(text, report) + check_paragraphs(text, report)
    elif final:
        res.append(finding("R6 缺审校报告", None, "终验必须带 --report review_report.md（不生成不得呈报）", gate="W5-4"))
    if as_json:
        print(json.dumps(res, ensure_ascii=False, indent=1))
    else:
        for r in sorted(res, key=lambda r: ({"block": 0, "warn": 1, "advice": 2}[r["severity"]], r["line"] or 0)):
            print(f"[{r['severity']}] {r['gate']} {r['rule']} 第{r['line'] or '-'}行：{r['msg']}")
    blocks = sum(r["severity"] == "block" for r in res)
    print(f"机检：block {blocks} / warn {sum(r['severity'] == 'warn' for r in res)} / "
          f"advice {sum(r['severity'] == 'advice' for r in res)}" + ("——不通过，不进入人工/LLM 环节" if blocks else "——通过"))
    return 1 if blocks else 0


if __name__ == "__main__":
    common.force_utf8_stdout()
    sys.exit(main(sys.argv[1:]))
