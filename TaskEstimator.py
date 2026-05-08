import json
from LLM_Decomposition import process_document, ensure_model, DEFAULT_MODEL
from DurationEstimator import estimate_tasks_from_llm, train_evaluate_and_save, load_model_objects

# Function to test integration of LLM decomposition and duration estimation
def estimate_project_tasks(document_path: str, buffer=1.2) -> dict:
    
    print("\n" + "="*60)
    print("TASK ESTIMATOR - PROJECT DECOMPOSITION & DURATION ESTIMATION")
    print("="*60 + "\n")
    
    # Step 1: Ensure LLM model is available
    print(f"Loading LLM model: {DEFAULT_MODEL}...")
    try:
        ensure_model(DEFAULT_MODEL)
    except Exception as e:
        return {"status": "error", "message": f"Failed to load LLM model: {e}"}
    
    # Step 2: Check if duration estimator models exist
    print("🔍 Checking duration estimator models...")
    model, le_task = load_model_objects()
    if model is None:
        print("⚠️  Duration estimator models not found. Training new model...")
        train_evaluate_and_save()
        model, le_task = load_model_objects()
        if model is None:
            return {"status": "error", "message": "Failed to train duration estimator model"}
    
    # Step 3: Decompose document
    print(f"\nProcessing document: {document_path}")
    decomposition_result = process_document(document_path)
    
    if decomposition_result["status"] != "success":
        return decomposition_result
    
    tasks = decomposition_result.get("tasks", [])
    response_time = decomposition_result.get("response_time_seconds", 0)
    print(f"Decomposition complete in {response_time}s. Found {len(tasks)} tasks.")
    
    # Step 4: Estimate duration for each task
    print(f"\nEstimating task durations...")
    estimated_tasks = estimate_tasks_from_llm(tasks, buffer=buffer)
    
    # Step 5: Compile results
    total_minutes = sum(t.get('estimated_duration_minutes', 0) for t in estimated_tasks if t.get('estimated_duration_minutes'))
    
    print("\n" + "="*60)
    print("RESULTS")
    print("="*60)
    for i, task in enumerate(estimated_tasks, 1):
        complexity = task.get('task_complexity', '?')
        duration = task.get('estimated_duration_minutes', 'N/A')
        print(f"\n{i}. {task['task_name']}")
        print(f"   Type: {task['task_type']} | Complexity: {complexity}/5")
        print(f"   LLM Estimate: {task['general_estimation']}h | ⏱️ ADHD Duration: {duration} min")
    
    print("\n" + "="*60)
    print(f"📈 TOTAL PROJECT TIME (ADHD): {total_minutes:.0f} minutes ({total_minutes/60:.1f} hours)")
    print("="*60 + "\n")
    
    return {
        "status": "success",
        "document": document_path,
        "decomposition_time_seconds": response_time,
        "tasks_count": len(estimated_tasks),
        "tasks": estimated_tasks,
        "total_duration_minutes": total_minutes
    }


if __name__ == "__main__":
    # Example usage
    document_file = r".\TestDocuments\document3.docx"
    
    result = estimate_project_tasks(document_file, buffer=1.2)
    
    # Save results to file
    with open("task_estimates.json", "w") as f:
        json.dump(result, f, indent=4)
    
    print("\n Results saved to task_estimates.json")
