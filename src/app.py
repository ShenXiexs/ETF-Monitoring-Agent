from __future__ import annotations

import io
import os
import time
from typing import Dict

from dotenv import load_dotenv
from flask import Flask, jsonify, render_template, request, send_file, send_from_directory

try:
    from .prd_engine import PRDDeliveryEngine
except ImportError:
    from prd_engine import PRDDeliveryEngine


load_dotenv()


def create_app(test_config: Dict | None = None) -> Flask:
    app = Flask(__name__, template_folder="../templates", static_folder=None)
    app.config.from_mapping(
        HOST=os.getenv("HOST", "127.0.0.1"),
        PORT=int(os.getenv("PORT", "5000")),
        JSON_AS_ASCII=False,
        PRD_KNOWLEDGE_PACK_PATH=os.getenv("PRD_KNOWLEDGE_PACK_PATH", ""),
    )
    if test_config:
        app.config.update(test_config)

    engine = PRDDeliveryEngine(knowledge_pack_path=app.config.get("PRD_KNOWLEDGE_PACK_PATH") or None)
    app.config["PRD_ENGINE"] = engine

    allowed_actions = {
        "refresh",
        "load_prd_demo",
        "inline_suggest",
        "next_edit_suggest",
        "rewrite_selection",
        "review_prd",
        "generate_delivery_plan",
        "quality_snapshot",
        "export_prd",
        "switch_agent_mode",
        "assistant_command",
        "apply_persona_rewrite",
        "inline_review",
        "rollback_suggestion",
        "reminder_snapshot",
    }

    def payload() -> dict:
        if request.is_json:
            return request.get_json(silent=True) or {}
        return request.form.to_dict()

    @app.after_request
    def add_security_headers(response):
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers.setdefault("Cache-Control", "no-store")
        return response

    @app.get("/")
    def index() -> str:
        return render_template("dashboard.html", bootstrap=engine.get_bootstrap_state())

    @app.get("/assets/ref/<path:filename>")
    def ref_asset(filename: str):
        return send_from_directory(engine.base_dir / "docs" / "ref", filename)

    @app.post("/workspace")
    def workspace():
        data = payload()
        action = str(data.get("action", "")).strip()
        if action not in allowed_actions:
            return jsonify({"error": "Unsupported action"}), 400

        current_text = str(data.get("current_text") or data.get("document_text") or "")

        if action == "refresh":
            return jsonify(engine.get_bootstrap_state())

        if action == "load_prd_demo":
            return jsonify(engine.load_prd_demo(str(data.get("demo_id", "")).strip() or None))

        if action in {"inline_suggest", "next_edit_suggest"}:
            raw_cursor = data.get("cursor_position")
            try:
                cursor_position = int(raw_cursor) if raw_cursor not in (None, "") else None
            except (TypeError, ValueError):
                cursor_position = None
            if action == "next_edit_suggest":
                return jsonify(
                    engine.next_edit_suggest(
                        current_text,
                        cursor_position=cursor_position,
                        persona=str(data.get("persona", "INTJ_ARCHITECT")),
                    )
                )
            return jsonify(engine.inline_suggest(current_text, cursor_position=cursor_position))

        if action == "rewrite_selection":
            return jsonify(
                engine.rewrite_selection(
                    selected_text=str(data.get("selected_text", "")),
                    mode=str(data.get("mode", "make_concise")),
                    full_text=current_text,
                )
            )

        if action == "switch_agent_mode":
            return jsonify(engine.switch_agent_mode(str(data.get("agent_mode", "reminder"))))

        if action == "assistant_command":
            return jsonify(
                engine.assistant_command(
                    command=str(data.get("command", "")),
                    current_text=current_text,
                    selected_text=str(data.get("selected_text", "")),
                    persona=str(data.get("persona", "INTJ_ARCHITECT")),
                )
            )

        if action == "apply_persona_rewrite":
            return jsonify(
                engine.apply_persona_rewrite(
                    persona=str(data.get("persona", "INTJ_ARCHITECT")),
                    selected_text=str(data.get("selected_text", "")),
                    current_text=current_text,
                )
            )

        if action == "inline_review":
            return jsonify(engine.inline_review(current_text))

        if action == "rollback_suggestion":
            return jsonify(
                engine.rollback_suggestion(
                    rollback_token=str(data.get("rollback_token", "")),
                    current_text=current_text,
                )
            )

        if action == "reminder_snapshot":
            try:
                idle_seconds = float(data.get("idle_seconds", 0) or 0)
            except (TypeError, ValueError):
                idle_seconds = 0
            return jsonify(engine.reminder_snapshot(current_text, idle_seconds=idle_seconds))

        if action == "review_prd":
            return jsonify(engine.review_prd(current_text))

        if action == "generate_delivery_plan":
            return jsonify(engine.generate_delivery_plan(current_text))

        if action == "quality_snapshot":
            return jsonify(engine.quality_snapshot(current_text))

        if action == "export_prd":
            markdown_bytes = engine.export_prd_markdown(current_text)
            report_date = time.strftime("%Y-%m-%d")
            return send_file(
                io.BytesIO(markdown_bytes),
                mimetype="text/markdown; charset=utf-8",
                as_attachment=True,
                download_name=f"doc-as-ide-export-{report_date}.md",
            )

        return jsonify({"error": "Unsupported action"}), 400

    @app.get("/_internal/health")
    def health():
        return jsonify(
            {
                "status": "ok",
                "engine": "PRDDeliveryEngine",
                "knowledge_pack": engine.knowledge_pack_summary(),
                "time": time.time(),
            }
        )

    return app


app = create_app()


if __name__ == "__main__":
    app.run(host=app.config["HOST"], port=app.config["PORT"])
