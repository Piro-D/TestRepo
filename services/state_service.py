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
                # Safely ignore any old database user_id strings if they are stuck in the file
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
    """Parses the HTML form matching the original UI format."""
    working_hours = {}
    
    # Restored to original lowercase format for the UI
    days = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']
    
    for day in days:
        if form_data.get(day):
            start = form_data.get(f"{day}_start", "08:00")
            end = form_data.get(f"{day}_end", "20:00")
            
            # Clean up AM/PM formats just in case
            start = start.replace(" AM", "").replace(" PM", "").strip()
            end = end.replace(" AM", "").replace(" PM", "").strip()
            
            # Restored to original dictionary format so the UI saves correctly
            working_hours[day] = {"start": start, "end": end}
            
    return working_hours