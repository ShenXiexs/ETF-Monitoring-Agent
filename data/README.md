# External Data Only

仓库不内置业务数据。

运行时请通过 `DATA_SOURCE_DIR` 指向外部目录，并提供：

- `market_snapshot.json`
- `policy_catalog.xlsx`

工作台在没有外部数据时会以空态模式启动。

