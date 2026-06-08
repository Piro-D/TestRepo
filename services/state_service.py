import json
import os
from pathlib import Path

# 🌟 THE AZURE PERSISTENCE FIX
if os.environ.get("WEBSITE_SITE_NAME"):
    PERSISTENT_DIR = Path("/home/data")
else:
    PERSISTENT_DIR = Path(__file__).resolve().parent.parent / "artifacts"

PERSISTENT_DIR.mkdir(parents=True, exist_ok=True)

# 🌟 EXACT ORIGINAL FILENAME RESTORED
STATE_FILE = PERSISTENT_DIR / "state.json"

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
    days = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']
    
    # Converts every single HTML key to lowercase so it cannot miss
    form_lower = {k.lower(): v for k, v in form_data.items()}
    
    for day in days:
        if day in form_lower:
            start = form_lower.get(f"{day}_start", "08:00")
            end = form_lower.get(f"{day}_end", "20:00")
            
            # HTML5 TIME FIX: Strips any AM/PM text so the browser time-picker doesn't crash
            start = start.upper().replace(" AM", "").replace(" PM", "").strip()
            end = end.upper().replace(" AM", "").replace(" PM", "").strip()
            
            if len(start) > 5: start = start[:5]
            if len(end) > 5: end = end[:5]
            
            working_hours[day] = {"start": start, "end": end}
            
    return working_hours