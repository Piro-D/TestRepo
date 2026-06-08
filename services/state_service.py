import json
import os
from pathlib import Path

# 🌟 THE AZURE PERSISTENCE FIX
# If running on Azure, use the permanent /home/data folder. 
# If running locally on your laptop, put it in the local artifacts folder.
if os.environ.get("WEBSITE_SITE_NAME"):
    PERSISTENT_DIR = Path("/home/data")
else:
    PERSISTENT_DIR = Path(__file__).resolve().parent.parent / "artifacts"

# Ensure the directory exists
PERSISTENT_DIR.mkdir(parents=True, exist_ok=True)
STATE_FILE = PERSISTENT_DIR / "active_schedule.json"

def load_state():
    """Reads the schedule from the persistent JSON file."""
    if STATE_FILE.exists():
        try:
            with STATE_FILE.open("r", encoding="utf-8") as f:
                return json.load(f)
        except (OSError, json.JSONDecodeError):
            pass
            
    # Default empty state if the file doesn't exist yet
    return {
        "tasks": [],
        "events": [],
        "settings": {
            "attention_span": 25,
            "break_duration": 5,
            "working_hours_config": {}
        }
    }

def save_state(tasks, active_event_ids, settings):
    """Saves the schedule to the persistent JSON file."""
    state_data = {
        "tasks": tasks,
        "events": active_event_ids,
        "settings": settings
    }
    
    with STATE_FILE.open("w", encoding="utf-8") as f:
        json.dump(state_data, f, indent=4)

def build_working_hours(form_data):
    """Parses the HTML form to build the weekly schedule dictionary."""
    working_hours = {}
    days = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']
    
    for day in days:
        if form_data.get(day):
            start = form_data.get(f"{day}_start", "08:00 AM")
            end = form_data.get(f"{day}_end", "08:00 PM")
            working_hours[day] = {"start": start, "end": end}
            
    return working_hours