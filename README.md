# 资管产品洞察协作台

这是一个面向资管产品场景的协作工作台。系统提供四类岗位化能力：产品研究、市场监测、内容策略、政策解析。页面只暴露一个入口 `GET /`，所有内部交互统一通过 `POST /workspace` 完成。

## 金融专家 Skills

系统在模块 prompt 和研报工作流中内置了一组金融专家 skills，用来提升摘要和研报的一致性与专业度。

- `产品结构分析`
- `资金与成交信号`
- `宏观与市场影响`
- `政策解读`
- `产品策略建议`
- `风险与合规`
- `报告编审`
- `内容叙事设计`

其中 `政策解析` 模块会在文档摘要和正式研报导出时启用双阶段工作流：

1. 先生成按 skills 拆分的分析笔记
2. 再由报告编审视角整合为最终摘要或正式研报

详细定义见 [financial_skills.md](/Users/samxie/Research/Agent-Promotion/asset-intel-workbench/docs/financial_skills.md)。

## 运行方式

1. 安装依赖

```bash
pip install -r requirements.txt
```

2. 配置环境变量

```bash
export DATA_SOURCE_DIR=/absolute/path/to/external-data
export LLM_API_KEY=your_key
export EMBEDDING_API_KEY=your_key
```

`DATA_SOURCE_DIR` 可选。未配置时系统会以空态模式启动，页面仍可访问，但监测和日报区域不会展示业务数据。

3. 启动服务

```bash
python -m src.app
```

或在 Windows PowerShell 中运行 `.\start_server.ps1`。

## 数据目录约定

外部目录固定使用以下文件名：

- `market_snapshot.json`
- `policy_catalog.xlsx`

`market_snapshot.json` 的顶层结构为按日期索引的对象：

```json
{
  "2026-01-05": {
    "products": [
      {
        "code": "560001.SH",
        "name": "示例产品A",
        "setup_date": "2025-05-10",
        "list_date": "2025-05-20",
        "scale": 12.5,
        "volume": 3.2,
        "inflow": 1.1,
        "index_code": "000001.SH"
      }
    ],
    "indices": {
      "000001.SH": {
        "name": "示例指数",
        "prev_close": 3200.0,
        "open": 3215.0,
        "change": 1.2,
        "volume": 986.4
      }
    }
  }
}
```

`policy_catalog.xlsx` 建议至少包含四列：

- `公告日期`
- `标题`
- `法律位阶`
- `来源`

详细说明见 [docs/data_contract.md](/Users/samxie/Research/Agent-Promotion/asset-intel-workbench/docs/data_contract.md)。

## 接口说明

- `GET /`: 返回完整工作台页面和首屏 bootstrap 数据
- `POST /workspace`: 统一内部工作入口，支持 `chat`、`refresh`、`toggle_simulation`、`daily_report`、`generate_report`
- `GET /_internal/health`: 部署探活

## 测试

```bash
pytest
```
