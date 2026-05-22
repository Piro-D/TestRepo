"""
ADHD Task Scheduler - Flask Application
Main entry point for the web application.
"""

import os
import json
import uuid
from flask import Flask, redirect, request, session, url_for, render_template
from werkzeug.utils import secure_filename

# Import service modules
from TaskEstimator import estimate_project_tasks
from LLM_Decomposition import process_document
from DurationEstimator import predict_duration_adhd
from oauth_service import get_authorization_url, handle_oauth_callback
from calendar_service import push_to_calendar
import config

# ==========================================
# APP INITIALIZATION
# ==========================================
app = Flask(__name__, static_folder='static', static_url_path='/static')
app.secret_key = config.SECRET_KEY
app.config['UPLOAD_FOLDER'] = config.UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

ACTIVE_SCHEDULE_FILE = 'active_schedule.json'

# ==========================================
# FILE-BASED STATE MANAGEMENT (Tasks, Events, AND Settings)
# ==========================================
def load_state():
    """Load the task backlog, calendar events, and settings from a local file safely."""
    default_settings = {
        "attention_span": config.DEFAULT_ATTENTION_SPAN,
        "break_duration": config.DEFAULT_BREAK_DURATION,
        "working_hours_config": {day: [{"start": "08:00", "end": "20:00"}] for day in ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]}
    }
    default_state = {"tasks": [], "events": [], "settings": default_settings}
    
    if not os.path.exists(ACTIVE_SCHEDULE_FILE):
        return default_state
        
    try:
        with open(ACTIVE_SCHEDULE_FILE, 'r') as f:
            data = json.load(f)
            # Ensure the keys exist, if not, patch them in with defaults
            if 'settings' not in data:
                data['settings'] = default_settings
            if 'tasks' not in data:
                data['tasks'] = []
            if 'events' not in data:
                data['events'] = []
            return data
    except (json.JSONDecodeError, KeyError):
        return default_state

def save_state(tasks, events, settings=None):
    """Save the state to a local file. Keeps existing settings if none are provided."""
    if settings is None:
        settings = load_state()['settings']
        
    with open(ACTIVE_SCHEDULE_FILE, 'w') as f:
        json.dump({"tasks": tasks, "events": events, "settings": settings}, f, indent=4)

def sync_calendar(tasks):
    """
    Centralized function to delete old events, schedule new ones, 
    and save the new state to the JSON file.
    """
    state = load_state()
    
    # We combine the session credentials with the file-based settings and event IDs
    sync_data = dict(session)
    sync_data['attention_span'] = state['settings']['attention_span']
    sync_data['break_duration'] = state['settings']['break_duration']
    sync_data['working_hours_config'] = state['settings']['working_hours_config']
    sync_data['active_event_ids'] = state.get('events', [])
    
    # Push to Google Calendar
    new_event_ids = push_to_calendar(tasks, sync_data)
    
    # Save the updated task list and new calendar IDs to our file
    save_state(tasks, new_event_ids, state['settings'])

# ==========================================
# ML PIPELINE INTEGRATION
# ==========================================
def run_ml_decomposition(filepath):
    print(f"\n🚀 Bridging to TaskEstimator.py...")
    try:
        pipeline_result = estimate_project_tasks(filepath, buffer=config.BUFFER_MULTIPLIER)
        if pipeline_result.get("status") != "success":
            print(f"❌ Pipeline Error: {pipeline_result.get('message')}")
            return None
        
        formatted_tasks = []
        for task in pipeline_result.get("tasks", []):
            try:
                duration = int(task.get("estimated_duration_minutes", 60))
                formatted_tasks.append({
                    "name": task.get("task_name", "Unnamed Task"),
                    "duration_minutes": duration
                })
            except Exception as e:
                print(f"⚠️ Warning: Could not parse task data: {task} | Error: {e}")
        
        print(f"✅ Bridge successful. Passed {len(formatted_tasks)} formatted tasks.")
        return formatted_tasks
    except Exception as e:
        print(f"❌ ML Pipeline Error: {e}")
        return None

