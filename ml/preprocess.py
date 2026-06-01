import sys
from pathlib import Path

if __package__ is None or __package__ == "":
    sys.path.append(str(Path(__file__).resolve().parents[1]))

import numpy as np
import pandas as pd

import config


def categorize_task(text):
    text = str(text).lower()

    categories = {
        'coding': ['code', 'implement', 'debug', 'function', 'api', 'refactor', 'develop'],
        'writing': ['write', 'essay', 'report', 'draft', 'documentation', 'content'],
        'reading': ['read', 'chapter', 'article', 'paper', 'literature'],
        'problem solving': ['solve', 'exercise', 'math', 'logic', 'calculate', 'algorithm'],
        'review': ['review', 'check', 'proofread', 'audit', 'inspect', 'verify'],
        'research': ['research', 'find', 'explore', 'investigate', 'search', 'study']
    }

    for category, keywords in categories.items():
        if any(word in text for word in keywords):
            return category
    return 'general'





def preprocess_jira_data(file_path):
    df = pd.read_csv(file_path)

    df = df[(df['actual_effort'] > 0) & (df['actual_effort'] < 360000)].copy()

    df['clean_text'] = df['corpus'].str.replace(r'[^a-zA-Z\s]', '', regex=True).str.lower()
    df['task_type'] = df['clean_text'].apply(categorize_task)

    bins = [0, 900, 3600, 10800, 18000, np.inf]
    labels = [1, 2, 3, 4, 5]
    df['complexity_class'] = pd.cut(df['expert_estimated_effort'], bins=bins, labels=labels)

    df['word_count'] = df['clean_text'].apply(lambda x: len(str(x).split()))

    return df[['clean_text', 'word_count', 'expert_estimated_effort', 'actual_effort', 'complexity_class', 'task_type']]





def clean_duration_training_data(file_path):
    df = pd.read_csv(file_path)
    df = df[(df['expert_estimated_effort'] > 0) & (df['actual_effort'] > 0)].copy()

    df["effort_ratio"] = df["actual_effort"] / df["expert_estimated_effort"]
    ratio_limits = {
        "coding": 4,
        "problem solving": 3,
        "research": 3,
    }
    default_ratio = 2

    df["allowed_ratio"] = df["task_type"].map(ratio_limits).fillna(default_ratio)
    df["lower_ratio"] = 1 / df["allowed_ratio"]
    df["upper_ratio"] = df["allowed_ratio"]
    df = df[
        (df["effort_ratio"] >= df["lower_ratio"]) &
        (df["effort_ratio"] <= df["upper_ratio"])
    ].copy()

    q1 = df['actual_effort'].quantile(0.25)
    q3 = df['actual_effort'].quantile(0.75)
    iqr = q3 - q1

    lower_bound = q1 - 1.5 * iqr
    upper_bound = q3 + 1.5 * iqr
    df_clean = df[(df['actual_effort'] >= lower_bound) & (df['actual_effort'] <= upper_bound)].copy()

    removed_count = len(df) - len(df_clean)
    print(f"Outlier Removal: Deleted {removed_count} noisy rows.")
    print(f"Final Dataset Size: {len(df_clean)} rows.")

    df_clean['task_type'] = df_clean['task_type'].fillna('general').astype(str)
    df_clean['complexity_class'] = df_clean['complexity_class'].fillna(3).astype(int)
    df_clean.to_csv(config.CLEANED_DATASET_FILE, index=False)

    return df_clean





def build_preprocessed_jira_dataset(
    source_path=config.BASE_DIR / "Datasets" / "JOSSE_DATA.csv",
    output_path=config.BASE_DIR / "Datasets" / "preprocessed_jira_data.csv",
):
    processed_df = preprocess_jira_data(source_path)
    processed_df['task_type'] = processed_df['clean_text'].apply(categorize_task)
    processed_df.drop(columns=['clean_text'], inplace=True)
    processed_df.to_csv(output_path, index=False)
    return processed_df





if __name__ == "__main__":
    processed_df = build_preprocessed_jira_dataset()
    print(processed_df.head())
    processed_df.info()
