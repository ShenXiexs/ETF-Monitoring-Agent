<h1 align="center">ASSET WORKBENCH: 资管产品洞察协作台</h1>

<p align="center">
  面向资管研究与政策研判的智能分析工作台
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.10%2B-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python 3.10+">
  <img src="https://img.shields.io/badge/Platform-macOS%20%7C%20Windows%20%7C%20Linux-1f2937?style=for-the-badge" alt="Cross platform">
  <img src="https://img.shields.io/badge/Mode-External%20Data%20%7C%20Demo%20Mode-0f766e?style=for-the-badge" alt="External and demo modes">
  <img src="https://img.shields.io/badge/API-Single%20Workspace%20Endpoint-b45309?style=for-the-badge" alt="Single workspace endpoint">
</p>

`•` 不是聊天工具，而是围绕“查数据、读政策、做判断、写报告”的完整研究闭环产品

`•` 以结构化数据处理 + RAG 检索增强 + 金融专家 skills 编排为核心 AI 方案

`•` 支持 Baseline vs Enhanced 对比、报告 Trace、质量评分卡和答辩大纲导出

`•` 没有真实外部数据时可自动切换到内置脱敏 Demo Mode，保证比赛现场稳定展示

`•` 通过 `DATA_SOURCE_DIR` + `DATA_PROFILE_PATH` 适配不同数据任务，同时保留资管研究语境

