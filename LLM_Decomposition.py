import ollama
import os
import subprocess
from docx import Document
from PyPDF2 import PdfReader
import json
import time
import sys
import contextlib
from io import StringIO


#Set up model directory for Ollama LLM model
BASE_DIR = os.path.dirname(__file__)
MODEL_DIR = os.path.join(BASE_DIR, "models")
MAX_DOCUMENT_CHARS = 4000
DEFAULT_MODEL = "phi3:mini"
DEFAULT_NUM_PREDICT = 500

os.makedirs(MODEL_DIR, exist_ok=True)
os.environ["OLLAMA_MODELS"] = MODEL_DIR


# Extraction of text from docx or pdf files
def extract_text(file_path: str) -> str:
    ext = os.path.splitext(file_path)[1].lower()

    if ext == ".docx":
        doc = Document(file_path)
        return " ".join(p.text for p in doc.paragraphs)

    elif ext == ".pdf":
        reader = PdfReader(file_path)
        return " ".join(page.extract_text() or "" for page in reader.pages)

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
            with contextlib.redirect_stdout(StringIO()), contextlib.redirect_stderr(StringIO()):
                subprocess.run(["ollama", "pull", model_name], check=True)

    except Exception as e:
        raise RuntimeError(f"Failed to ensure model: {e}")




def extract_json_payload(text: str):
    """Try to parse JSON from a raw model response string."""
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Handle nested output from Ollama when the response is wrapped in a message object.
    import re

    matcher = re.search(r"content=(?P<quote>['\"])(?P<body>.*?)(?P=quote)", text, flags=re.DOTALL)
    if matcher:
        body = matcher.group('body')
        try:
            unescaped = bytes(body, 'utf-8').decode('unicode_escape')
        except Exception:
            unescaped = body
        try:
            return json.loads(unescaped)
        except json.JSONDecodeError:
            # Fall through and try plain substring extraction below.
            text = unescaped

    for start_char in ['[', '{']:
        start = text.find(start_char)
        if start == -1:
            continue

        stack = []
        for idx in range(start, len(text)):
            ch = text[idx]
            if ch in '{[':
                stack.append(ch)
            elif ch == '}' and stack and stack[-1] == '{':
                stack.pop()
            elif ch == ']' and stack and stack[-1] == '[':
                stack.pop()

            if not stack:
                candidate = text[start:idx + 1]
                try:
                    return json.loads(candidate)
                except json.JSONDecodeError:
                    break

    raise json.JSONDecodeError('No valid JSON payload found', text, 0)


# Function to call LLM for task decomposition
def generate_tasks(document_text: str, model: str = DEFAULT_MODEL) -> tuple:
    """
    Generate tasks from document text using a faster model.
    Use phi2 (2.7B params) by default for speed.
    """
    # Shortened, more direct prompt to reduce inference time
    system_prompt = (
        "You are a task decomposition assistant. Break down the project into subtasks."
        "Output ONLY a valid JSON list. Each task must have: "
        "'task_name', 'task_complexity' (1-5), 'task_type' (coding/writing/reading/problem solving/review/research/general), "
        "'general_estimation' (hours). No explanations, no extra text."
    )

    if len(document_text) > MAX_DOCUMENT_CHARS:
        document_text = document_text[:MAX_DOCUMENT_CHARS].rsplit(' ', 1)[0]
        document_text += " [TRUNCATED DOCUMENT - use a smaller document for faster output]"

    start_time = time.perf_counter()
    try:
        with contextlib.redirect_stdout(StringIO()), contextlib.redirect_stderr(StringIO()):
            response = ollama.chat(
                model=model,
                messages=[
                    {'role': 'system', 'content': system_prompt},
                    {'role': 'user', 'content': f"Document:\n{document_text}"}
                ],
                format='json',
                options={
                    'temperature': 0.1,  # Lower = faster, more consistent
                    'num_predict': DEFAULT_NUM_PREDICT,  # Reduce generation overhead
                }
            )
        
        elapsed = time.perf_counter() - start_time
        raw_text = response['message']['content'] if isinstance(response, dict) and 'message' in response else str(response)
        parsed = extract_json_payload(raw_text)
        if isinstance(parsed, dict) and 'tasks' in parsed:
            return parsed['tasks'], elapsed
        return parsed, elapsed
    except Exception as e:
        elapsed = time.perf_counter() - start_time
        raw_text = response['message']['content'] if 'response' in locals() and isinstance(response, dict) else str(response) if 'response' in locals() else ''
        raise ValueError(
            f"Model output was not valid JSON after {elapsed:.3f}s"
        )


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

        # Generate tasks and measure response time
        tasks, response_time = generate_tasks(document_text)

        return {
            "status": "success",
            "tasks": tasks,
            "response_time_seconds": round(response_time, 3)
        }

    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }


#testing
if __name__ == "__main__":
    try:
        # Ensure model is downloaded once at startup
        ensure_model(DEFAULT_MODEL)
        
        file_path = r".\TestDocuments\document.pdf"
        result = process_document(file_path)
        print(json.dumps(result, indent=4))
    except Exception as e:
        result = {
            "status": "error",
            "message": str(e)
        }
        print(json.dumps(result, indent=4))














































