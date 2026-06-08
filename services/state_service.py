import os
from pymongo import MongoClient

# Initialize MongoDB connection safely
mongo_uri = "mongodb+srv://MLAdmin:TestPass1234@mlproject.8tzzzh8.mongodb.net/?appName=MLProject"
client = MongoClient(mongo_uri) if mongo_uri else None

def get_state_collection():
    """Helper function to fetch the collection."""
    if not client:
        raise RuntimeError("MONGO_URI environment variable is missing. Check Azure Configuration.")
    db = client['task_scheduler_db']
    return db['state']

def load_state(user_id):
    """Fetches the state ONLY for the specific user."""
    collection = get_state_collection()
    state = collection.find_one({"user_id": user_id})
    
    if not state:
        return {
            "user_id": user_id,
            "tasks": [],
            "events": [],
            "settings": {
                "attention_span": 25,
                "break_duration": 5,
                "working_hours_config": {}
            }
        }
    
    # Remove the hidden MongoDB object ID so it doesn't break Flask
    state.pop('_id', None)
    return state

def save_state(user_id, tasks, active_event_ids, settings):
    """Overwrites the database ONLY for the specific user."""
    collection = get_state_collection()
    new_state = {
        "user_id": user_id,
        "tasks": tasks,
        "events": active_event_ids,
        "settings": settings
    }
    
    collection.replace_one(
        {"user_id": user_id},
        new_state,
        upsert=True
    )

def build_working_hours(form_data):
    """Parses the HTML form to build the weekly schedule dictionary."""
    working_hours = {}
    days = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']
    
    for day in days:
        # Check if the day's checkbox was ticked in the form
        if form_data.get(day):
            start = form_data.get(f"{day}_start", "08:00 AM")
            end = form_data.get(f"{day}_end", "08:00 PM")
            working_hours[day] = {"start": start, "end": end}
            
    return working_hours