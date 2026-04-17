# 数据接入约定

## 目录结构

外部数据目录固定使用以下文件名：

- `market_snapshot.json`
- `policy_catalog.xlsx`

## `market_snapshot.json`

顶层为日期字典，键使用 `YYYY-MM-DD`。

每个日期对象支持两个字段：

- `products`: 产品列表
- `indices`: 指数字典或列表

### 产品字段

- `code`: 产品代码
- `name`: 产品名称
- `setup_date`: 成立日，可为空
- `list_date`: 上市日，可为空
- `scale`: 规模，数值型
- `volume`: 成交额，数值型
- `inflow`: 净流入，数值型
- `index_code`: 跟踪指数代码，可为空

### 指数字段

- `name`: 指数名称
- `prev_close`: 前收
- `open`: 开盘
- `change`: 涨跌幅
- `volume`: 成交额

## `policy_catalog.xlsx`

系统默认读取第一个工作表，按表头定位字段。建议至少包含：

- `公告日期`
- `标题`
- `法律位阶`
- `来源`

`公告日期` 支持 Excel 日期或 `YYYY-MM-DD` 字符串。

