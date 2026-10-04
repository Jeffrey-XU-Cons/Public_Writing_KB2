"""范文库 articles.jsonl 校验（kb_validate.validate_article）与审计接入。"""

import json

from kb_validate import validate_article


def make_article(root, **over):
    rec = {
        "id": "AR-0001",
        "title": "在〔甲地〕企业管理工作会议上的讲话",
        "doc_type": "讲话稿",
        "subtype": "启动部署讲话",
        "org_level": "地市级",
        "industry": "烟草",
        "summary": "分管领导在启动会上讲三点意见：认识、关键、落实。",
        "skeleton": ["一、深刻认识重要性", "二、牢牢把握关键", "三、科学统筹落实"],
        "why_good": ["一", "二", "三"],
        "must_haves": ["开场交代分工", "领导带头", "方案只点名", "结尾锚定听众"],
        "linked_qa": [],
        "source_path": "source/source_doc.md",
        "grade": "A",
        "batch_id": "B-20261004-AR-01",
    }
    rec.update(over)
    return rec


def test_valid_article_passes(tmp_root):
    assert validate_article(make_article(tmp_root)) == []


def test_bad_subtype_and_level_fail(tmp_root):
    errs = validate_article(make_article(tmp_root, subtype="随便讲讲", org_level="市局"))
    assert any("subtype" in e for e in errs) and any("org_level" in e for e in errs)


def test_grade_b_needs_caveat_and_c_rejected(tmp_root):
    assert any("caveat" in e for e in validate_article(make_article(tmp_root, grade="B")))
    assert validate_article(make_article(tmp_root, grade="B", caveat="部署段缺时间节点")) == []
    assert any("C 级不入库" in e for e in validate_article(make_article(tmp_root, grade="C")))


def test_counts_paths_and_quotes(tmp_root):
    assert any("must_haves" in e for e in validate_article(make_article(tmp_root, must_haves=["只有一条"])))
    assert any("source_path" in e for e in validate_article(make_article(tmp_root, source_path="nope.md")))
    assert any("linked_qa" in e for e in validate_article(make_article(tmp_root, linked_qa=["AR-0002"])))
    assert any("弯引号" in e for e in validate_article(make_article(tmp_root, summary="讲了「三点」")))


def test_audit_flags_dangling_linked_qa(tmp_root):
    import kb_audit
    art_dir = tmp_root / "20_knowledge" / "articles"
    art_dir.mkdir(parents=True)
    rec = make_article(tmp_root, linked_qa=["QA-C5-00099"])
    (art_dir / "articles.jsonl").write_text(json.dumps(rec, ensure_ascii=False) + "\n", encoding="utf-8")
    errors, _ = kb_audit.audit()
    assert any("linked_qa 指向不存在的 QA" in e for e in errors)
