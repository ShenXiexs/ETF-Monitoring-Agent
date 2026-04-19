# 实际运行示例

这组文件来自一次真实本地运行，使用的是项目内置 `Demo Mode` 和预置案例 `policy_shock`。

执行路径如下：

1. `GET /`
2. `POST /workspace` with `action=refresh`
3. `POST /workspace` with `action=load_demo_case` and `case_id=policy_shock`
4. `POST /workspace` with `action=report_trace`
5. `POST /workspace` with `action=quality_snapshot`
6. `POST /workspace` with `action=export_outline`
7. `POST /workspace` with `action=generate_report`

目录说明：

- [policy_shock_demo_summary.json](/Users/samxie/Research/Agent-Promotion/asset-intel-workbench/docs/examples/policy_shock_demo_summary.json)：本次运行的结构化摘要，包含会话 ID、质量卡、trace steps 和输出预览。
- [policy_shock_outline.md](/Users/samxie/Research/Agent-Promotion/asset-intel-workbench/docs/examples/policy_shock_outline.md)：答辩大纲原文，可直接给评委或放进项目介绍页。
- [policy_shock_report_excerpt.txt](/Users/samxie/Research/Agent-Promotion/asset-intel-workbench/docs/examples/policy_shock_report_excerpt.txt)：从导出的 Word 研判报告中抽取的正文文本，便于 GitHub 在线查看。
- [policy_shock_report.docx](/Users/samxie/Research/Agent-Promotion/asset-intel-workbench/docs/examples/policy_shock_report.docx)：实际导出的 Word 报告文件。

说明：

- 这组示例在 `2026-04-19` 生成。
- 当前示例基于内置脱敏演示数据，不依赖外部业务目录即可复现。
- `session_id` 属于单次运行结果，每次重新加载案例都会变化。
