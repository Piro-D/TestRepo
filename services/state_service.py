import json
from pathlib import Path

# 🌟 THE AZURE PERSISTENCE FIX
# Force the app to save the state on the permanent Azure drive so it survives restarts.
STATE_FILE = Path("/home/site/wwwroot/state.json")

def _read_all_users():
    """Helper to read the entire JSON file containing all users."""
    if STATE_FILE.exists():
        try:
            with STATE_FILE.open("r", encoding="utf-8") as f:
                return json.load(f)
        except (OSError, json.JSONDecodeError):
            pass
    return {}

def _write_all_users(data):
    """Helper to safely overwrite the JSON file."""
    with STATE_FILE.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)

def load_state(user_id):
    """Fetches the state ONLY for the specific user from the JSON file."""
    all_data = _read_all_users()
    
    # If the user doesn't exist yet, return the defaults
    if user_id not in all_data:
        return {
            "tasks": [],
            "events": [],
            "settings": {
                "attention_span": 25,
                "break_duration": 5,
                "working_hours_config": {}
            }
        }
        
    return all_data[user_id]

def save_state(user_id, tasks, active_event_ids, settings):
    """Overwrites the specific user's state in the JSON file."""
    all_data = _read_all_users()
    
    all_data[user_id] = {
        "tasks": tasks,
        "events": active_event_ids,
        "settings": settings
    }
    
    _write_all_users(all_data)

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