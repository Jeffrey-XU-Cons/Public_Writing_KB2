# 一次性数据迁移，2026-10-03 执行（P5 第 1 轮 第⑦步抽检 15 条后的修正），留档备查。可重跑：已改过的不再动。
# 抽检由 Claude 代做（Jeffrey 2026-10-03 授权“ThinkBook 收尾你决定”），并对三批 83 条全部答案做了数字回源核对。
#   QA-C5-00017：“三种态按一成、七成、两成分配篇幅”素材里没有，是萃取时编的比例 → 改为素材原意
#   QA-C3-00023：把原文一个例子“全文不到2000字”写成了规则“两千字以内” → 改回例子
#   QA-C6-00029：一条里拼了“起草人立场三无”和“文气”两个知识点（批次自评最差的原因）→ 只留三无；
#               文气（Ch19.3）判为待单独萃取，记入 source_anchor
# -*- coding: utf-8 -*-
import json
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import common  # noqa: E402
from kb_validate import answer_hash, validate_record  # noqa: E402

TODAY = date.today().isoformat()

# (id, 字段, 旧文本, 新文本)
REPLACEMENTS = [
    ("QA-C5-00017", "answer",
     "三种态按大约一成、七成、两成分配篇幅。",
     "篇幅大头给行动之态，身份之态和决心之态从简。"),
    ("QA-C3-00023", "answer",
     "能，就写“点子”式，两千字以内，直接给建议。",
     "能，就写“点子”式，篇幅可以很短（前面清理占道经营一例全文不到两千字），直接给建议。"),
    ("QA-C6-00029", "question",
     " / 什么是公文的“文气”？",
     " / 起草人怎样对自己的稿子做立场自查？"),
    ("QA-C6-00029", "answer",
     "立场正了，公文才有正气；在此基础上，意气、气势、气脉三者贯通，文章才有感染力。",
     "立场正了，公文才有正气。"),
    ("QA-C6-00029", "answer",
     "\n文气从三个方面把握：意气，体现思想高度和格局；气势，有力度、有激情；气脉，思路连贯、结构紧凑、语言流畅，一气呵成。文气畅通的前提是精心构思和一气呵成。",
     ""),
    ("QA-C6-00029", "answer",
     "\n坑五“文气断裂”。东拼西凑，读来气脉不通。",
     ""),
    ("QA-C6-00029", "answer",
     "⑥文气：意气、气势、气脉；⑦成稿做立场自查。",
     "⑥成稿做立场自查：篇幅、归属、问题、经手工作四查。"),
    ("QA-C6-00029", "source_anchor",
     "Ch19《文以气胜》19.1 文以载道、19.3 文气要畅通（行3205-3326）",
     "Ch19《文以气胜》19.1 文以载道（行3205-3280）；19.3 文气要畅通（行3281-3326）2026-10-03 抽检拆出，待单独萃取"),
    # 同日补萃完成后回填指向
    ("QA-C6-00029", "source_anchor",
     "2026-10-03 抽检拆出，待单独萃取",
     "2026-10-03 抽检拆出，已萃为 QA-C4-00010（B-20261003-02）"),
]


def main():
    files = {f: [json.loads(l) for l in f.read_text(encoding="utf-8").splitlines() if l.strip()]
             for f in sorted(common.qa_dir().glob("c[1-6]_*.jsonl"))}
    recs = {r["id"]: r for rs in files.values() for r in rs}
    done = []
    for rid, field, old, new in REPLACEMENTS:
        rec = recs[rid]
        if old in rec[field]:
            rec[field] = rec[field].replace(old, new, 1)
            rec["updated"] = TODAY
            done.append(f"{rid}.{field}")
        # 旧文本已不在：要么已改过，要么被同字段后一条替换接着改过（重跑时两者都正常），跳过
    errors = []
    for rid in {d.split(".")[0] for d in done}:
        recs[rid]["answer_hash"] = answer_hash(recs[rid]["answer"])
        errors += [f"{rid}: {e}" for e in validate_record(recs[rid])]
    if errors:
        raise SystemExit("校验未过，终止且未写任何文件：\n" + "\n".join(errors))
    for f, rs in files.items():
        tmp = f.with_suffix(".jsonl.tmp")
        tmp.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in rs) + "\n", encoding="utf-8")
        tmp.replace(f)
    print("\n".join(done) or "无变化（已改过）")


if __name__ == "__main__":
    common.force_utf8_stdout()
    main()
