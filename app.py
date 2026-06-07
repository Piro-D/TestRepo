import json
import uuid
from datetime import datetime, timezone
from pathlib import Path # 🌟 ADDED: Required for the absolute path

from flask import Flask, redirect, render_template, request, session, url_for

import config
from ml.service import decompose_document, estimate_duration, run_ml_decomposition
from services.calendar_service import push_to_calendar
from services.oauth_service import get_authorization_url, handle_oauth_callback
from services.state_service import build_working_hours, load_state, save_state
from services.upload_utils import remove_file, save_upload
from werkzeug.middleware.proxy_fix import ProxyFix


app = Flask(__name__, static_folder="static", static_url_path="/static")
app.secret_key = config.SECRET_KEY
app.config["UPLOAD_FOLDER"] = str(config.UPLOAD_FOLDER)
app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024

app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)


def redirect_home(message=None, tab="pipeline"):
    params = {"tab": tab}
    if message:
        params["message"] = message
    return redirect(url_for("index", **params))


def require_login(tab="pipeline"):
    if "credentials" not in session:
        return redirect_home("Log in first.", tab=tab)
    return None


def sync_calendar(tasks):
    state = load_state()
    sync_data = dict(session)
    sync_data.update(
        {
            "attention_span": state["settings"]["attention_span"],
            "break_duration": state["settings"]["break_duration"],
            "working_hours_config": state["settings"]["working_hours_config"],
            "active_event_ids": state.get("events", []),
        }
    )

    new_event_ids = push_to_calendar(tasks, sync_data)
    save_state(tasks, new_event_ids, state["settings"])


def append_tasks(tasks, new_tasks):
    for task in new_tasks:
        tasks.append(
            {
                "id": str(uuid.uuid4()),
                "name": task.get("name", "Manual Task"),
                "duration_minutes": int(task.get("duration_minutes", 30)),
            }
        )
    return tasks


def save_feedback(ratings, comments):
    # 🌟 THE FIX: Hardcoding the absolute Azure path to escape the temporary RAM
    feedback_path = Path("/home/site/wwwroot/feedback.json")
    
    feedback_entries = []
    if feedback_path.exists():
        try:
            with feedback_path.open("r", encoding="utf-8") as feedback_file:
                feedback_entries = json.load(feedback_file)
        except (OSError, json.JSONDecodeError):
            feedback_entries = []

    feedback_entries.append(
        {
            "ratings": ratings,
            "comments": comments,
            "submitted_at": datetime.now(timezone.utc).isoformat(),
        }
    )

    with feedback_path.open("w", encoding="utf-8") as feedback_file:
        json.dump(feedback_entries, feedback_file, indent=4)


def process_uploaded_file(field_name, processor):
    file = request.files.get(field_name)
    if not file or file.filename == "":
        return None, "No file selected."

    filepath = save_upload(file)
    try:
        return processor(filepath), None
    finally:
        remove_file(filepath)


@app.route("/")
def index():
    state = load_state()

    return render_template(
        "index.html",
        logged_in="credentials" in session,
        current_span=state["settings"]["attention_span"],
        working_hours_config=state["settings"]["working_hours_config"],
        break_duration=state["settings"]["break_duration"],
        message=request.args.get("message"),
        active_tab=request.args.get("tab", "pipeline"),
        decompose_result=session.pop("decompose_result", None),
        estimate_result=session.pop("estimate_result", None),
        saved_tasks=state["tasks"],
        has_saved_tasks=bool(state["tasks"]),
    )


@app.route("/authorize")
def authorize():
    try:
        authorization_url, state, code_verifier = get_authorization_url()
        session["state"] = state
        session["code_verifier"] = code_verifier
        return redirect(authorization_url)
    except Exception as exc:
        return redirect_home(f"Google OAuth Error: {exc}")


@app.route("/oauth2callback")
def oauth2callback():
    try:
        credentials = handle_oauth_callback(
            request.url,
            session.get("state"),
            session.get("code_verifier"),
        )
        session["credentials"] = credentials
        session.pop("state", None)
        session.pop("code_verifier", None)
        return redirect(url_for("index"))
    except Exception as exc:
        return redirect_home(f"OAuth Callback Error: {exc}")


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("index"))


@app.route("/update_settings", methods=["POST"])
def update_settings():
    state = load_state()
    settings = state["settings"]
    settings["attention_span"] = int(request.form.get("span", config.DEFAULT_ATTENTION_SPAN))
    settings["break_duration"] = int(request.form.get("break_duration", config.DEFAULT_BREAK_DURATION))
    settings["working_hours_config"] = build_working_hours(request.form)

    save_state(state["tasks"], state.get("events", []), settings)

    if state["tasks"] and "credentials" in session:
        try:
            sync_calendar(state["tasks"])
            return redirect_home("Settings saved and calendar updated.")
        except Exception as exc:
            return redirect_home(f"Settings saved, but calendar update failed: {exc}")

    return redirect_home("Schedule configuration saved.")


