import json

import config


WEEKDAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]


def default_settings():
    return {
        "attention_span": config.DEFAULT_ATTENTION_SPAN,
        "break_duration": config.DEFAULT_BREAK_DURATION,
        "working_hours_config": {
            day: [{"start": config.DEFAULT_WORK_START, "end": config.DEFAULT_WORK_END}]
            for day in WEEKDAYS
        },
    }


def default_state():
    return {"tasks": [], "events": [], "settings": default_settings()}


def normalize_state(data):
    state = default_state()
    if isinstance(data, dict):
        state["tasks"] = data.get("tasks") or []
        state["events"] = data.get("events") or []
        state["settings"].update(data.get("settings") or {})
    return state


def load_state():
    if not config.ACTIVE_SCHEDULE_FILE.exists():
        return default_state()

    try:
        with config.ACTIVE_SCHEDULE_FILE.open("r", encoding="utf-8") as state_file:
            return normalize_state(json.load(state_file))
    except (OSError, json.JSONDecodeError):
        return default_state()


def save_state(tasks, events, settings=None):
    current_settings = settings if settings is not None else load_state()["settings"]
    state = {"tasks": tasks, "events": events, "settings": current_settings}

    with config.ACTIVE_SCHEDULE_FILE.open("w", encoding="utf-8") as state_file:
        json.dump(state, state_file, indent=4)


def build_working_hours(form):
    selected_days = form.getlist("working_days")
    return {
        day: [
            {
                "start": form.get(f"{day}_start", config.DEFAULT_WORK_START),
                "end": form.get(f"{day}_end", config.DEFAULT_WORK_END),
            }
        ]
        for day in selected_days
    }
