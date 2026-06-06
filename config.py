import os
from pathlib import Path
from dotenv import load_dotenv

# 🌟 THE BRIDGE: Load variables from the .env file (Azure uses App Settings natively)
load_dotenv()

BASE_DIR = Path(__file__).resolve().parent

RUNTIME_DIR = BASE_DIR / "instance"
ARTIFACTS_DIR = BASE_DIR / "artifacts"
UPLOAD_FOLDER = BASE_DIR / "uploads"

for directory in (RUNTIME_DIR, ARTIFACTS_DIR, UPLOAD_FOLDER):
    directory.mkdir(exist_ok=True)

# 🔒 SECURITY UPDATES FOR CLOUD DEPLOYMENT
# Azure MUST have FLASK_SECRET_KEY set in its Environment Variables.
SECRET_KEY = os.getenv("FLASK_SECRET_KEY", "fallback_local_dev_key_only")

# API Keys
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")

# Google OAuth Configuration
SCOPES = [
    'https://www.googleapis.com/auth/calendar.events',
    'https://www.googleapis.com/auth/calendar.readonly'
]
CLIENT_SECRETS_FILE = "credentials.json"

# File Upload Configuration
ALLOWED_EXTENSIONS = {'.pdf', '.doc', '.docx'}
ACTIVE_SCHEDULE_FILE = RUNTIME_DIR / "active_schedule.json" # Kept for fallback, overridden in state_service.py
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

# 🔒 Disable Insecure Transport in Production (Azure uses HTTPS)
if os.getenv("FLASK_ENV") == "development":
    os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'
elif 'OAUTHLIB_INSECURE_TRANSPORT' in os.environ:
    del os.environ['OAUTHLIB_INSECURE_TRANSPORT']