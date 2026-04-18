# Data Profiles

`DATA_PROFILE_PATH` 用来把外部数据和工作台界面解耦。你可以通过一个 JSON 文件同时定义：

- 工作台名称、说明文案和按钮文案
- 模块名称、模块简介和系统 prompt
- 外部文件名
- JSON 字段映射
- Excel 列别名

## 最小流程

1. 复制 [profile_template.json](/Users/samxie/Research/Agent-Promotion/asset-intel-workbench/config/profile_template.json)
2. 修改 `workspace` 段中的名称和文案
3. 修改 `files` 段中的文件名
4. 修改 `snapshot` 和 `policy` 段中的字段映射
5. 设置 `DATA_PROFILE_PATH=/absolute/path/to/profile.json`

## 适用边界

当前 profile 机制适合“记录快照 + 参考指标 + 文档目录”这类任务。它可以覆盖：

- 资管产品数据
- 行业监测样本
- 事件台账
- 研究对象目录加文档目录的混合型任务

如果你的任务仍然需要“排行、异常信号、日报、文档解析”这些通用能力，通常只改 profile 就够了。

## 与代码的关系

- 前端展示文案读取 `workspace`
- 数据加载读取 `files / snapshot / policy`
- 模块标题和系统 prompt 读取 `workspace.module_overrides`

这样在切换任务时，常见改动落在配置层，而不是页面模板和业务代码。
