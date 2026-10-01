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
    (tmp_root / "20_knowledge" / "规则_v2.yaml").write_text("x", encoding="utf-8")
    errors, _ = kb_audit.audit()
    assert any("禁用命名" in e for e in errors)


def test_banned_name_inside_dot_dir_is_skipped(tmp_root):
    """.venv/.git 等点号目录整棵子树都不扫——第三方依赖代码里常见 _final 这类误命中。"""
    nested = tmp_root / ".venv" / "lib" / "some_final_module.py"
    nested.parent.mkdir(parents=True)
    nested.write_text("x", encoding="utf-8")
    errors, _ = kb_audit.audit()
    assert not any("some_final_module" in e for e in errors)


def test_banned_name_in_source_archive_legacy_is_skipped(tmp_root):
    """原始素材、前期归档、legacy 存档保留原名，不报禁用命名。"""
    for rel in ("10_source/raw_materials/方案_v3.2_完成版.md",
                "99_前期资料/02_Dify部署/GUIDE_v2.md",
                "20_knowledge/terms/legacy/official_terms_v2.yaml"):
        f = tmp_root / rel
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text("x", encoding="utf-8")
    errors, _ = kb_audit.audit()
    assert not any("禁用命名" in e for e in errors)


def test_legacy_dir_name_itself_does_not_exempt_siblings(tmp_root):
    """豁免只看上级目录；legacy 目录外的同名违规照报。"""
    (tmp_root / "20_knowledge" / "terms").mkdir(parents=True)
    (tmp_root / "20_knowledge" / "terms" / "词典_v2.yaml").write_text("x", encoding="utf-8")
    errors, _ = kb_audit.audit()
    assert any("词典_v2.yaml" in e for e in errors)


def test_project_structure_md_allowed_at_root(tmp_root):
    (tmp_root / "PROJECT_STRUCTURE.md").write_text("x", encoding="utf-8")
    errors, _ = kb_audit.audit()
    assert not any("PROJECT_STRUCTURE.md" in e for e in errors)
