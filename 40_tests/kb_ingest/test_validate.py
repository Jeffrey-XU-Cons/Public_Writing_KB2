from conftest import make_record
from kb_validate import validate_record


def test_valid_record_passes(tmp_root):
    assert validate_record(make_record(tmp_root)) == []


def test_missing_field_fails(tmp_root):
    rec = make_record(tmp_root)
    del rec["scenarios"]
    assert any("缺失必填字段" in e for e in validate_record(rec))


def test_bad_id_fails(tmp_root):
    rec = make_record(tmp_root, id="QA-C7-00001")
    assert any("id 格式错误" in e for e in validate_record(rec))


def test_short_answer_fails(tmp_root):
    rec = make_record(tmp_root, answer="太短的答案。")
    assert any("下限" in e for e in validate_record(rec))


def test_wrong_l2_for_category_fails(tmp_root):
    rec = make_record(tmp_root, category_l2="模块写法")  # 模块写法属 C3 而非 C1
    assert any("受控词表" in e for e in validate_record(rec))


def test_straight_quote_fails(tmp_root):
    rec = make_record(tmp_root, answer='含英文引号 "quoted" 的答案' + "。" * 80)
    assert any("直引号" in e for e in validate_record(rec))


def test_hash_mismatch_fails(tmp_root):
    rec = make_record(tmp_root)
    rec["answer_hash"] = "000000000000"
    assert any("answer_hash" in e for e in validate_record(rec))


def test_too_few_questions_fails(tmp_root):
    rec = make_record(tmp_root, question="只有一个问题？")
    assert any("问法数量" in e for e in validate_record(rec))


def test_broken_source_path_fails(tmp_root):
    rec = make_record(tmp_root, source_path=str(tmp_root / "不存在.md"))
    assert any("断链" in e for e in validate_record(rec))


def test_method_type_needs_reverse_question(tmp_root):
    rec = make_record(
        tmp_root,
        answer_type="方法型",
        answer="方法论答案。" * 80,
        question="怎么写好开头？ / 开头有哪些写法？ / 如何让开头出彩？",
    )
    assert any("反向问法" in e for e in validate_record(rec))


# --- P1.3：depth/enforce/w_layer + 最小挂钩链（可选字段，出现才校验） ---

def test_record_without_depth_still_passes(tmp_root):
    """现有 34 条未打标，回填前不能被判不合格。"""
    assert validate_record(make_record(tmp_root)) == []


def test_invalid_depth_fails(tmp_root):
    rec = make_record(tmp_root, depth="不存在的等级")
    assert any("depth 非法" in e for e in validate_record(rec))


def test_axiom_without_governs_fails(tmp_root):
    rec = make_record(tmp_root, depth="axiom")
    assert any("必须填 governs" in e for e in validate_record(rec))


def test_axiom_with_governs_passes(tmp_root):
    rec = make_record(tmp_root, depth="axiom", governs=[1, 3, 4])
    assert validate_record(rec) == []


def test_axiom_governs_bad_category_fails(tmp_root):
    rec = make_record(tmp_root, depth="axiom", governs=[9])
    assert any("governs 含非法大类" in e for e in validate_record(rec))


def test_technique_without_implements_fails(tmp_root):
    rec = make_record(tmp_root, depth="technique")
    assert any("必须填 implements" in e for e in validate_record(rec))


def test_technique_with_implements_passes(tmp_root):
    rec = make_record(tmp_root, depth="technique", implements=["QA-C3-00002"])
    assert validate_record(rec) == []


def test_method_without_derives_from_fails(tmp_root):
    rec = make_record(tmp_root, depth="method")
    assert any("必须填 derives_from" in e for e in validate_record(rec))


def test_invalid_enforce_fails(tmp_root):
    rec = make_record(tmp_root, enforce="拦不住")
    assert any("enforce 非法" in e for e in validate_record(rec))


def test_valid_enforce_passes(tmp_root):
    rec = make_record(tmp_root, enforce="hard")
    assert validate_record(rec) == []


def test_invalid_w_layer_fails(tmp_root):
    rec = make_record(tmp_root, w_layer=["W9"])
    assert any("w_layer" in e for e in validate_record(rec))


def test_multi_w_layer_passes(tmp_root):
    rec = make_record(tmp_root, w_layer=["W2", "W3"])
    assert validate_record(rec) == []
