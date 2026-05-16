"""
Configuration settings for the ADHD Task Scheduler application.
"""

import os

# Flask Configuration
SECRET_KEY = "super_secret_adhd_scheduler_key"

# Google OAuth Configuration
SCOPES = [
    'https://www.googleapis.com/auth/calendar.events',
    'https://www.googleapis.com/auth/calendar.readonly'
]
CLIENT_SECRETS_FILE = "credentials.json"

# File Upload Configuration
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'.pdf', '.doc', '.docx'}

# Create upload folder if it doesn't exist
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

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
