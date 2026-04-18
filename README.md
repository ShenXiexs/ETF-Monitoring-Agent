# 资管产品洞察协作台

<p align="center">
  <strong>ASSET WORKBENCH</strong>
</p>

<p align="center">
  面向数据驱动研究、政策解析和结构化报告输出的本地工作台
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.10%2B-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python 3.10+">
  <img src="https://img.shields.io/badge/Platform-macOS%20%7C%20Windows%20%7C%20Linux-1f2937?style=for-the-badge" alt="Cross platform">
  <img src="https://img.shields.io/badge/Runtime-Local%20Only-0f766e?style=for-the-badge" alt="Local runtime">
  <img src="https://img.shields.io/badge/API-Single%20Workspace%20Endpoint-b45309?style=for-the-badge" alt="Single endpoint">
</p>

`•` 本地优先运行，默认绑定 `127.0.0.1`

`•` 单入口架构：页面 `GET /`，交互 `POST /workspace`

`•` 内置四个岗位化模块：产品研究、市场监测、内容策略、政策解析

`•` 支持 PDF 摘要、专家 skills 编排和 DOCX 研判报告导出

`•` 通过 `DATA_SOURCE_DIR` + `DATA_PROFILE_PATH` 适配不同数据任务

[快速开始](#快速开始) · [平台运行](docs/platform_guide.md) · [数据接入](docs/data_contract.md) · [Data Profiles](docs/data_profiles.md) · [金融专家 Skills](docs/financial_skills.md) · [安全策略](SECURITY.md) · [事件响应](INCIDENT_RESPONSE.md)

## 项目概览

这个项目把“查数据、看信号、读文档、写初稿”整合进一个统一工作台。系统前端只暴露一个页面入口，所有内部动作都通过 `/workspace` 收口，适合本地开发、比赛演示和中小规模研究场景。

AI 能力采用“结构化数据处理 + 大模型生成 + RAG 检索增强 + 金融专家 skills 编排”的组合方案。对话分析、政策摘要和正式研报可以在同一界面里完成，且在没有业务数据时仍能以空态模式启动，便于演示和联调。

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

复制 `.env.example`，至少按需设置：

```bash
DATA_SOURCE_DIR=/absolute/path/to/data
DATA_PROFILE_PATH=/absolute/path/to/profile.json
LLM_API_KEY=your_key
EMBEDDING_API_KEY=your_key
HOST=127.0.0.1
PORT=5000
```

说明：

- `DATA_SOURCE_DIR` 可选，不配时以空态模式启动
- `DATA_PROFILE_PATH` 可选，不配时使用默认 profile
- `LLM_API_KEY` 未配置时，系统会退回离线摘要与离线研报模板

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

## 主要能力

- `产品研究`：回答产品快照、基础事实、结构特征和简单区间对比
- `市场监测`：生成当日信号、历史回放和排行摘要
- `内容策略`：把事实结论转为可执行的表达框架
- `政策解析`：上传 PDF 后生成政策摘要，并可导出正式 DOCX 报告

## Data Profile 驱动的通用化

项目把“任务文案”和“数据映射”拆到了 profile 配置中。只要你的任务仍然属于“记录快照 + 文档目录 + 信号/日报”这类工作流，通常不需要改前端和核心后端，只需要：

1. 在 `DATA_SOURCE_DIR` 中准备数据文件
2. 在 `DATA_PROFILE_PATH` 中配置文件名、字段映射和界面文案
3. 按需覆盖模块名称和系统 prompt

模板见 [config/profile_template.json](/Users/samxie/Research/Agent-Promotion/asset-intel-workbench/config/profile_template.json)。

## 金融专家 Skills

当前研报链路内置以下专家视角：

- `产品结构分析`
- `资金与成交信号`
- `宏观与市场影响`
- `政策解读`
- `产品策略建议`
- `风险与合规`
- `报告编审`
- `内容叙事设计`

详细说明见 [docs/financial_skills.md](/Users/samxie/Research/Agent-Promotion/asset-intel-workbench/docs/financial_skills.md)。

## 接口与运行边界

- `GET /`：返回完整工作台页面和首屏 bootstrap 数据
- `POST /workspace`：统一内部工作入口，支持 `chat`、`refresh`、`toggle_simulation`、`daily_report`、`generate_report`
- `GET /_internal/health`：仅用于探活

默认运行方式是本机单用户工作台，不建议直接裸露到公网或共享网络环境。

## 安全与可用性

`•` 默认只监听 `127.0.0.1`

`•` 上传仅接受 PDF，并受 `MAX_UPLOAD_MB` 限制

`•` 文档会话按 `DOCUMENT_SESSION_TTL_SECONDS` 自动过期

`•` 聊天历史按 `MAX_CHAT_HISTORY` 截断，避免上下文无限增长

`•` LLM 缓存落在系统临时目录，不写回仓库

更多说明见 [SECURITY.md](SECURITY.md) 和 [INCIDENT_RESPONSE.md](INCIDENT_RESPONSE.md)。

## 测试

```bash
python3 -m pytest -q
```
