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
