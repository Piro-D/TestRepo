import contextlib
import json
import os
import sys
import time
from io import StringIO
from pathlib import Path

# Ensure the parent directory is in the path for modular imports
if __package__ is None or __package__ == "":
    sys.path.append(str(Path(__file__).resolve().parents[1]))

from PyPDF2 import PdfReader
from docx import Document
from groq import Groq

import config

# Configuration
MAX_DOCUMENT_CHARS = 15000  # Groq handles much larger contexts than local models
DEFAULT_MODEL = "qwen/qwen3-32b"  # Native Groq Qwen model, replicating your local architecture


def extract_text(file_path: str) -> str:
    """Extract text from docx or pdf files."""
    ext = os.path.splitext(file_path)[1].lower()

    if ext == ".docx":
        doc = Document(file_path)
        return " ".join(p.text for p in doc.paragraphs)

    if ext == ".pdf":
        reader = PdfReader(file_path)
        return " ".join(page.extract_text() or "" for page in reader.pages)

    raise ValueError("Only .pdf and .docx files are supported")


def extract_json_payload(text: str):
    """Safely parse JSON from the model response string with fallback logic."""
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

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

    raise json.JSONDecodeError(f'No valid JSON payload found. Raw output:\n{text}', text, 0)


def generate_tasks(document_text: str, model: str = DEFAULT_MODEL) -> tuple:
    """
    Generate tasks from document text using the Groq Cloud API.
    """
    if not hasattr(config, 'GROQ_API_KEY') or not config.GROQ_API_KEY:
        raise ValueError("GROQ_API_KEY is missing. Check your .env and config.py files.")

    client = Groq(api_key=config.GROQ_API_KEY)

    system_prompt = (
        "You are an academic project manager specializing in high-level task summarization.\n"
        "You will receive a project description. You must extract the major milestones dynamically based on the project's scope.\n\n"
        "CRITICAL RULES:\n"
        "1. DYNAMIC SCALING: Adapt the number of milestones to the project size (e.g., 2-4 tasks for a weekly assignment, 5-8 for a mid-term project, and up to 12 for a massive semester thesis). Do not artificially inflate or restrict the count.\n"
        "2. DO NOT BE GRANULAR: Aggressively group minor deliverables (like administrative forms, citations, or submission formatting) into major phases. Every milestone must be a substantial chunk of work. Never micro-manage the steps.\n"
        "3. EFFORT ANCHORING: Assume this is an undergraduate university assignment. Keep complexity scores realistic (mostly 2s, 3s, and 4s) so the time estimation reflects a normal student workload, not a multi-month enterprise software lifecycle.\n"
        "4. Output ONLY a valid JSON object. Do not hallucinate any information outside the source text.\n\n"
        "The JSON MUST be an object with a single key called \"tasks\", containing a list of task objects.\n"
        "Each task object must contain EXACTLY these four keys:\n"
        "1. 'task_name' : A short, descriptive name for the milestone\n"
        "2. 'task_complexity' : A scale from 1 - 5\n"
        "3. 'task_type' : Exactly one of (coding, writing, reading, problem solving, review, research, general)\n"
        "4. 'general_estimation' : Estimated minutes for a college student\n\n"
        "The output must exactly follow this structural template:\n"
        "{\n"
        "  \"tasks\": [\n"
        "    {\n"
        "      \"task_name\": \"Research and Problem Selection\",\n"
        "      \"task_complexity\": 3,\n"
        "      \"task_type\": \"research\",\n"
        "      \"general_estimation\": 60\n"
        "    }\n"
        "  ]\n"
        "}"
    )

    if len(document_text) > MAX_DOCUMENT_CHARS:
        document_text = document_text[:MAX_DOCUMENT_CHARS].rsplit(' ', 1)[0]
        document_text += " [TRUNCATED DOCUMENT]"

    start_time = time.perf_counter()
    print(f"\n🧠 [Groq API] Sending payload to {model}...", flush=True)

    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {'role': 'system', 'content': system_prompt},
                {'role': 'user', 'content': f"Document:\n{document_text}"}
            ],
            response_format={"type": "json_object"},  # Forces strict JSON object structure
            temperature=0.1
        )

        elapsed = time.perf_counter() - start_time
        raw_text = response.choices[0].message.content
        parsed = extract_json_payload(raw_text)

        if isinstance(parsed, dict) and 'tasks' in parsed:
            return parsed['tasks'], elapsed
        return parsed, elapsed

    except Exception as e:
        elapsed = time.perf_counter() - start_time
        print("\n" + "=" * 60)
        print(f"ERROR: Groq API Error after {elapsed:.3f}s")
        print("=" * 60)
        print(str(e))
        raise ValueError(f"Model error after {elapsed:.3f}s: {e}")


def process_document(file_path: str) -> dict:
    """Main Project Decomposition Function"""
    try:
        if not os.path.exists(file_path):
            return {"status": "error", "message": "File not found"}

        document_text = extract_text(file_path)
        if not document_text.strip():
            return {"status": "error", "message": "No readable text found"}

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


# Testing of the LLM Decomposition component
if __name__ == "__main__":
    try:
        # Assumes document3.docx exists in your TestDocuments folder
        file_path = config.BASE_DIR / "TestDocuments" / "document3.docx"
        result = process_document(str(file_path))
        print(json.dumps(result, indent=4))
    except Exception as e:
        result = {"status": "error", "message": str(e)}
        print(json.dumps(result, indent=4))