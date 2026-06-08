import json
import os
from pathlib import Path

# 🌟 THE AZURE PERSISTENCE FIX
if os.environ.get("WEBSITE_SITE_NAME"):
    PERSISTENT_DIR = Path("/home/data")
else:
    PERSISTENT_DIR = Path(__file__).resolve().parent.parent / "artifacts"

PERSISTENT_DIR.mkdir(parents=True, exist_ok=True)
STATE_FILE = PERSISTENT_DIR / "active_schedule.json"

def load_state():
    """Reads the schedule from the persistent JSON file."""
    if STATE_FILE.exists():
        try:
            with STATE_FILE.open("r", encoding="utf-8") as f:
                data = json.load(f)
                # Safety wipe: If old user_id format is accidentally loaded, ignore it
                if data and any(k.startswith("user_") for k in data.keys()):
                    pass
                elif "settings" in data:
                    return data
        except (OSError, json.JSONDecodeError):
            pass
            
    # Default empty state
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
    """Parses the HTML form and correctly structures it for the calendar service."""
    working_hours = {}
    days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    
    for day in days:
        day_lower = day.lower()
        
        # Check if the frontend sent the checkbox as 'monday' or 'Monday'
        if form_data.get(day_lower) or form_data.get(day):
            start = form_data.get(f"{day_lower}_start") or form_data.get(f"{day}_start") or "08:00"
            end = form_data.get(f"{day_lower}_end") or form_data.get(f"{day}_end") or "20:00"
            
            # Clean up AM/PM formats just in case; Calendar expects strictly "HH:MM"
            start = start.replace(" AM", "").replace(" PM", "").strip()
            end = end.replace(" AM", "").replace(" PM", "").strip()
            
            # IMPORTANT: calendar_service expects a LIST of blocks!
            working_hours[day] = [{"start": start, "end": end}]
            
    return working_hours