# ==========================================
# WEB ROUTES - DASHBOARD
# ==========================================
@app.route('/')
def index():
    logged_in = 'credentials' in session
    message = request.args.get('message')
    active_tab = request.args.get('tab', 'pipeline')
    decompose_result = session.pop('decompose_result', None)
    estimate_result = session.pop('estimate_result', None)
    
    # Fetch EVERYTHING from the persistent file state
    state = load_state()
    saved_tasks = state['tasks']
    has_saved_tasks = len(saved_tasks) > 0
    
    current_span = state['settings']['attention_span']
    break_duration = state['settings']['break_duration']
    working_hours_config = state['settings']['working_hours_config']
    
    return render_template(
        'index.html',
        logged_in=logged_in,
        current_span=current_span,
        working_hours_config=working_hours_config,
        break_duration=break_duration,
        message=message,
        active_tab=active_tab,
        decompose_result=decompose_result,
        estimate_result=estimate_result,
        saved_tasks=saved_tasks,
        has_saved_tasks=has_saved_tasks
    )

# ==========================================
# WEB ROUTES - AUTHENTICATION
# ==========================================
@app.route('/authorize')
def authorize():
    try:
        authorization_url, state, code_verifier = get_authorization_url()
        session['state'] = state
        session['code_verifier'] = code_verifier
        return redirect(authorization_url)
    except Exception as e:
        return redirect(url_for('index', message=f"❌ Google OAuth Error: {str(e)}"))

@app.route('/oauth2callback')
def oauth2callback():
    try:
        credentials = handle_oauth_callback(request.url, session.get('state'), session.get('code_verifier'))
        session['credentials'] = credentials
        session.pop('state', None)
        session.pop('code_verifier', None)
        return redirect(url_for('index'))
    except Exception as e:
        return redirect(url_for('index', message=f"❌ OAuth Callback Error: {str(e)}"))

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

# ==========================================
# WEB ROUTES - ACTIONS & TOOLS
# ==========================================
@app.route('/update_settings', methods=['POST'])
def update_settings():
    state = load_state()
    
    # Update settings inside the state object
    state['settings']['attention_span'] = int(request.form.get('span', config.DEFAULT_ATTENTION_SPAN))
    state['settings']['break_duration'] = int(request.form.get('break_duration', config.DEFAULT_BREAK_DURATION))
    
    selected_days = request.form.getlist('working_days')
    new_config = {}
    for day in selected_days:
        new_config[day] = [{"start": request.form.get(f"{day}_start", "08:00"), "end": request.form.get(f"{day}_end", "20:00")}]
    state['settings']['working_hours_config'] = new_config
    
    # Save the updated settings to the file permanently
    save_state(state['tasks'], state.get('events', []), state['settings'])
    
    # Resync the calendar using the new settings
    if state['tasks'] and 'credentials' in session:
        try:
            sync_calendar(state['tasks'])
            return redirect(url_for('index', message="✅ Settings saved & Calendar dynamically updated!", tab='pipeline'))
        except Exception as e:
            return redirect(url_for('index', message=f"⚠️ Settings saved, but Calendar update failed: {e}", tab='pipeline'))
            
    return redirect(url_for('index', message="✅ Schedule configuration saved!", tab='pipeline'))

@app.route('/schedule_tasks', methods=['POST'])
def schedule_tasks():
    """Upload Document and APPEND to Task Backlog"""
    if 'credentials' not in session: return redirect(url_for('index', message="❌ Log in first.", tab='pipeline'))
    if 'task_file' not in request.files or request.files['task_file'].filename == '':
        return redirect(url_for('index', message="❌ No file selected.", tab='pipeline'))

    file = request.files['task_file']
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], secure_filename(file.filename))
    file.save(filepath)

    new_ml_tasks = run_ml_decomposition(filepath)
    try: os.remove(filepath)
    except Exception: pass

    if not new_ml_tasks: return redirect(url_for('index', message="❌ AI processing failed.", tab='pipeline'))

    state = load_state()
    existing_tasks = state['tasks']
    
    for t in new_ml_tasks:
        t['id'] = str(uuid.uuid4())
        existing_tasks.append(t)

    try:
        sync_calendar(existing_tasks)
        return redirect(url_for('index', message="✅ Document parsed! Tasks appended to backlog and scheduled.", tab='pipeline'))
    except Exception as e:
        return redirect(url_for('index', message=f"⚠️ Scheduled failed: {str(e)}", tab='pipeline'))

