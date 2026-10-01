# 一次性数据迁移，2026-09-29 执行（P5 第 1 轮阶段 0 第 4 步），留档备查。可重跑：已是相对路径的记录不动。
# 把 QA 记录里的 Windows 绝对路径 D:\projects\Public_Writing_KB\... 改成项目内相对路径（正斜杠），
# 两台机器都能解析。只改 source_path，不动答案与 answer_hash，也不改 updated（内容没变）。
# -*- coding: utf-8 -*-
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import common  # noqa: E402

WIN_PREFIX = re.compile(r"^[A-Za-z]:[\\/]projects[\\/]Public_Writing_KB[\\/]")


def to_relative(path: str) -> str:
    return WIN_PREFIX.sub("", path).replace("\\", "/")


def main():
    root = common.project_root()
    changed = 0
    pending = {}  # qa_file -> new lines; write only after every target is verified
    for qa_file in sorted(common.qa_dir().glob("c[1-6]_*.jsonl")):
        out = []
        for line in qa_file.read_text(encoding="utf-8").splitlines():
            if line.strip():
                rec = json.loads(line)
                old = rec["source_path"]
                if WIN_PREFIX.match(old):
                    new = to_relative(old)
                    if not (root / new).exists():
                        raise SystemExit(f"目标不存在，终止且未写任何文件: {rec['id']} → {new}")
                    rec["source_path"] = new
                    changed += 1
                    line = json.dumps(rec, ensure_ascii=False)
            out.append(line)
        pending[qa_file] = out
    for qa_file, out in pending.items():
        tmp = qa_file.with_suffix(".jsonl.tmp")
        tmp.write_text("\n".join(out) + "\n", encoding="utf-8")
        tmp.replace(qa_file)
    print(f"已改 {changed} 条 source_path")


if __name__ == "__main__":
    common.force_utf8_stdout()
    main()
