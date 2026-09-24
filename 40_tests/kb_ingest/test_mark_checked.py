import json

from conftest import make_record
import common
import kb_mark_checked
import vocab


def write_lib(tmp_root, records):
    f = common.qa_dir() / vocab.QA_FILENAMES[1]
    f.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in records) + "\n",
                 encoding="utf-8")


def read_lib(tmp_root):
    f = common.qa_dir() / vocab.QA_FILENAMES[1]
    return [json.loads(l) for l in f.read_text(encoding="utf-8").splitlines() if l.strip()]


def test_mark_sets_checked_true(tmp_root):
    r = make_record(tmp_root, batch_id="B-20260706-01", quality_checked=False)
    write_lib(tmp_root, [r])
    assert kb_mark_checked.mark_batch("B-20260706-01") == 0
    assert read_lib(tmp_root)[0]["quality_checked"] is True


def test_mark_with_grade(tmp_root):
    r = make_record(tmp_root, batch_id="B-20260706-01")
    write_lib(tmp_root, [r])
    assert kb_mark_checked.mark_batch("B-20260706-01", grade="A") == 0
    assert read_lib(tmp_root)[0]["quality_grade"] == "A"


def test_mark_unknown_batch_noop(tmp_root):
    write_lib(tmp_root, [make_record(tmp_root, batch_id="B-20260706-01")])
    assert kb_mark_checked.mark_batch("B-99999999-99") == 1
