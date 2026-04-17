from __future__ import annotations

import io
import json
import os
import threading
import time
import uuid
from typing import Dict, Iterable, Tuple

from flask import Flask, Response, jsonify, render_template, request, send_file
from pypdf import PdfReader

try:
    from .agent_manager import AssetWorkbenchManager, MODULES
except ImportError:
    from agent_manager import AssetWorkbenchManager, MODULES


def create_app(test_config: Dict | None = None) -> Flask:
    app = Flask(__name__, template_folder="../templates", static_folder=None)
    app.config.from_mapping(
        DATA_SOURCE_DIR=os.getenv("DATA_SOURCE_DIR"),
        SIMULATION_INTERVAL=float(os.getenv("SIMULATION_INTERVAL_SECONDS", "5")),
        JSON_AS_ASCII=False,
    )
    if test_config:
        app.config.update(test_config)

    manager = AssetWorkbenchManager(data_source_dir=app.config.get("DATA_SOURCE_DIR"))
    simulation_state = {
        "is_running": True,
        "interval": float(app.config["SIMULATION_INTERVAL"]),
    }
    chat_history = []
    document_sessions: Dict[str, str] = {}
    app.config["MANAGER"] = manager
    app.config["DOCUMENT_SESSIONS"] = document_sessions

    def current_bootstrap() -> dict:
        return manager.get_bootstrap_state(simulation_state)

    def payload() -> dict:
        if request.is_json:
            return request.get_json(silent=True) or {}
        return request.form.to_dict()

    def parse_pdf(file_storage) -> str:
        reader = PdfReader(io.BytesIO(file_storage.read()))
        parts = []
        for page in reader.pages:
            parts.append(page.extract_text() or "")
        text = "\n".join(parts).strip()
        return text or "未提取到可识别正文，请生成一份以结构化框架为主的审慎研判说明。"

    def simulation_loop() -> None:
        while True:
            try:
                if simulation_state["is_running"] and manager.has_data():
                    if not manager.next_step():
                        manager.reset_cycle()
                time.sleep(simulation_state["interval"])
            except Exception as exc:
                app.logger.exception("simulation loop error: %s", exc)
                time.sleep(1)

    if not app.config.get("TESTING"):
        threading.Thread(target=simulation_loop, daemon=True).start()

    @app.get("/")
    def index() -> str:
        return render_template("dashboard.html", bootstrap=current_bootstrap())

    @app.post("/workspace")
    def workspace():
        data = payload()
        action = data.get("action", "").strip()

        if action == "refresh":
            return jsonify(current_bootstrap())

        if action == "toggle_simulation":
            if manager.has_data():
                simulation_state["is_running"] = not simulation_state["is_running"]
            return jsonify(current_bootstrap())

        if action == "daily_report":
            return jsonify(manager.get_daily_report(manager.get_current_date()))

        if action == "generate_report":
            session_id = data.get("session_id", "").strip()
            source_text = document_sessions.get(session_id, "")
            pdf_file = request.files.get("pdf_file")
            if pdf_file:
                source_text = parse_pdf(pdf_file)
            if not source_text:
                return jsonify({"error": "未找到可导出的文件内容。"}), 400

            report_text = manager.analyze_document(source_text)
            report_bytes = manager.build_docx_report(report_text)
            report_date = manager.get_current_date() or time.strftime("%Y-%m-%d")
            return send_file(
                io.BytesIO(report_bytes),
                mimetype="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                as_attachment=True,
                download_name=f"policy-report-{report_date}.docx",
            )

        if action == "chat":
            message = data.get("message", "").strip()
            active_module = data.get("active_module", MODULES[0]["key"]).strip() or MODULES[0]["key"]
            pdf_file = request.files.get("pdf_file")

            def generate() -> Iterable[str]:
                start_time = time.time()

                if pdf_file:
                    try:
                        text = parse_pdf(pdf_file)
                    except Exception as exc:
                        event = {"content": f"文件解析失败：{exc}"}
                        yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
                        return

                    session_id = uuid.uuid4().hex
                    document_sessions[session_id] = text
                    summary = manager.summarize_document(text)
                    final_message = (
                        "### 政策解析摘要\n\n"
                        f"{summary}\n\n"
                        "如需导出正式研判报告，请点击页面中的“导出报告”。"
                    )
                    chat_history.append({"role": "user", "content": "[上传文件]"})
                    chat_history.append({"role": "assistant", "content": final_message})
                    event = {
                        "content": final_message,
                        "session_id": session_id,
                        "report_ready": True,
                        "metrics": {
                            "think_time": round(max(0.1, time.time() - start_time), 2),
                            "gen_time": 0.1,
                        },
                    }
                    yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
                    return

                if not message:
                    event = {"content": "请输入消息或上传待解析文件。"}
                    yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
                    return

                direct = manager.detect_structured_response(message, active_module)
                if direct is not None:
                    chat_history.append({"role": "user", "content": message})
                    chat_history.append({"role": "assistant", "content": direct})
                    event = {
                        "content": direct,
                        "metrics": {
                            "think_time": round(max(0.05, time.time() - start_time), 2),
                            "gen_time": 0.05,
                        },
                    }
                    yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
                    return

                thought = {"content": f"<thought>{manager.module_label(active_module)}正在整理上下文...</thought>"}
                yield f"data: {json.dumps(thought, ensure_ascii=False)}\n\n"

                prompt = manager.build_llm_prompt(message, active_module)
                system_prompt = manager.build_system_prompt(active_module)
                response_text = ""
                content_started = False
                gen_start = start_time

                for chunk in manager.call_llm_stream(
                    prompt,
                    system_content=system_prompt,
                    history=chat_history[-6:],
                    model="qwen-flash" if active_module != "product_research" else "qwen-turbo",
                ):
                    if not content_started:
                        content_started = True
                        gen_start = time.time()
                    response_text += chunk
                    yield f"data: {json.dumps({'content': chunk}, ensure_ascii=False)}\n\n"

                chat_history.append({"role": "user", "content": message})
                chat_history.append({"role": "assistant", "content": response_text})
                metrics = {
                    "content": "",
                    "metrics": {
                        "think_time": round(max(0.05, gen_start - start_time), 2),
                        "gen_time": round(max(0.05, time.time() - gen_start), 2),
                    },
                }
                yield f"data: {json.dumps(metrics, ensure_ascii=False)}\n\n"

            return Response(generate(), mimetype="text/event-stream")

        return jsonify({"error": "Unsupported action"}), 400

    @app.get("/_internal/health")
    def health():
        return jsonify({"status": "ok", "has_data": manager.has_data(), "time": time.time()})

    return app


app = create_app()


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "5000")))
