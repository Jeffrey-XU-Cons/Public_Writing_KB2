"""Dictionary candidate terms (07章 §2.4, 11章 P2.5; gate decided 11章§五③).

The original 1,242-candidate list behind 07章 §2.1 was never saved; this recomputes it.
Candidate = 2-3 adjacent content tokens (each >=2 chars, no punctuation/function word between),
4-8 chars joined, corpus freq >= 60, not already in the dictionary.
Accepted  = candidate with freq >= 100 AND an industry root, spread over >= 5 files,
            and not a place/unit/person name.

CLI: python term_candidates.py [OUT_DIR]   -> candidates.jsonl (all >=60) + candidates_accepted.jsonl
"""

import json
import sys
from collections import Counter
from pathlib import Path

import jieba

sys.path.insert(0, str(Path(__file__).resolve().parent))
import common
import t2_collocation as t2

CANDIDATE_MIN = 60
ACCEPT_MIN = 100
MIN_DOCS = 5
# 07章 §2.4 列的词根 + 同类烟草生产/营销专有字眼（通用公文词如"贯彻落实""质量管理"不收）
ROOTS = ["卷烟", "烟叶", "烟草", "专卖", "终端", "货源", "配送", "精益", "对标", "成熟度",
         "零售户", "烟农", "烟站", "复烤", "醇化", "制丝", "卷接", "烟用", "打叶", "烟丝", "细支", "中支"]


# 首跑 439 个人工过目后归纳的四类非词条（2026-09-25）：
# 动词+术语（推进精益、提升卷烟营销）属 T2 搭配层；范围修饰（全省烟草、五家卷烟厂）；
# "X工作/X水平"；跨词界碎片与公司全称残片（卷烟非法、烟草物流有限责任）
VERB_HEAD = set("推进 开展 提升 推动 实现 深化 运用 提高 实施 导入 形成 打造 推行 规范 确保 促进 构建 "
                "加强 营造 优化 围绕 完善 应用 强化 制定 成立 按照 建立 完成 降低 做好 树立 建设 "
                "全面推进 深入推进 当前 引入 落实 坚持 助力 保障 发挥 做强 组织 收购 销售 经营".split())
SCOPE_HEAD = ("全省", "全市", "全国", "省级", "省内", "省外", "行业", "年度", "人均", "分公司",
              "物流分公司", "物流中心", "中心", "五家", "五个", "各", "烟草卷烟", "全面推进", "深入推进")
BAD_TAIL = ("工作", "水平", "实施", "推进", "人均", "区域", "实际", "规范", "非法", "异常", "前置",
            "综合", "循环", "成品", "仓库")
ORG_FRAGMENT = ("有限责任", "有限公司", "分公司")


def structural_junk(term):
    tokens = jieba.lcut(term, HMM=False)
    return (tokens[0] in VERB_HEAD or term.startswith(SCOPE_HEAD) or term.endswith(BAD_TAIL)
            or any(f in term for f in ORG_FRAGMENT))


def ngrams(tokens):
    run = []
    for tok in tokens + [""]:
        if len(tok) >= 2 and t2.HAN_RE.match(tok) and tok not in t2.SKIP and tok not in t2.LIGHT:
            run.append(tok)
            continue
        for n in (2, 3):
            for i in range(len(run) - n + 1):
                g = "".join(run[i:i + n])
                if 4 <= len(g) <= 8:
                    yield g
        run = []


def count(texts):
    freq, df = Counter(), Counter()
    for text in texts:
        grams = list(ngrams(jieba.lcut(text, HMM=False)))
        freq.update(grams)
        df.update(set(grams))
    return freq, df


def select(freq, df, known_terms, known_names=()):
    cands, accepted = [], []
    for g, f in freq.most_common():
        if f < CANDIDATE_MIN:
            break
        if g in known_terms:
            continue
        row = {"term": g, "corpus_freq": f, "doc_freq": df[g]}
        cands.append(row)
        if (f >= ACCEPT_MIN and df[g] >= MIN_DOCS and any(r in g for r in ROOTS)
                and not structural_junk(g) and not t2.is_sensitive(g, known_names)):
            accepted.append(row)
    return cands, accepted


def main(argv):
    root = common.project_root()
    out_dir = Path(argv[0]) if argv else root / "20_knowledge/terms"
    terms = t2.load_terms(root)
    for t in terms:
        if t2.HAN_RE.match(t):
            jieba.add_word(t, freq=10 ** 6)
    texts = [t2.FRONTMATTER_RE.sub("", p.read_text(encoding="utf-8"), count=1) for p in t2.corpus_files(root)]
    freq, df = count(texts)
    cands, accepted = select(freq, df, set(terms))
    for name, rows in (("candidates.jsonl", cands), ("candidates_accepted.jsonl", accepted)):
        (out_dir / name).write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows), encoding="utf-8")
    print(f"语料 {len(texts)} 份；候选（频次≥{CANDIDATE_MIN}、词典未收）{len(cands)} 个；"
          f"入库门槛（≥{ACCEPT_MIN}、含行业词根、≥{MIN_DOCS} 份文件、非地名单位人名）通过 {len(accepted)} 个")
    return 0


if __name__ == "__main__":
    common.force_utf8_stdout()
    sys.exit(main(sys.argv[1:]))
