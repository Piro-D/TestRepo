"""
ADHD Academic Task Duration Estimator - High Accuracy Version
Features: IQR Outlier Removal, Dataset Cleaning, and Optimized Random Forest.
"""

import warnings
import sys
from pathlib import Path

if __package__ is None or __package__ == "":
    sys.path.append(str(Path(__file__).resolve().parents[1]))

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder

import config
from ml.preprocess import clean_duration_training_data

warnings.filterwarnings('ignore')

DATA_PATH = config.BASE_DIR / "Datasets" / "preprocessed_jira_data.csv"
MODELS_DIR = config.BASE_DIR / "models"
MODELS_DIR.mkdir(exist_ok=True)


def train_evaluate_and_save():
    if not DATA_PATH.exists():
        print(f"Error: Dataset not found at {DATA_PATH}")
        return

    for filename in ['duration_model.pkl', 'encoder_task_type.pkl']:
        model_file = MODELS_DIR / filename
        if model_file.exists():
            model_file.unlink()

    df_clean = clean_duration_training_data(DATA_PATH)

    le_task = LabelEncoder()
    df_clean['task_type_enc'] = le_task.fit_transform(df_clean['task_type'])

    x = df_clean[['expert_estimated_effort', 'complexity_class', 'task_type_enc']]
    y = df_clean['actual_effort']

    x_train, x_test, y_train, y_test = train_test_split(x, y, test_size=0.3, random_state=26)

    params = {
        "n_estimators": 600,
        "max_depth": 8,
        "min_samples_leaf": 8,
        "random_state": 26,
        "n_jobs": -1,
    }

    model = RandomForestRegressor(**params)
    model.fit(x_train, y_train)

    

    print(df_clean[['expert_estimated_effort', 'actual_effort']].corr())

    preds = model.predict(x_test)
    mae = mean_absolute_error(y_test, preds)
    rmse = np.sqrt(mean_squared_error(y_test, preds))
    r2 = r2_score(y_test, preds)

    print("=" * 40)
    print("OPTIMIZED MODEL RESULTS")
    print("=" * 40)
    print(f"MAE      : {mae:.2f} seconds")
    print(f"RMSE     : {rmse:.2f} seconds")
    print(f"R2 Score : {r2:.4f}")
    print("=" * 40)

    joblib.dump(model, MODELS_DIR / 'duration_model.pkl')
    joblib.dump(le_task, MODELS_DIR / 'encoder_task_type.pkl')
    print(f"Model and Encoders saved to {MODELS_DIR}\n")

    return {
        "model": model,
        "encoder": le_task,
        "params": params,
        "metrics": {
            "mae": mae,
            "rmse": rmse,
            "r2_score": r2,
        },
        "x_test": x_test,
    }


def load_model_objects():
    try:
        model = joblib.load(MODELS_DIR / 'duration_model.pkl')
        task_encoder = joblib.load(MODELS_DIR / 'encoder_task_type.pkl')
        return model, task_encoder
    except Exception:
        return None, None


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
    if model is None:
        return "Error: Model files not found."

    task_type = str(task_type_str)
    if task_type not in le_task.classes_:
        task_type = le_task.classes_[0]
    task_type_encoded = le_task.transform([task_type])[0]

    complexity_numeric = max(1, min(5, int(complexity_numeric)))

    x_input = pd.DataFrame(
        [[expert_est_sec, complexity_numeric, task_type_encoded]],
        columns=['expert_estimated_effort', 'complexity_class', 'task_type_enc']
    )

    pred_sec = model.predict(x_input)[0]
    return round((pred_sec / 60) * buffer, 1)


def estimate_tasks_from_llm(tasks_list: list, buffer=1.2) -> list:
    enriched_tasks = []

    for task in tasks_list:
        try:
            if not isinstance(task, dict):
                print(f"Skipping invalid task format (expected dict, got {type(task).__name__}): {task}")
                continue

            task_complexity = task.get('task_complexity', 3)
            task_type = task.get('task_type', 'general')
            general_estimation_minutes = task.get('general_estimation', 1)
            expert_est_sec = general_estimation_minutes * 60

            duration_minutes = predict_duration_adhd(
                expert_est_sec,
                task_complexity,
                task_type,
                buffer=buffer
            )

            enriched_task = task.copy()
            enriched_task['estimated_duration_minutes'] = duration_minutes
            enriched_tasks.append(enriched_task)
        except Exception as e:
            task_name = task.get('task_name', 'Unknown') if isinstance(task, dict) else str(task)
            print(f"Error estimating duration for '{task_name}': {e}")
            if isinstance(task, dict):
                task['estimated_duration_minutes'] = None
                enriched_tasks.append(task)

    return enriched_tasks


# ML Flow Assignment

def run_mlflow_pipeline():
    import mlflow
    import mlflow.sklearn

    mlflow.set_experiment("ADHD Task Duration Estimation")

    training_result = train_evaluate_and_save()
    if training_result is None:
        return

    with mlflow.start_run():
        mlflow.log_params(training_result["params"])
        mlflow.log_metrics(training_result["metrics"])

        model_info = mlflow.sklearn.log_model(
            training_result["model"],
            "duration_model",
            input_example=training_result["x_test"].head(5),
        )

        mlflow.log_artifact(str(MODELS_DIR / "duration_model.pkl"))
        mlflow.log_artifact(str(MODELS_DIR / "encoder_task_type.pkl"))
        mlflow.log_artifact(str(DATA_PATH))

        if config.CLEANED_DATASET_FILE.exists():
            mlflow.log_artifact(str(config.CLEANED_DATASET_FILE))

        mlflow.set_tag(
            "Training Info",
            "Random Forest model for ADHD task duration estimation",
        )

    return model_info


# Testing of the Machine Learning Component
if __name__ == "__main__":
    run_mlflow_pipeline()

    print("SAMPLE PREDICTION")
    result = predict_duration_adhd(7200, 5, "coding")
    print(f"Suggested Duration: {result} minutes")

