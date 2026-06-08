import json
import os
from pathlib import Path

# 🌟 THE AZURE PERSISTENCE FIX (The only change kept)
if os.environ.get("WEBSITE_SITE_NAME"):
    PERSISTENT_DIR = Path("/home/data")
else:
    PERSISTENT_DIR = Path(__file__).resolve().parent.parent / "artifacts"

PERSISTENT_DIR.mkdir(parents=True, exist_ok=True)
STATE_FILE = PERSISTENT_DIR / "active_schedule.json"

def load_state():
    if STATE_FILE.exists():
        try:
            with STATE_FILE.open("r", encoding="utf-8") as f:
                data = json.load(f)
                if data and "settings" in data:
                    return data
        except (OSError, json.JSONDecodeError):
            pass
            
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
    state_data = {
        "tasks": tasks,
        "events": active_event_ids,
        "settings": settings
    }
    
    with STATE_FILE.open("w", encoding="utf-8") as f:
        json.dump(state_data, f, indent=4)

def build_working_hours(form_data):
    working_hours = {}
    
    # EXACT ORIGINAL LOGIC: Lowercase names, AM/PM format, Dict structure
    days = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']
    
    for day in days:
        if form_data.get(day):
            start = form_data.get(f"{day}_start", "08:00 AM")
            end = form_data.get(f"{day}_end", "08:00 PM")
            working_hours[day] = {"start": start, "end": end}
            
    return working_hours