
import pandas as pd
import numpy as np

def preprocess_jira_data(file_path):
    # 1. Load the dataset (Assuming CSV, but works for SQLite conversion too)
    df = pd.read_csv(file_path)

    # 2. Filter out the 'Noise'
    # Remove rows where time spent is 0 or unrealistically high (e.g., > 100 hours)
    df = df[(df['actual_effort'] > 0) & (df['actual_effort'] < 360000)].copy()

    # 3. Handle 'Obscure' Text Labels
    # Convert descriptions to lowercase and remove special characters
    df['clean_text'] = df['corpus'].str.replace(r'[^a-zA-Z\s]', '', regex=True).str.lower()

    # 4. Create the "Complexity Buckets" (The Target for ML)
    # Define thresholds in seconds: 30m, 1h, 3h, 6h
    bins = [0, 1800, 3600, 10800, 21600, np.inf]
    labels = [1, 2, 3, 4, 5]
    
    df['complexity_class'] = pd.cut(df['actual_effort'], bins=bins, labels=labels)

    # 5. Extract Text Features (Basic NLP for the ML model)
    df['word_count'] = df['clean_text'].apply(lambda x: len(str(x).split()))
    
    return df[['clean_text', 'word_count', 'expert_estimated_effort','actual_effort','complexity_class']]


def categorize_task(text):
    text = str(text).lower()
    
    # Define keyword maps
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
    return 'general' # Fallback category

# Example usage:
processed_df = preprocess_jira_data('.\\Datasets\\JOSSE_DATA.csv')
print(processed_df.head())  

processed_df.info()
# Apply to your dataframe
processed_df['task_type'] = processed_df['clean_text'].apply(categorize_task)
processed_df.drop(columns=['clean_text'], inplace=True) 

processed_df.to_csv('.\\Datasets\\preprocessed_jira_data.csv', index=False)