import ollama
import os
import subprocess
from docx import Document
from PyPDF2 import PdfReader
import json


#Set up model directory for Ollama LLM model
BASE_DIR = os.path.dirname(__file__)
MODEL_DIR = os.path.join(BASE_DIR, "models")

os.makedirs(MODEL_DIR, exist_ok=True)
os.environ["OLLAMA_MODELS"] = MODEL_DIR


# Extraction of text from docx or pdf files
def extract_text(file_path: str) -> str:
    ext = os.path.splitext(file_path)[1].lower()

    if ext == ".docx":
        doc = Document(file_path)
        return "\n".join(p.text for p in doc.paragraphs)

    elif ext == ".pdf":
        reader = PdfReader(file_path)
        return "\n".join(page.extract_text() or "" for page in reader.pages)

    else:
        raise ValueError("Only .pdf and .docx files are supported")



# Ensure target LLM model is downloaded
def ensure_model(model_name: str):
    try:
        # Check installed models
        result = subprocess.run(
            ["ollama", "list"],
            capture_output=True,
            text=True
        )

        if model_name not in result.stdout:
            print(f"Downloading model: {model_name}...")
            subprocess.run(["ollama", "pull", model_name], check=True)
            print("Download complete.")

    except Exception as e:
        raise RuntimeError(f"Failed to ensure model: {e}")




# Function to call LLM for task decomposition
def generate_tasks(document_text: str, model: str = "llama3.1:8b") -> list:
    ensure_model(model)
    
    system_prompt = (
        "You are an academic academic task decomposition assistant in charge of breaking down projects into smaller tasks."
        "You will receive a project description, and you must break the project down into subtasks and output ONLY a valid JSON list of those tasks. "
        "The JSON must contain the following information related to each task:"
        "'task_name' : A descriptive & informative name for the task, "
        "'task_complexity' : A scale from 1 - 5 related to the difficulty of the task, "
        "'task_type' : A category of the task, where the category must be one of these (coding, writing, reading, problem solving, review, research, general), "
        "and 'general_estimation' : An estimation of how long the task will take in hours for an undergraduate student."
        "Note: The output must be a valid JSON list of tasks, and nothing else. Do not include any explanations or text outside the JSON. Do not hallucinate any information"
        "Note: Focus only on tasks that are necessary for the completion of the project. "
    )

    response = ollama.chat(
        model=model,
        messages=[
            {'role': 'system', 'content': system_prompt},
            {'role': 'user', 'content': f"Document content:\n{document_text}"}
        ],
        format='json'
    )

    try:
        return json.loads(response['message']['content'])
    except Exception:
        raise ValueError("Model did not return valid JSON")


# Main Project Decomposition Function (Call this function to run the entire decomposition process)
def process_document(file_path: str) -> dict:
    try:
        # Check file exists
        if not os.path.exists(file_path):
            return {"status": "error", "message": "File not found"}

        # Extract text
        document_text = extract_text(file_path)

        if not document_text.strip():
            return {"status": "error", "message": "No readable text found"}

        # Generate tasks
        tasks = generate_tasks(document_text)

        return {
            "status": "success",
            "tasks": tasks
        }

    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }


#testing
if __name__ == "__main__":
    file_path = r".\TestDocuments\document.pdf"

    result = process_document(file_path)

    print(json.dumps(result, indent=4))












































