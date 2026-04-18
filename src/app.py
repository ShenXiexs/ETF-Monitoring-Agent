from __future__ import annotations

import io
import json
import os
import threading
import time
import uuid
from typing import Dict, Iterable

from flask import Flask, Response, jsonify, render_template, request, send_file
from pypdf import PdfReader

try:
    from .agent_manager import AssetWorkbenchManager, MODULES
except ImportError:
    from agent_manager import AssetWorkbenchManager, MODULES


def create_app(test_config: Dict | None = None) -> Flask:
    module_keys = {item["key"] for item in MODULES}
    allowed_actions = {
        "chat",
        "refresh",
        "toggle_simulation",
        "daily_report",
        "generate_report",
        "load_demo_case",
        "report_trace",
        "quality_snapshot",
        "export_outline",
    }
    app = Flask(__name__, template_folder="../templates", static_folder=None)
    app.config.from_mapping(
        DATA_SOURCE_DIR=os.getenv("DATA_SOURCE_DIR"),
        DATA_PROFILE_PATH=os.getenv("DATA_PROFILE_PATH"),
        ENABLE_DEMO_MODE=os.getenv("ENABLE_DEMO_MODE", "1").strip() != "0",
        SIMULATION_INTERVAL=float(os.getenv("SIMULATION_INTERVAL_SECONDS", "5")),
        HOST=os.getenv("HOST", "127.0.0.1"),
        PORT=int(os.getenv("PORT", "5000")),
        MAX_CONTENT_LENGTH=int(float(os.getenv("MAX_UPLOAD_MB", "8")) * 1024 * 1024),
        DOCUMENT_SESSION_TTL_SECONDS=int(os.getenv("DOCUMENT_SESSION_TTL_SECONDS", "3600")),
        MAX_CHAT_HISTORY=int(os.getenv("MAX_CHAT_HISTORY", "24")),
        JSON_AS_ASCII=False,
    )
    if test_config:
        app.config.update(test_config)

    manager = AssetWorkbenchManager(
        data_source_dir=app.config.get("DATA_SOURCE_DIR"),
        profile_path=app.config.get("DATA_PROFILE_PATH"),
        enable_demo_mode=bool(app.config.get("ENABLE_DEMO_MODE", True)),
    )
    simulation_state = {
        "is_running": True,
        "interval": float(app.config["SIMULATION_INTERVAL"]),
    }
    chat_history = []
    document_sessions: Dict[str, dict] = {}
    competition_state: Dict[str, object] = {
        "latest_session_id": None,
        "loaded_case": None,
        "trace_summary": manager.default_trace_summary(),
        "quality_metrics": manager.default_quality_metrics(),
        "comparison": manager.default_comparison(),
    }
    app.config["MANAGER"] = manager
    app.config["DOCUMENT_SESSIONS"] = document_sessions

    def current_bootstrap() -> dict:
        payload = manager.get_bootstrap_state(simulation_state)
        payload.update(competition_state)
        return payload

    def update_competition_state(session_id: str | None = None, artifact: dict | None = None, loaded_case: dict | None = None) -> None:
        if session_id:
            competition_state["latest_session_id"] = session_id
        if artifact:
            competition_state["trace_summary"] = artifact["trace_summary"]
            competition_state["quality_metrics"] = artifact["quality_metrics"]
            competition_state["comparison"] = artifact["comparison"]
        if loaded_case is not None:
            competition_state["loaded_case"] = loaded_case

    def payload() -> dict:
        if request.is_json:
            return request.get_json(silent=True) or {}
        return request.form.to_dict()

    def cleanup_document_sessions() -> None:
        now = time.time()
        ttl = int(app.config["DOCUMENT_SESSION_TTL_SECONDS"])
        expired = [
            session_id
            for session_id, entry in document_sessions.items()
            if now - float(entry.get("created_at", now)) > ttl
        ]
        for session_id in expired:
            document_sessions.pop(session_id, None)
            if competition_state.get("latest_session_id") == session_id:
                competition_state["latest_session_id"] = None
                competition_state["loaded_case"] = None
                competition_state["trace_summary"] = manager.default_trace_summary()
                competition_state["quality_metrics"] = manager.default_quality_metrics()
                competition_state["comparison"] = manager.default_comparison()

    def trim_history() -> None:
        max_items = int(app.config["MAX_CHAT_HISTORY"])
        if len(chat_history) > max_items:
            del chat_history[:-max_items]

    def get_session_entry(session_id: str | None = None) -> dict | None:
        resolved = session_id or str(competition_state.get("latest_session_id") or "")
        return document_sessions.get(resolved) if resolved else None

    def validate_upload(file_storage) -> None:
        filename = (file_storage.filename or "").lower()
        if not filename.endswith(".pdf"):
            raise ValueError("仅支持 PDF 文件。")
        content_type = (file_storage.mimetype or file_storage.content_type or "").lower()
        if content_type and content_type not in {"application/pdf", "application/octet-stream"}:
            raise ValueError("上传文件的类型无效，请使用 PDF。")

    def parse_pdf(file_storage) -> str:
        validate_upload(file_storage)
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

    @app.after_request
    def add_security_headers(response):
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers.setdefault("Cache-Control", "no-store")
        return response

    @app.errorhandler(413)
    def payload_too_large(_error):
        return jsonify({"error": "上传文件超过大小限制。"}), 413

    @app.get("/")
    def index() -> str:
        return render_template("dashboard.html", bootstrap=current_bootstrap())

    @app.post("/workspace")
    def workspace():
        cleanup_document_sessions()
        data = payload()
        action = data.get("action", "").strip()
        if action not in allowed_actions:
            return jsonify({"error": "Unsupported action"}), 400

        if action == "refresh":
            return jsonify(current_bootstrap())

        if action == "toggle_simulation":
            if manager.has_data():
                simulation_state["is_running"] = not simulation_state["is_running"]
            return jsonify(current_bootstrap())

        if action == "daily_report":
            return jsonify(manager.get_daily_report(manager.get_current_date()))

        if action == "load_demo_case":
            case_id = data.get("case_id", "").strip()
            if not case_id:
                return jsonify({"error": "缺少 case_id。"}), 400
            try:
                artifact = manager.build_demo_case_artifact(case_id)
            except ValueError as exc:
                return jsonify({"error": str(exc)}), 400

            session_id = uuid.uuid4().hex
            document_sessions[session_id] = {
                "text": artifact["text"],
                "artifact": artifact,
                "created_at": time.time(),
            }
            simulation_state["is_running"] = False
            update_competition_state(session_id=session_id, artifact=artifact, loaded_case=artifact["case"])
            response = current_bootstrap()
            response.update(
                {
                    "session_id": session_id,
                    "assistant_message": artifact["assistant_message"],
                    "report_ready": True,
                    "outline_ready": True,
                    "active_module": artifact["case"]["active_module"],
                }
            )
            return jsonify(response)

        if action == "report_trace":
            entry = get_session_entry(data.get("session_id", "").strip())
            if entry and entry.get("artifact"):
                return jsonify(entry["artifact"]["trace_summary"])
            return jsonify(competition_state["trace_summary"])

        if action == "quality_snapshot":
            entry = get_session_entry(data.get("session_id", "").strip())
            if entry and entry.get("artifact"):
                return jsonify(entry["artifact"]["quality_metrics"])
            return jsonify(competition_state["quality_metrics"])

        if action == "generate_report":
            session_id = data.get("session_id", "").strip()
            entry = get_session_entry(session_id)
            source_text = entry.get("text", "") if entry else ""
            artifact = entry.get("artifact") if entry else None
            pdf_file = request.files.get("pdf_file")
            if pdf_file:
                try:
                    source_text = parse_pdf(pdf_file)
                except ValueError as exc:
                    return jsonify({"error": str(exc)}), 400
                artifact = manager.build_document_artifact(source_text)
            if not source_text:
                return jsonify({"error": "未找到可导出的文件内容。"}), 400

            if not artifact:
                artifact = manager.build_document_artifact(source_text)
            report_bytes = manager.build_docx_report(
                artifact["enhanced_report"],
                title=artifact.get("report_title", "政策研判报告"),
            )
            report_date = manager.get_current_date() or time.strftime("%Y-%m-%d")
            return send_file(
                io.BytesIO(report_bytes),
                mimetype="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                as_attachment=True,
                download_name=f"policy-report-{report_date}.docx",
            )

        if action == "export_outline":
            session_id = data.get("session_id", "").strip()
            entry = get_session_entry(session_id)
            artifact = entry.get("artifact") if entry else None
            if not artifact:
                return jsonify({"error": "当前没有可导出的答辩大纲。"}), 400
            outline_bytes = manager.build_outline_bytes(artifact["outline"])
            report_date = manager.get_current_date() or time.strftime("%Y-%m-%d")
            return send_file(
                io.BytesIO(outline_bytes),
                mimetype="text/markdown; charset=utf-8",
                as_attachment=True,
                download_name=f"competition-outline-{report_date}.md",
            )

        if action == "chat":
            message = data.get("message", "").strip()
            active_module = data.get("active_module", MODULES[0]["key"]).strip() or MODULES[0]["key"]
            if active_module not in module_keys:
                active_module = MODULES[0]["key"]
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
                    artifact = manager.build_document_artifact(text)
                    document_sessions[session_id] = {"text": text, "artifact": artifact, "created_at": time.time()}
                    update_competition_state(session_id=session_id, artifact=artifact)
                    competition_state["loaded_case"] = None
                    final_message = (
                        "### 政策解析摘要\n\n"
                        f"{artifact['enhanced_summary']}\n\n"
                        f"- 综合评分：{round(sum(item['score'] for item in artifact['quality_metrics']) / len(artifact['quality_metrics']))} 分\n"
                        "- 已生成报告 trace、质量评分卡和答辩大纲，可直接导出。"
                    )
                    chat_history.append({"role": "user", "content": "[上传文件]"})
                    chat_history.append({"role": "assistant", "content": final_message})
                    trim_history()
                    event = {
                        "content": final_message,
                        "session_id": session_id,
                        "report_ready": True,
                        "outline_ready": True,
                        "trace_summary": artifact["trace_summary"],
                        "quality_metrics": artifact["quality_metrics"],
                        "comparison": artifact["comparison"],
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
                trim_history()
                metrics = {
                    "content": "",
                    "metrics": {
                        "think_time": round(max(0.05, gen_start - start_time), 2),
                        "gen_time": round(max(0.05, time.time() - gen_start), 2),
                    },
                }
                yield f"data: {json.dumps(metrics, ensure_ascii=False)}\n\n"

            return Response(
                generate(),
                mimetype="text/event-stream",
                headers={"Cache-Control": "no-store", "X-Accel-Buffering": "no"},
            )

    @app.get("/_internal/health")
    def health():
        return jsonify({"status": "ok", "has_data": manager.has_data(), "time": time.time()})

    return app


app = create_app()


if __name__ == "__main__":
    app.run(host=app.config["HOST"], port=app.config["PORT"])
