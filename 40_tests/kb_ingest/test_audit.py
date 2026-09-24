import json

from conftest import make_record
import common
import kb_audit
import vocab


def write_lib(tmp_root, records):
    f = common.qa_dir() / vocab.QA_FILENAMES[1]
    f.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in records) + "\n",
                 encoding="utf-8")


def test_clean_library_passes(tmp_root):
    write_lib(tmp_root, [make_record(tmp_root)])
    errors, _ = kb_audit.audit()
    assert errors == []


def test_duplicate_id_detected(tmp_root):
    r1 = make_record(tmp_root)
    r2 = make_record(tmp_root, answer=r1["answer"].replace("请示", "批复"))
    r2["id"] = r1["id"]  # 故意重复
    write_lib(tmp_root, [r1, r2])
    errors, _ = kb_audit.audit(fast=True)
    assert any("id 重复" in e for e in errors)


def test_duplicate_hash_detected(tmp_root):
    r1 = make_record(tmp_root)
    r2 = make_record(tmp_root, id="QA-C1-00002")
    write_lib(tmp_root, [r1, r2])
    errors, _ = kb_audit.audit(fast=True)
    assert any("answer_hash 重复" in e for e in errors)


def test_broken_json_detected(tmp_root):
    f = common.qa_dir() / vocab.QA_FILENAMES[1]
    f.write_text('{"id": 坏掉的JSON\n', encoding="utf-8")
    errors, _ = kb_audit.audit(fast=True)
    assert any("JSON 解析失败" in e for e in errors)


def test_banned_filename_detected(tmp_root):
    (tmp_root / "knowledge" / "规则_v2.yaml").write_text("x", encoding="utf-8")
    errors, _ = kb_audit.audit()
    assert any("禁用命名" in e for e in errors)
