"""
ADHD Task Scheduler - Flask Application
Main entry point for the web application.

This module handles:
- Web routes and request handling
- Session management
- Integration between frontend, OAuth, and calendar services
"""

import os
from flask import Flask, redirect, request, session, url_for, render_template
from werkzeug.utils import secure_filename

# Import service modules
from TaskEstimator import estimate_project_tasks
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


# ==========================================
# ML PIPELINE INTEGRATION
# ==========================================
def run_ml_decomposition(filepath):
    """
    Run the ML pipeline to decompose document into tasks.
    
    Args:
        filepath: Path to the uploaded document
        
    Returns:
        list: Formatted tasks with name and duration, or None if failed
    """
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
        
        print(f"✅ Bridge successful. Passed {len(formatted_tasks)} formatted tasks to Scheduler.")
        return formatted_tasks
        
    except Exception as e:
        print(f"❌ ML Pipeline Error: {e}")
        return None


# ==========================================
# WEB ROUTES
# ==========================================
@app.route('/')
def index():
    """Render the main dashboard page."""
    logged_in = 'credentials' in session
    current_span = session.get('attention_span', config.DEFAULT_ATTENTION_SPAN)
    work_start = session.get('work_start', config.DEFAULT_WORK_START)
    work_end = session.get('work_end', config.DEFAULT_WORK_END)
    working_days = session.get('working_days', config.DEFAULT_WORKING_DAYS)
    break_duration = session.get('break_duration', config.DEFAULT_BREAK_DURATION)
    message = request.args.get('message')
    has_saved_tasks = 'saved_ml_tasks' in session
    
    return render_template(
        'index.html',
        logged_in=logged_in,
        current_span=current_span,
        work_start=work_start,
        work_end=work_end,
        working_days=working_days,
        break_duration=break_duration,
        message=message,
        has_saved_tasks=has_saved_tasks
    )


@app.route('/authorize')
def authorize():
    """Redirect user to Google OAuth authorization."""
    try:
        authorization_url, state, code_verifier = get_authorization_url()
        session['state'] = state
        session['code_verifier'] = code_verifier
        return redirect(authorization_url)
    except Exception as e:
        error_msg = f"❌ Google OAuth Error: {str(e)}"
        return redirect(url_for('index', message=error_msg))


@app.route('/oauth2callback')
def oauth2callback():
    """Handle the OAuth callback from Google."""
    try:
        state = session.get('state')
        code_verifier = session.get('code_verifier')
        credentials = handle_oauth_callback(request.url, state, code_verifier)
        session['credentials'] = credentials
        session.pop('state', None)
        session.pop('code_verifier', None)
        return redirect(url_for('index'))
    except Exception as e:
        error_msg = f"❌ OAuth Callback Error: {str(e)}"
        return redirect(url_for('index', message=error_msg))


@app.route('/logout')
def logout():
    """Log out the user and clear session."""
    session.clear()
    return redirect(url_for('index'))


@app.route('/update_settings', methods=['POST'])
def update_settings():
    """
    Update user settings (attention span, working hours, working days).
    If tasks are cached, instantly recalculate and update the calendar.
    """
    # Save settings
    session['attention_span'] = int(request.form.get('span', config.DEFAULT_ATTENTION_SPAN))
    session['work_start'] = request.form.get('work_start', config.DEFAULT_WORK_START)
    session['work_end'] = request.form.get('work_end', config.DEFAULT_WORK_END)
    session['break_duration'] = int(request.form.get('break_duration', config.DEFAULT_BREAK_DURATION))
    
    # Handle working days checkboxes
    working_days = request.form.getlist('working_days')
    if working_days:
        session['working_days'] = working_days
    else:
        session['working_days'] = config.DEFAULT_WORKING_DAYS
    
    # Apply to calendar if tasks are cached
    if 'saved_ml_tasks' in session and 'credentials' in session:
        try:
            generated_ids = push_to_calendar(session['saved_ml_tasks'], session)
            session['active_event_ids'] = generated_ids
            return redirect(url_for('index', message="✅ Settings saved & Calendar updated!"))
        except Exception as e:
            return redirect(url_for('index', message=f"⚠️ Settings saved, but calendar update failed: {e}"))
    
    return redirect(url_for('index', message="✅ Settings saved!"))


@app.route('/schedule_tasks', methods=['POST'])
def schedule_tasks():
    """
    Upload a document, run ML pipeline, and push tasks to Google Calendar.
    """
    # Check authentication
    if 'credentials' not in session:
        return redirect(url_for('index', message="❌ Please log in to Google first."))

    # Validate file
    if 'task_file' not in request.files:
        return redirect(url_for('index', message="❌ Error: No file uploaded."))
    
    file = request.files['task_file']
    if file.filename == '':
        return redirect(url_for('index', message="❌ Error: No file selected."))

    # Save uploaded file
    filename = secure_filename(file.filename)
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    file.save(filepath)

    # Run ML pipeline
    ml_tasks = run_ml_decomposition(filepath)
    
    # Clean up uploaded file
    try:
        os.remove(filepath)
    except Exception:
        pass

    # Check if pipeline succeeded
    if not ml_tasks:
        return redirect(url_for('index', message="❌ Error: The AI pipeline could not process the document."))

    # Cache results in session
    session['saved_ml_tasks'] = ml_tasks

    # Push to calendar
    try:
        generated_ids = push_to_calendar(ml_tasks, session)
        session['active_event_ids'] = generated_ids
        message = f"✅ Success! AI processed the document and pushed tasks to your Google Calendar."
        return redirect(url_for('index', message=message))
    except Exception as e:
        error_msg = f"⚠️ Document processed but calendar update failed: {str(e)}"
        return redirect(url_for('index', message=error_msg))


# ==========================================
# APPLICATION ENTRY POINT
# ==========================================
if __name__ == '__main__':
    app.run(port=8080, debug=True)