import sys
from pathlib import Path

if __package__ is None or __package__ == "":
    sys.path.append(str(Path(__file__).resolve().parents[1]))

import config
from ml.duration_estimator import estimate_tasks_from_llm, load_model_objects, train_evaluate_and_save
from ml.llm_decomposition import DEFAULT_MODEL, ensure_model, process_document




def estimate_project_tasks(document_path: str, buffer=1.2) -> dict:
    print("\n" + "=" * 60)
    print("TASK ESTIMATOR - PROJECT DECOMPOSITION & DURATION ESTIMATION")
    print("=" * 60 + "\n")

    print(f"Loading LLM model: {DEFAULT_MODEL}...")
    try:
        ensure_model(DEFAULT_MODEL)
    except Exception as e:
        return {"status": "error", "message": f"Failed to load LLM model: {e}"}

    print("Checking duration estimator models...")
    model, le_task = load_model_objects()
    if model is None:
        print("Duration estimator models not found. Training new model...")
        train_evaluate_and_save()
        model, le_task = load_model_objects()
        if model is None:
            return {"status": "error", "message": "Failed to train duration estimator model"}

    print(f"\nProcessing document: {document_path}")
    decomposition_result = process_document(document_path)

    if decomposition_result.get("status") != "success":
        return decomposition_result

    tasks = decomposition_result.get("tasks", [])
    response_time = decomposition_result.get("response_time_seconds", 0)
    print(f"Decomposition complete in {response_time}s. Found {len(tasks)} tasks.")

    valid_tasks = []
    for task in tasks:
        if isinstance(task, dict):
            valid_tasks.append(task)
        else:
            print(f"Warning: Skipping invalid task format (expected dict, got {type(task).__name__})")

    tasks = valid_tasks
    if not tasks:
        return {"status": "error", "message": "No valid tasks found after decomposition"}

    print(f"Valid tasks: {len(tasks)}")
    print("\nEstimating task durations...")
    estimated_tasks = estimate_tasks_from_llm(tasks, buffer=buffer)

    total_minutes = sum(
        task.get('estimated_duration_minutes', 0)
        for task in estimated_tasks
        if task.get('estimated_duration_minutes')
    )

    print("\n" + "=" * 60)
    print("RESULTS")
    print("=" * 60)
    for i, task in enumerate(estimated_tasks, 1):
        name = task.get('task_name', task.get('task_nameiname', 'Unnamed Task'))
        complexity = task.get('task_complexity', '?')
        task_type = task.get('task_type', 'general')
        llm_est = task.get('general_estimation', '?')
        duration = task.get('estimated_duration_minutes', 'N/A')

        print(f"\n{i}. {name}")
        print(f"   Type: {task_type} | Complexity: {complexity}/5")
        print(f"   LLM Estimate: {llm_est} min | Estimated Actual Duration: {duration} min")

    print("\n" + "=" * 60)
    print(f"TOTAL PROJECT TIME (ADHD): {total_minutes:.0f} minutes ({total_minutes / 60:.1f} hours)")
    print("=" * 60 + "\n")

    return {
        "status": "success",
        "document": document_path,
        "decomposition_time_seconds": response_time,
        "tasks_count": len(estimated_tasks),
        "tasks": estimated_tasks,
        "total_duration_minutes": total_minutes
    }


if __name__ == "__main__":
    import json

    document_file = config.BASE_DIR / "TestDocuments" / "document3.docx"
    result = estimate_project_tasks(str(document_file), buffer=1.2)

    with config.TASK_ESTIMATES_FILE.open("w", encoding="utf-8") as f:
        json.dump(result, f, indent=4)

    print(f"\nResults saved to {config.TASK_ESTIMATES_FILE}")
