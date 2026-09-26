from collections import Counter

from term_candidates import ngrams, select


def test_ngrams_adjacent_content_words_only():
    grams = list(ngrams(["深化", "卷烟", "营销", "，", "网络", "的", "建设"]))
    assert "卷烟营销" in grams and "深化卷烟营销" in grams
    assert "营销网络" not in grams   # 隔着标点
    assert "网络建设" not in grams   # 隔着虚词


def test_gate_requires_root_freq_docs_and_not_place():
    freq = Counter({"卷烟营销": 500, "贯彻落实": 900, "长沙卷烟": 300, "烟叶收购": 80, "精益物流": 150})
    df = Counter({"卷烟营销": 40, "贯彻落实": 90, "长沙卷烟": 30, "烟叶收购": 20, "精益物流": 3})
    cands, accepted = select(freq, df, known_terms=set())
    assert [r["term"] for r in accepted] == ["卷烟营销"]
    # 贯彻落实：无行业词根；长沙卷烟：地名；烟叶收购：频次<100；精益物流：只在3份文件里
    assert {r["term"] for r in cands} == {"卷烟营销", "贯彻落实", "长沙卷烟", "烟叶收购", "精益物流"}


def test_known_terms_excluded():
    cands, _ = select(Counter({"卷烟营销": 500}), Counter({"卷烟营销": 40}), known_terms={"卷烟营销"})
    assert cands == []


def test_structural_junk_four_classes():
    from term_candidates import structural_junk
    for junk in ["推进精益", "提升卷烟营销", "全省烟草", "五家卷烟厂", "精益管理工作",
                 "卷烟非法", "烟草物流有限责任", "物流中心卷烟仓库"]:
        assert structural_junk(junk), junk
    for good in ["精益管理", "卷烟营销", "现代终端", "货源投放", "原料醇化", "再造烟叶",
                 "中式卷烟", "卷烟非法流通", "终端建设", "精益十佳"]:
        assert not structural_junk(good), good
