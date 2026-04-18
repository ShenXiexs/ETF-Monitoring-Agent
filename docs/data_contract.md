# 数据接入约定

项目的数据接入由两部分组成：

- `DATA_SOURCE_DIR`：外部数据目录
- `DATA_PROFILE_PATH`：字段映射与界面文案配置

若未提供 `DATA_SOURCE_DIR`，且 `ENABLE_DEMO_MODE` 未关闭，系统会自动切换到仓库内置的脱敏演示数据。

默认 profile 见 [config/default_profile.json](/Users/samxie/Research/Agent-Promotion/asset-intel-workbench/config/default_profile.json)，自定义模板见 [config/profile_template.json](/Users/samxie/Research/Agent-Promotion/asset-intel-workbench/config/profile_template.json)。

## 目录结构

默认情况下，外部目录使用以下文件名：

- `market_snapshot.json`
- `policy_catalog.xlsx`

如果你的任务使用不同文件名，可以在 profile 的 `files` 段覆盖。

## 快照文件

默认快照是按日期组织的 JSON，支持字典或列表两种形式。系统会把原始字段映射到一组标准字段：

- 记录字段：`code`、`name`、`setup_date`、`list_date`、`scale`、`volume`、`inflow`、`index_code`
- 参考指标字段：`name`、`prev_close`、`open`、`change`、`volume`

这些名字只是系统内部使用的标准键，不要求你的原始数据真的叫这个名字。只要在 profile 的 `snapshot.product_fields` 和 `snapshot.index_fields` 里做映射即可。

## 文档目录文件

默认文档目录是 Excel 文件，系统按表头别名定位列。默认识别以下标准列：

- 日期列：`公告日期`
- 标题列：`标题`
- 分类列：`法律位阶`
- 来源列：`来源`

你也可以在 profile 的 `policy.columns` 中配置别名，例如把 `文档标题` 映射到标题列，把 `发布日期` 映射到日期列。

## 适配建议

- 若只是换字段名或文件名，优先修改 profile，不要改 Python 代码。
- 若是新的记录类任务，尽量把核心数值映射到 `scale / volume / inflow` 这三个标准指标，便于继续使用现有的排行、信号和日报逻辑。
- 若数据完全不适合现有三指标范式，再考虑扩展规则引擎，而不是直接改前端页面。
- 若需要比赛展示，可优先在 profile 中覆盖 `competition.demo_cases`、`competition.why_it_matters` 和 `competition.quality_thresholds`，而不是改模板。
