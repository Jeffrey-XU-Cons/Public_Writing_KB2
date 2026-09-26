# golden 快照

- `draft_lint_real_docs.json`：82 份脱敏个人历史交付物跑 `draft_lint` 的 block 结果。
  改规则后测试失败 → 先逐条确认变化是改进还是回归；确认是改进后重新生成：
  `KBRAG_ROOT=$PWD python3 40_tests/golden/make_draft_lint_snapshot.py`
- 10章§5.4 规划的检索 golden set 尚未建（依赖 P3.7 检索接入）。