# ==========================================
# BACKLOG MANAGEMENT ROUTES
# ==========================================
@app.route('/update_backlog', methods=['POST'])
def update_backlog():
    if 'credentials' not in session: return redirect(url_for('index', message="❌ Log in first."))
    
    state = load_state()
    task_ids = request.form.getlist('task_ids')
    updated_tasks = []
    
    for t_id in task_ids:
        if request.form.get(f'complete_{t_id}'):
            continue
        
        new_duration = int(request.form.get(f'duration_{t_id}', 0))
        new_name = request.form.get(f'name_{t_id}', "Task")
        
        if new_duration > 0:
            original = next((t for t in state['tasks'] if t.get('id') == t_id), None)
            if original:
                original['name'] = new_name
                original['duration_minutes'] = new_duration
                updated_tasks.append(original)
            else:
                updated_tasks.append({"id": t_id, "name": new_name, "duration_minutes": new_duration})
    
    try:
        sync_calendar(updated_tasks)
        return redirect(url_for('index', message="✅ Backlog updated & Calendar synced!", tab='pipeline'))
    except Exception as e:
        return redirect(url_for('index', message=f"⚠️ Update saved, but Calendar sync failed: {e}", tab='pipeline'))

@app.route('/clear_backlog', methods=['POST'])
def clear_backlog():
    if 'credentials' in session:
        try:
            sync_calendar([]) 
        except: pass
    return redirect(url_for('index', message="🧹 All tasks cleared!", tab='pipeline'))

# ==========================================
# INDIVIDUAL TOOL ROUTES
# ==========================================
@app.route('/tool_decompose', methods=['POST'])
def tool_decompose():
    if 'doc_file' not in request.files or request.files['doc_file'].filename == '':
        return redirect(url_for('index', message="❌ No file selected.", tab='decompose'))
        
    file = request.files['doc_file']
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], secure_filename(file.filename))
    file.save(filepath)
    
    result = process_document(filepath)
    try: os.remove(filepath)
    except: pass
    
    if result.get('status') == 'success':
        session['decompose_result'] = result.get('tasks')
        return redirect(url_for('index', message="✅ Decomposition complete!", tab='decompose'))
    return redirect(url_for('index', message=f"❌ Error: {result.get('message')}", tab='decompose'))

@app.route('/tool_estimate', methods=['POST'])
def tool_estimate():
    try:
        expert_hours = float(request.form.get('hours', 1))
        complexity = int(request.form.get('complexity', 3))
        task_type = request.form.get('task_type', 'general')
        
        minutes = predict_duration_adhd(expert_hours * 3600, complexity, task_type, buffer=config.BUFFER_MULTIPLIER)
        
        session['estimate_result'] = {
            "hours": expert_hours, "complexity": complexity, "type": task_type, "adhd_minutes": minutes
        }
        return redirect(url_for('index', message="✅ Prediction generated!", tab='estimate'))
    except Exception as e:
        return redirect(url_for('index', message=f"❌ Estimation Error: {str(e)}", tab='estimate'))

@app.route('/tool_schedule', methods=['POST'])
def tool_schedule():
    if 'credentials' not in session: return redirect(url_for('index', message="❌ Log in first.", tab='schedule'))
    try:
        raw_json = request.form.get('json_tasks', '[]')
        tasks = json.loads(raw_json)
        
        state = load_state()
        existing_tasks = state['tasks']
        
        for t in tasks:
            clean_task = {
                "id": str(uuid.uuid4()), 
                "name": t.get("name", "Manual Task"), 
                "duration_minutes": int(t.get("duration_minutes", 30))
            }
            existing_tasks.append(clean_task)
            
        sync_calendar(existing_tasks)
        return redirect(url_for('index', message="✅ Custom tasks appended to backlog and scheduled!", tab='schedule'))
    except json.JSONDecodeError:
        return redirect(url_for('index', message="❌ Invalid JSON format.", tab='schedule'))
    except Exception as e:
        return redirect(url_for('index', message=f"❌ Scheduling Error: {str(e)}", tab='schedule'))

if __name__ == '__main__':
    app.run(port=8080, debug=True)
