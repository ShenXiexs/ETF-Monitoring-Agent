# Platform Guide

## macOS / Linux

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
./start_server.sh
```

Or run directly:

```bash
python -m src.app
```

## Windows PowerShell

```powershell
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
.\start_server.ps1
```

## Runtime Variables

- `HOST`: defaults to `127.0.0.1`.
- `PORT`: defaults to `5000`.
- `PRD_KNOWLEDGE_PACK_PATH`: optional path to a custom seeded PRD knowledge pack.

## Demo Checklist

- Open `http://127.0.0.1:5000`.
- Load the PRD demo document.
- Confirm the floating birdhouse appears in `ReminderMode`.
- Switch to `AssistantMode` and verify the mascot changes to the expanded assistant asset.
- Run Next Edit, then press `Tab` to accept ghost text and accept/reject the rephrase diff.
- Select a sentence and press `Cmd/Ctrl+K` to rewrite it.
- Run `@mbti` or select a persona to apply MBTI style rewriting.
- Run `@review` or `Cmd/Ctrl+Enter` to generate inline review.
- Accept, reject, and rollback the inline diff.
- Generate the delivery plan.
- Export the PRD Markdown.