@app.route("/schedule_tasks", methods=["POST"])
def schedule_tasks():
    login_redirect = require_login()
    if login_redirect:
        return login_redirect

    new_tasks, error = process_uploaded_file("task_file", run_ml_decomposition)
    if error:
        return redirect_home(error)
    if not new_tasks:
        return redirect_home("AI processing failed.")

    state = load_state()
    updated_tasks = append_tasks(state["tasks"], new_tasks)

    try:
        sync_calendar(updated_tasks)
        return redirect_home("Document parsed. Tasks appended to backlog and scheduled.")
    except Exception as exc:
        return redirect_home(f"Scheduling failed: {exc}")


@app.route("/update_backlog", methods=["POST"])
def update_backlog():
    login_redirect = require_login()
    if login_redirect:
        return login_redirect

    state = load_state()
    updated_tasks = []

    for task_id in request.form.getlist("task_ids"):
        if request.form.get(f"complete_{task_id}"):
            continue

        duration = int(request.form.get(f"duration_{task_id}", 0))
        name = request.form.get(f"name_{task_id}", "Task")
        if duration <= 0:
            continue

        task = next((item for item in state["tasks"] if item.get("id") == task_id), {"id": task_id})
        task.update({"name": name, "duration_minutes": duration})
        updated_tasks.append(task)

    try:
        sync_calendar(updated_tasks)
        return redirect_home("Backlog updated and calendar synced.")
    except Exception as exc:
        return redirect_home(f"Update saved, but calendar sync failed: {exc}")


@app.route("/clear_backlog", methods=["POST"])
def clear_backlog():
    if "credentials" in session:
        try:
            sync_calendar([])
        except Exception:
            pass
    
    # 🔒 Clear local state as well
    save_state([], [])
    return redirect_home("All tasks cleared.")


@app.route("/submit_feedback", methods=["POST"])
def submit_feedback():
    active_tab = request.form.get("active_tab", "pipeline")
    comments = request.form.get("feedback_comments", "").strip()
    rating_fields = {
        "usability": "feedback_usability",
        "interface": "feedback_interface",
        "usefulness": "feedback_usefulness",
    }
    ratings = {}

    for aspect, field_name in rating_fields.items():
        try:
            rating = int(request.form.get(field_name, "0"))
        except ValueError:
            rating = 0

        if rating < 1 or rating > 5:
            return redirect_home("Please rate usability, interface, and usefulness from 1 to 5.", tab=active_tab)

        ratings[aspect] = rating

    save_feedback(ratings, comments)
    return redirect_home("Thanks for the feedback. It helps improve the scheduler.", tab=active_tab)


@app.route("/tool_decompose", methods=["POST"])
def tool_decompose():
    result, error = process_uploaded_file("doc_file", decompose_document)
    if error:
        return redirect_home(error, tab="decompose")

    if result.get("status") == "success":
        session["decompose_result"] = result.get("tasks")
        return redirect_home("Decomposition complete.", tab="decompose")
    return redirect_home(f"Error: {result.get('message')}", tab="decompose")


@app.route("/tool_estimate", methods=["POST"])
def tool_estimate():
    try:
        expert_hours = float(request.form.get("hours", 1))
        complexity = int(request.form.get("complexity", 3))
        task_type = request.form.get("task_type", "general")
        minutes = estimate_duration(expert_hours, complexity, task_type)

        session["estimate_result"] = {
            "hours": expert_hours,
            "complexity": complexity,
            "type": task_type,
            "adhd_minutes": minutes,
        }
        return redirect_home("Prediction generated.", tab="estimate")
    except Exception as exc:
        return redirect_home(f"Estimation Error: {exc}", tab="estimate")


@app.route("/tool_schedule", methods=["POST"])
def tool_schedule():
    login_redirect = require_login(tab="schedule")
    if login_redirect:
        return login_redirect

    try:
        tasks = json.loads(request.form.get("json_tasks", "[]"))
        state = load_state()
        updated_tasks = append_tasks(state["tasks"], tasks)
        sync_calendar(updated_tasks)
        return redirect_home("Custom tasks appended to backlog and scheduled.", tab="schedule")
    except json.JSONDecodeError:
        return redirect_home("Invalid JSON format.", tab="schedule")
    except Exception as exc:
        return redirect_home(f"Scheduling Error: {exc}", tab="schedule")


if __name__ == "__main__":
    app.run(port=8080)