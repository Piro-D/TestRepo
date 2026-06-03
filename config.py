import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

RUNTIME_DIR = BASE_DIR / "instance"
ARTIFACTS_DIR = BASE_DIR / "artifacts"
UPLOAD_FOLDER = BASE_DIR / "uploads"

for directory in (RUNTIME_DIR, ARTIFACTS_DIR, UPLOAD_FOLDER):
    directory.mkdir(exist_ok=True)

# Flask Configuration
SECRET_KEY = "super_secret_adhd_scheduler_key"

# Google OAuth Configuration
SCOPES = [
    'https://www.googleapis.com/auth/calendar.events',
    'https://www.googleapis.com/auth/calendar.readonly'
]
CLIENT_SECRETS_FILE = "credentials.json"

# File Upload Configuration
ALLOWED_EXTENSIONS = {'.pdf', '.doc', '.docx'}
ACTIVE_SCHEDULE_FILE = RUNTIME_DIR / "active_schedule.json"
CLEANED_DATASET_FILE = ARTIFACTS_DIR / "cleaned_dataset.csv"
TASK_ESTIMATES_FILE = ARTIFACTS_DIR / "task_estimates.json"
FEEDBACK_FILE = ARTIFACTS_DIR / "feedback.json"

# Default Settings
DEFAULT_ATTENTION_SPAN = 20  # minutes
DEFAULT_WORK_START = '08:00'
DEFAULT_WORK_END = '20:00'
DEFAULT_WORKING_DAYS = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday']
DEFAULT_BREAK_DURATION = 5  # minutes between sessions
SCHEDULING_HORIZON_DAYS = 14
BUFFER_MULTIPLIER = 1.2

# Session Duration Options (in minutes)
MIN_ATTENTION_SPAN = 5
MAX_ATTENTION_SPAN = 120
MIN_BREAK_DURATION = 0
MAX_BREAK_DURATION = 60

# OAuth Security Flag (for local testing)
os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'