[快速开始](#快速开始) · [Demo Flow](#demo-flow) · [架构](#系统架构) · [平台运行](docs/platform_guide.md) · [数据接入](docs/data_contract.md) · [Data Profiles](docs/data_profiles.md) · [金融专家 Skills](docs/financial_skills.md) · [安全策略](SECURITY.md)

## 项目亮点

这个项目的目标不是“做一个会回答问题的聊天框”，而是把资管团队常见的研究工作流整合成一个统一入口。系统把市场快照、政策目录、历史信号和上传文档统一接入，再通过金融专家 skills 编排，把原本分散的检索、归因、写作流程压缩成一条可解释、可对比、可导出的研究链路。

在比赛场景下，工作台除了能生成正式研判报告，还会同步展示：

- `预置 Demo Case`：政策冲击型、市场波动型、产品策略型三类固定演示场景
- `报告 Trace`：展示哪些专家 skills 被调用、哪些观察进入最终成稿
- `结果对比`：对比 Baseline 与 Enhanced 两种输出
- `报告质量卡`：从事实覆盖度、证据引用率、风险提示完整度、结构完整度四个维度给出评分
- `答辩大纲`：一键导出比赛汇报所需的 1 页式摘要

## AI 技术方案

项目采用的是**结构化数据处理 + 大模型生成 + RAG 检索增强 + 专家 skills 编排**的组合方案。

- `结构化数据处理`：先从市场快照、产品数据和政策目录中提取可验证事实
- `RAG 检索增强`：利用 embedding 和历史信号召回，为模型补充上下文
- `专家 skills 编排`：把政策解读、市场影响、产品策略、风险合规、报告编审等视角嵌入同一条工作流
- `结构化报告生成`：最终输出摘要、正式报告、答辩大纲三类结果物

默认模型路径保持为 DashScope-compatible + Qwen + embedding 方案，不额外引入复杂多服务部署。

## Demo Flow

比赛现场建议按以下顺序演示：

1. 打开首页，展示研究流水线、Why it matters、系统诊断和质量卡
2. 点击一个 `Demo Case`，例如“政策冲击型”
3. 展示系统如何把市场快照、政策目录、历史信号和文档信息整合到同一条研究链路
4. 切换到 `Baseline vs Enhanced` 区域，说明专家 skills 和证据引用带来的提升
5. 导出正式报告和答辩大纲，完成完整闭环

## 可量化产出

- `4` 个岗位化 AI 模块：产品研究、市场监测、内容策略、政策解析
- `8` 个金融专家 skills：产品结构分析、资金与成交信号、宏观与市场影响、政策解读、产品策略建议、风险与合规、报告编审、内容叙事设计
- `3` 类核心输出：正式报告、质量评分卡、答辩大纲
- `4` 类证据来源：市场快照、政策目录、历史信号、上传文档

## 系统架构

```mermaid
flowchart LR
    A[市场快照 / 政策目录 / 上传文档] --> B[数据标准化与规则信号]
    B --> C[RAG 检索与意图识别]
    C --> D[金融专家 Skills 编排]
    D --> E[结构化结论]
    E --> F[正式报告 / 质量卡 / 答辩大纲]
```

核心接口保持简单：

- `GET /`：返回完整工作台页面与首屏 bootstrap 数据
- `POST /workspace`：统一内部工作入口
- `GET /_internal/health`：仅用于探活

当前 `/workspace` 支持：

- `chat`
- `refresh`
- `toggle_simulation`
- `daily_report`
- `generate_report`
- `load_demo_case`
- `report_trace`
- `quality_snapshot`
- `export_outline`

## 快速开始

### 1. 安装依赖

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Windows PowerShell:

```powershell
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### 2. 配置环境变量

复制 `.env.example`，常用变量如下：

```bash
DATA_SOURCE_DIR=/absolute/path/to/data
DATA_PROFILE_PATH=/absolute/path/to/profile.json
ENABLE_DEMO_MODE=1
LLM_API_KEY=your_key
EMBEDDING_API_KEY=your_key
HOST=127.0.0.1
PORT=5000
```

说明：

- `DATA_SOURCE_DIR` 可选，不配时会优先进入内置 Demo Mode
- `DATA_PROFILE_PATH` 可选，不配时使用默认 profile
- `ENABLE_DEMO_MODE=0` 时，可强制关闭内置演示数据
- `LLM_API_KEY` 未配置时，系统会退回离线摘要与离线报告模板

### 3. 启动服务

macOS / Linux:

```bash
./start_server.sh
```

Windows PowerShell:

```powershell
.\start_server.ps1
```

或直接运行：

```bash
python -m src.app
```

## Data Profile 驱动的通用化

项目把“界面叙事”和“数据字段映射”拆到了 profile 配置中。只要你的任务仍属于“记录快照 + 文档目录 + 信号/日报”这类工作流，通常不需要改核心代码，只需要：

1. 在 `DATA_SOURCE_DIR` 中准备数据文件
2. 在 `DATA_PROFILE_PATH` 中配置文件名、字段映射和界面文案
3. 按需覆盖模块名称、Demo Case 文案、质量阈值和系统 prompt

模板见 [config/profile_template.json](/Users/samxie/Research/Agent-Promotion/asset-intel-workbench/config/profile_template.json)。

## 演示模式与跨平台支持

`•` 默认优先绑定 `127.0.0.1`，适合本机开发和比赛现场展示

`•` 提供 `start_server.sh` 和 `start_server.ps1`，同时兼容 macOS / Linux / Windows

`•` 没有真实数据时可自动切换到内置演示模式，避免现场因路径或 Excel 文件缺失而翻车

`•` `src/preprocess.py` 提供 profile-aware 数据校验能力，方便快速排查字段或目录问题

更多说明见 [docs/platform_guide.md](docs/platform_guide.md)、[docs/data_contract.md](docs/data_contract.md) 和 [docs/data_profiles.md](docs/data_profiles.md)。

## 安全与可用性

`•` 默认只监听 `127.0.0.1`

`•` 上传仅接受 PDF，并受 `MAX_UPLOAD_MB` 限制

`•` 文档会话按 `DOCUMENT_SESSION_TTL_SECONDS` 自动过期

`•` 聊天历史按 `MAX_CHAT_HISTORY` 截断，避免上下文无限增长

`•` LLM 缓存落在系统临时目录，不写回仓库

更多说明见 [SECURITY.md](SECURITY.md) 和 [INCIDENT_RESPONSE.md](INCIDENT_RESPONSE.md)。

## 开发说明

本轮按竞赛冲刺思路实现了展示层、Demo Case、Trace、质量卡与答辩大纲导出。你如果继续往下做，优先建议补：

1. 更强的可视化图表和时间序列展示
2. 更细粒度的报告评测与事实核对
3. 更完整的答辩材料与架构图资产
