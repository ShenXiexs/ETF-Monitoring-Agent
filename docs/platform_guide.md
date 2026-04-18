# 平台运行说明

## macOS / Linux

推荐命令：

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
./start_server.sh
```

如果脚本没有执行权限，也可以直接运行：

```bash
bash start_server.sh
```

## Windows PowerShell

```powershell
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
.\start_server.ps1
```

## 运行时建议

- 默认绑定 `127.0.0.1:5000`，更适合本机开发和比赛演示。
- 需要改端口时，设置 `PORT` 即可。
- 需要局域网访问时，再显式设置 `HOST=0.0.0.0`。
- 若未配置 `DATA_SOURCE_DIR`，默认会切换到内置 Demo Mode；若想强制空态，可设置 `ENABLE_DEMO_MODE=0`。

## 赛前建议

正式展示前可先运行一次数据校验：

```bash
python -m src.preprocess /absolute/path/to/data --profile /absolute/path/to/profile.json
```

这样可以提前发现文件名、日期格式、字段映射和目录结构问题。
