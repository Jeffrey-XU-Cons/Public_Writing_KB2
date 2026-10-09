# golden 快照

- `draft_lint_real_docs.json`：82 份脱敏个人历史交付物跑 `draft_lint` 的 block 结果。
  2026-10-07 起指向脱敏批次 r11（`B-20261007-deid-个人历史交付物-r11`）；由 r10 切过来重生成后 82 份逐份 block 不变（合计 188），快照内容未变。
  改规则后测试失败 → 先逐条确认变化是改进还是回归；确认是改进后重新生成：
  `KBRAG_ROOT=$PWD python3 40_tests/golden/make_draft_lint_snapshot.py`
- 10章§5.4 规划的检索 golden set 尚未建（依赖 P3.7 检索接入）。
