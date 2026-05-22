"""
Google Calendar service for scheduling tasks and managing calendar events.
"""

import datetime
from googleapiclient.discovery import build
from oauth_service import get_credentials_from_session
import config


def get_calendar_service():
    """
    Build and return a Google Calendar service client.
    
    Returns:
        Resource: Google Calendar API service object
        
    Raises:
        RuntimeError: If connection to Google Calendar fails
    """
    try:
        credentials = get_credentials_from_session()
        return build('calendar', 'v3', credentials=credentials)
    except Exception as e:
        raise RuntimeError(f"Cannot connect to Google Calendar API: {str(e)}")


def get_busy_intervals(service, time_min, time_max):
    """
    Fetch busy time intervals from the user's calendar.
    
    Args:
        service: Google Calendar service object
        time_min: Start datetime
        time_max: End datetime
        
    Returns:
        list: List of (start, end) tuples representing busy periods
    """
    try:
        events_result = service.events().list(
            calendarId='primary',
            timeMin=time_min.isoformat(),
            timeMax=time_max.isoformat(),
            singleEvents=True,
            orderBy='startTime'
        ).execute()
        
        events = events_result.get('items', [])
        busy_intervals = []
        
        for event in events:
            if 'dateTime' in event['start']:
                start = datetime.datetime.fromisoformat(event['start']['dateTime'])
                end = datetime.datetime.fromisoformat(event['end']['dateTime'])
                busy_intervals.append((start, end))
                
        return busy_intervals
    except Exception as e:
        print(f"⚠️ Warning: Could not fetch calendar events: {e}. Proceeding with no busy intervals.")
        return []


def is_within_working_hours(target_start, target_end, working_hours_config):
    """
    Check if a time slot falls within working hours based on the per-day dictionary.
    
    Args:
        target_start: Start datetime
        target_end: End datetime
        working_hours_config: Dict mapping day names to working hour blocks
        
    Returns:
        bool: True if slot is within working hours
    """
    day_name = target_start.strftime("%A")
    
    if day_name not in working_hours_config:
        return False
        
    for block in working_hours_config[day_name]:
        allowed_start_dt = datetime.datetime.combine(
            target_start.date(),
            datetime.datetime.strptime(block["start"], "%H:%M").time()
        ).replace(tzinfo=target_start.tzinfo)
        
        allowed_end_dt = datetime.datetime.combine(
            target_start.date(),
            datetime.datetime.strptime(block["end"], "%H:%M").time()
        ).replace(tzinfo=target_start.tzinfo)
        
        if target_start >= allowed_start_dt and target_end <= allowed_end_dt:
            return True
            
    return False


def find_next_free_slot(duration_mins, current_search_time, working_hours, busy_intervals):
    """
    Find the next available calendar slot that fits the duration.
    
    Args:
        duration_mins: Required duration in minutes
        current_search_time: Starting search datetime
        working_hours: Working hours configuration (per-day dictionary)
        busy_intervals: List of busy time periods
        
    Returns:
        tuple: (slot_start, slot_end) datetimes
    """
    while True:
        proposed_end = current_search_time + datetime.timedelta(minutes=duration_mins)
        
        if is_within_working_hours(current_search_time, proposed_end, working_hours):
            conflict = False
            
            for busy_start, busy_end in busy_intervals:
                if current_search_time < busy_end and busy_start < proposed_end:
                    conflict = True
                    current_search_time = busy_end
                    break
                    
            if not conflict:
                return current_search_time, proposed_end
                
        current_search_time += datetime.timedelta(minutes=5)


def build_focus_sessions(ml_tasks, attention_span):
    """
    Divide tasks into focus sessions based on attention span.
    
    Args:
        ml_tasks: List of tasks with 'name' and 'duration_minutes'
        attention_span: Maximum session duration in minutes
        
    Returns:
        list: List of sessions, each containing tasks
    """
    schedule = []
    current_session = []
    current_time = 0

    for task in ml_tasks:
        rem_time = task['duration_minutes']
        
        while rem_time > 0:
            avail = attention_span - current_time
            
            if rem_time <= avail:
                current_session.append({
                    "name": task['name'],
                    "duration": rem_time
                })
                current_time += rem_time
                rem_time = 0
            else:
                current_session.append({
                    "name": task['name'],
                    "duration": avail
                })
                schedule.append(current_session)
                current_session = []
                current_time = 0
                rem_time -= avail
                
            if current_time == attention_span:
                schedule.append(current_session)
                current_session = []
                current_time = 0
                
    if current_session:
        schedule.append(current_session)
        
    return schedule


def push_to_calendar(ml_tasks, session_data):
    """
    Clear old events and push new focus sessions to Google Calendar.
    
    Args:
        ml_tasks: List of tasks processed by ML pipeline
        session_data: User session data with credentials and settings
        
    Returns:
        list: IDs of newly created events
        
    Raises:
        RuntimeError: If calendar operations fail
    """
    service = get_calendar_service()
    
    # 1. Cleanup Old Schedule
    if 'active_event_ids' in session_data:
        for event_id in session_data['active_event_ids']:
            try:
                service.events().delete(calendarId='primary', eventId=event_id).execute()
            except Exception:
                pass
    
    # 2. Build Focus Sessions
    attention_span = session_data.get('attention_span', config.DEFAULT_ATTENTION_SPAN)
    schedule = build_focus_sessions(ml_tasks, attention_span)
    
    # 3. Setup Scheduling Parameters
    now = datetime.datetime.now().astimezone()
    search_horizon = now + datetime.timedelta(days=config.SCHEDULING_HORIZON_DAYS)
    busy_intervals = get_busy_intervals(service, now, search_horizon)
    
    # Load the pre-built, per-day dictionary directly from the session state
    default_config = {day: [{"start": "08:00", "end": "20:00"}] for day in ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]}
    working_hours_config = session_data.get('working_hours_config', default_config)
    
    current_search_time = now
    generated_ids = []

    # 4. Schedule Sessions on Calendar
    for i, sess in enumerate(schedule, 1):
        try:
            duration = sum(t['duration'] for t in sess)
            slot_start, slot_end = find_next_free_slot(
                duration_mins=duration,
                current_search_time=current_search_time,
                working_hours=working_hours_config,
                busy_intervals=busy_intervals
            )
            
            desc = f"Focus Session {i}\n" + "\n".join(
                [f"• {t['name']} ({t['duration']}m)" for t in sess]
            )
            
            event = {
                'summary': f'Focus Session {i}',
                'description': desc,
                'colorId': '11',
                'start': {'dateTime': slot_start.isoformat(), 'timeZone': 'UTC'},
                'end': {'dateTime': slot_end.isoformat(), 'timeZone': 'UTC'},
            }
            
            event_result = service.events().insert(calendarId='primary', body=event).execute()
            generated_ids.append(event_result.get('id'))
            
        except Exception as e:
            print(f"⚠️ Warning: Could not create event {i}: {e}")
        
        break_duration = session_data.get('break_duration', config.DEFAULT_BREAK_DURATION)
        current_search_time = slot_end + datetime.timedelta(minutes=break_duration)
    
    return generated_ids
