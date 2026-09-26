import jieba

from t2_collocation import collect, top, neighbor


def _stats(texts, terms):
    for t in terms:
        jieba.add_word(t, freq=10 ** 6)
    return collect(texts, set(terms))


def test_before_after_counts():
    texts = ["要深化卷烟营销改革。"] * 3 + ["持续深化卷烟营销改革。"]
    freq, before, after, _ = _stats(texts, ["卷烟营销"])
    assert freq["卷烟营销"] == 4
    assert before["卷烟营销"]["深化"] == 4
    assert after["卷烟营销"]["改革"] == 4


def test_skips_function_words_but_not_punctuation():
    tokens = ["推进", "的", "卷烟营销", "，", "改革"]
    assert neighbor(tokens, 2, -1) == "推进"
    assert neighbor(tokens, 2, +1) is None


def test_min_count_and_place_filter():
    from collections import Counter
    c = Counter({"深化": 5, "长沙": 9, "偶尔": 2})
    assert top(c, known_names=()) == ["深化"]


def test_drops_quantifiers_prepositions_generic_nouns():
    from collections import Counter
    c = Counter({"五家": 9, "关于": 8, "公司": 7, "深化": 6, "全面": 5, "各个": 5, "推进": 4})
    assert top(c, ()) == ["深化", "全面", "推进"]


def test_known_name_filtered():
    from collections import Counter
    assert top(Counter({"王建华": 5, "推进": 4}), known_names=("王建华",)) == ["推进"]


def test_collocate_concentrated_in_few_docs_dropped():
    """宏达只在 1 份文件里扎堆出现 10 次，推进分布在 6 份文件里。"""
    texts = ["宏达物流中心" * 10] + ["推进物流中心建设"] * 6
    freq, before, after, df = _stats(texts, ["物流中心"])
    assert top(before["物流中心"], (), df, ("物流中心", "前")) == ["推进"]


def test_official_rules_merged_with_kind(tmp_path):
    import json
    from t2_collocation import official_rule_rows
    d = tmp_path / "20_knowledge/terms"
    d.mkdir(parents=True)
    (d / "official_terms_解构.jsonl").write_text("\n".join(json.dumps(x, ensure_ascii=False) for x in [
        {"id": "PW-201-01", "category": "禁用词", "banned": "最好的", "replace_with": ["较好的"]},
        {"id": "MM-301-01", "category": "搭配", "wrong": "制定规划", "correct": "编制规划"},
        {"id": "CP-401-01", "category": "套话", "original": "与此同时", "suggested": "同时"},
    ]), encoding="utf-8")
    rows = official_rule_rows(tmp_path, 391)
    assert [(r["id"], r["kind"], r["term"]) for r in rows] == [
        ("T-00391", "禁用词", "最好的"), ("T-00392", "搭配错误", "制定规划"), ("T-00393", "套话", "与此同时")]
    assert rows[1]["rule"]["correct"] == "编制规划"
