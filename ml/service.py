import config
from ml.duration_estimator import predict_duration_adhd
from ml.llm_decomposition import process_document
from ml.task_estimator import estimate_project_tasks


def run_ml_decomposition(filepath):
    try:
        pipeline_result = estimate_project_tasks(filepath, buffer=config.BUFFER_MULTIPLIER)
        if pipeline_result.get("status") != "success":
            print(f"Pipeline Error: {pipeline_result.get('message')}")
            return None

        formatted_tasks = []
        for task in pipeline_result.get("tasks", []):
            try:
                formatted_tasks.append(
                    {
                        "name": task.get("task_name", "Unnamed Task"),
                        "duration_minutes": int(task.get("estimated_duration_minutes", 60)),
                    }
                )
            except (TypeError, ValueError) as exc:
                print(f"Warning: Could not parse task data: {task} | Error: {exc}")

        print(f"Bridge successful. Passed {len(formatted_tasks)} formatted tasks.")
        return formatted_tasks
    except Exception as exc:
        print(f"ML Pipeline Error: {exc}")
        return None


def decompose_document(filepath):
    return process_document(filepath)


def estimate_duration(expert_hours, complexity, task_type):
    return predict_duration_adhd(
        expert_hours * 3600,
        complexity,
        task_type,
        buffer=config.BUFFER_MULTIPLIER,
    )
