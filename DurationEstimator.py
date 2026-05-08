"""
ADHD Academic Task Duration Estimator - High Accuracy Version
Features: IQR Outlier Removal, Dataset Cleaning, and Optimized Random Forest.
"""

import pandas as pd
import numpy as np
import joblib
import os
import warnings
from pathlib import Path

from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.ensemble import RandomForestRegressor
from sklearn.preprocessing import LabelEncoder
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

warnings.filterwarnings('ignore')

# 1. PATH CONFIGURATION ------------------------------------------------------------------------------------------------
BASE_DIR = Path(__file__).parent
DATA_PATH = BASE_DIR / "Datasets" / "preprocessed_jira_data.csv"
MODELS_DIR = BASE_DIR / "models"
MODELS_DIR.mkdir(exist_ok=True)



# 2. TRAINING & EVALUATION FUNCTION ------------------------------------------------------------------------------------------------
def train_evaluate_and_save():
    if not DATA_PATH.exists():
        print(f"Error: Dataset not found at {DATA_PATH}")
        return

    # Cleanup old models
    for f in ['duration_model.pkl', 'encoder_task_type.pkl']:
        model_file = MODELS_DIR / f
        if model_file.exists(): model_file.unlink()

    df = pd.read_csv(DATA_PATH)
    
    # --- INITIAL CLEANING ---
    df = df[(df['expert_estimated_effort'] > 0) & (df['actual_effort'] > 0)].copy()

    # ---  IQR OUTLIER REMOVAL ---
    Q1 = df['actual_effort'].quantile(0.25)
    Q3 = df['actual_effort'].quantile(0.75)
    IQR = Q3 - Q1
    
    lower_bound = Q1 - 1.5 * IQR
    upper_bound = Q3 + 1.5 * IQR
    df_clean = df[(df['actual_effort'] >= lower_bound) & (df['actual_effort'] <= upper_bound)].copy()
    
    removed_count = len(df) - len(df_clean)
    print(f"Outlier Removal: Deleted {removed_count} noisy rows.")
    print(f"Final Dataset Size: {len(df_clean)} rows.")

    # --- ENCODING ---
    df_clean['task_type'] = df_clean['task_type'].fillna('general').astype(str)
    df_clean['complexity_class'] = df_clean['complexity_class'].fillna(3).astype(int)

    le_task = LabelEncoder()

    df_clean['task_type_enc'] = le_task.fit_transform(df_clean['task_type'])

    X = df_clean[['expert_estimated_effort', 'complexity_class', 'task_type_enc']]
    y = df_clean['actual_effort']

    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

    # --- OPTIMIZED MODEL ---
    model = RandomForestRegressor(
        n_estimators=300, 
        max_depth=12, 
        min_samples_leaf=4, 
        random_state=42,
        n_jobs=-1 
    )
    model.fit(X_train, y_train)

    # ---EVALUATION ---
    preds = model.predict(X_test)
    mae = mean_absolute_error(y_test, preds)
    rmse = np.sqrt(mean_squared_error(y_test, preds))
    r2 = r2_score(y_test, preds)
    
    print("=" * 40)
    print("📊 OPTIMIZED MODEL RESULTS")
    print("=" * 40)
    print(f"MAE      : {mae:.2f} seconds")
    print(f"RMSE     : {rmse:.2f} seconds")
    print(f"R² Score : {r2:.4f}")
    print("=" * 40)

    # Save models
    joblib.dump(model, MODELS_DIR / 'duration_model.pkl')
    joblib.dump(le_task, MODELS_DIR / 'encoder_task_type.pkl')
    print(f"Model and Encoders saved to {MODELS_DIR}\n")




# 3. GLOBAL OBJECT LOADING ------------------------------------------------------------------------------------------------
def load_model_objects():
    try:
        m = joblib.load(MODELS_DIR / 'duration_model.pkl')
        t = joblib.load(MODELS_DIR / 'encoder_task_type.pkl')
        return m, t
    except:
        return None, None




# 4. ROBUST INFERENCE ------------------------------------------------------------------------------------------------
def predict_duration_adhd(expert_est_sec, complexity_numeric, task_type_str, buffer=1.2):
    """
    Predict ADHD duration for a task.
    
    Args:
        expert_est_sec: Expert estimation in seconds
        complexity_numeric: Complexity on 1-5 scale (int)
        task_type_str: Task type string (coding, writing, reading, etc.)
        buffer: ADHD buffer multiplier (default 1.2)
    
    Returns:
        Estimated duration in minutes
    """
    model, le_task = load_model_objects()
    if model is None: return "Error: Model files not found."

    # Validate and encode task type
    t_str = str(task_type_str)
    if t_str not in le_task.classes_: t_str = le_task.classes_[0]
    t_enc = le_task.transform([t_str])[0]
    
    # Clamp complexity to 1-5 range
    complexity_numeric = max(1, min(5, int(complexity_numeric)))

    X_input = pd.DataFrame(
        [[expert_est_sec, complexity_numeric, t_enc]],
        columns=['expert_estimated_effort', 'complexity_class', 'task_type_enc']
    )
    
    pred_sec = model.predict(X_input)[0]
    return round((pred_sec / 60) * buffer, 1)






# 5. INTEGRATION WITH LLM DECOMPOSITION ------------------------------------------------------------------------------------------------
def estimate_tasks_from_llm(tasks_list: list, buffer=1.2) -> list:
    
    enriched_tasks = []
    
    for task in tasks_list:
        try:
            # Extract and validate task data
            task_name = task.get('task_name', 'Unknown')
            task_complexity = task.get('task_complexity', 3)
            task_type = task.get('task_type', 'general')
            general_estimation_hours = task.get('general_estimation', 1)
            
            # Convert hours to seconds for the model
            expert_est_sec = general_estimation_hours * 3600
            
            # Get duration estimate (complexity is numeric 1-5)
            duration_minutes = predict_duration_adhd(
                expert_est_sec, 
                task_complexity, 
                task_type, 
                buffer=buffer
            )
            
            # Enrich task with estimate
            enriched_task = task.copy()
            enriched_task['estimated_duration_minutes'] = duration_minutes
            enriched_tasks.append(enriched_task)
            
        except Exception as e:
            print(f"Error estimating duration for '{task.get('task_name', 'Unknown')}': {e}")
            task['estimated_duration_minutes'] = None
            enriched_tasks.append(task)
    
    return enriched_tasks


if __name__ == "__main__":
    train_evaluate_and_save()
    
    # Test
    print("SAMPLE PREDICTION")
    result = predict_duration_adhd(3600, 3, "coding")
    print(f"Suggested Duration: {result} minutes")