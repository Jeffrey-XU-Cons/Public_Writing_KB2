"""P3.4–3.6 三个 skill 的结构检查。skill 是给模型读的说明，逻辑正确性要到 P4 真实任务才测得出；
这里只验证能机械验证的：路径真实存在、给出的命令能跑、正文不带客户人名单位名。"""

import re
import subprocess
import sys
from pathlib import Path

import pytest

import deidentify

ROOT = Path(__file__).resolve().parents[2]
SKILLS = ROOT / ".claude/skills"
NAMES = ["gongwen", "gw-draft", "gw-review", "draft"]  # draft：2026-10-03 由全局迁入（Kb-RAG D-068）


def read(name):
    return (SKILLS / name / "SKILL.md").read_text(encoding="utf-8")


@pytest.mark.parametrize("name", NAMES)
def test_frontmatter(name):
    m = re.match(r"^---\nname: (.+)\ndescription: (.+)\n---\n", read(name))
    assert m and m.group(1) == name and len(m.group(2)) > 20


@pytest.mark.parametrize("name", NAMES)
def test_referenced_paths_exist(name):
    """SKILL.md 里反引号中的路径都要真实存在（占位写法 X_/…/* 跳过）。"""
    missing = []
    for p in re.findall(r"`([^`\s]+\.(?:md|py|jsonl))`", read(name)):
        if any(t in p for t in ("…", "*", "X_", "YYYY")) or "/" not in p:
            continue  # 不带目录的是任务目录里将生成的产物名（outline.md 等），不是 skill 自带文件
        base = ROOT if p.startswith(("30_engine", "20_knowledge", "90_design", "40_tests")) else SKILLS / name
        if not (base / p).exists():
            missing.append(p)
    assert not missing, missing


def test_gongwen_avoids_bare_trigger():
    desc = re.search(r"description: (.+)", read("gongwen")).group(1)
    assert "不响应裸的「起草」「写材料」" in desc


def test_gw_draft_retrieval_command_runs():
    """gw-draft 给出的临时检索命令要真能查到东西。"""
    cmd = next(l for l in read("gw-draft").splitlines() if l.startswith("python3 -c"))
    code = re.search(r'python3 -c "(.+)" (\S+)$', cmd)
    out = subprocess.run([sys.executable, "-c", code.group(1), code.group(2)], cwd=ROOT,
                         capture_output=True, text=True, timeout=60, stdin=subprocess.DEVNULL)
    assert out.returncode == 0, out.stderr
    assert "QA-C3-00001" in out.stdout


def test_lint_command_forms_in_skills_run(tmp_path):
    """SKILL.md 里用到的 draft_lint 参数组合都要能跑（不崩，退出码 0/1）。"""
    task = tmp_path / "t"
    task.mkdir()
    outline = (SKILLS / "gw-draft/templates/outline.md").read_text(encoding="utf-8")
    (task / "outline.md").write_text(outline, encoding="utf-8")
    (task / "v1_初稿.md").write_text("一、总体情况\n销量同比增长5%。\n", encoding="utf-8")
    (task / "review_report.md").write_text((SKILLS / "gw-review/templates/review_report.md").read_text(encoding="utf-8"), encoding="utf-8")
    lint = str(ROOT / "30_engine/tools/draft_lint.py")
    forms = [
        [str(task / "outline.md"), "--outline", str(task / "outline.md")],
        [str(task / "v1_初稿.md"), "--outline", str(task / "outline.md")],
        [str(task / "v1_初稿.md"), "--outline", str(task / "outline.md"), "--report", str(task / "review_report.md"), "--final"],
    ]
    for args in forms:
        r = subprocess.run([sys.executable, lint, *args], cwd=ROOT, capture_output=True, text=True, timeout=60, stdin=subprocess.DEVNULL)
        assert r.returncode in (0, 1), r.stderr
        assert "机检：" in r.stdout
    # 空模板必须被拦（不能拿模板原样过终验）
    r = subprocess.run([sys.executable, lint, *forms[2]], cwd=ROOT, capture_output=True, text=True, timeout=60, stdin=subprocess.DEVNULL)
    assert r.returncode == 1


@pytest.mark.parametrize("name", NAMES)
def test_skill_body_has_no_real_names_or_units(name):
    """SKILL.md 每次写作都加载、服务所有客户，不得带真实人名/单位名/地名（references 按设计带 [客户:] 标注，不在此查）。"""
    _, changes, _ = deidentify.deidentify(read(name))
    leaks = [c for c in changes if c["type"] in ("人名", "人名(简称)", "单位名", "地名", "企业名", "单位简称")]
    assert not leaks, leaks


def test_gw_draft_exemplar_command_runs():
    """W2-0 范文对照命令要真能列出同子类范文的要件。"""
    lines = [l for l in read("gw-draft").splitlines() if l.startswith("python3 -c") and "articles.jsonl" in l]
    assert lines, "gw-draft 缺范文对照命令"
    code = re.search(r'python3 -c "(.+)" (\S+)$', lines[0])
    out = subprocess.run([sys.executable, "-c", code.group(1), code.group(2)], cwd=ROOT,
                         capture_output=True, text=True, timeout=60, stdin=subprocess.DEVNULL)
    assert out.returncode == 0, out.stderr
    assert "AR-" in out.stdout and "  - " in out.stdout
