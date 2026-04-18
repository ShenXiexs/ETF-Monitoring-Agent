# Data Directory

仓库不内置真实业务数据，但内置了一份**脱敏演示数据**用于比赛展示：

- `demo_workspace.json`

运行时优先读取 `DATA_SOURCE_DIR` 指向的外部目录，并按 profile 约定加载：

- `market_snapshot.json`
- `policy_catalog.xlsx`

如果未提供外部目录，且 `ENABLE_DEMO_MODE` 未关闭，工作台会自动切换到内置演示模式，保证现场 Demo 可稳定运行。
