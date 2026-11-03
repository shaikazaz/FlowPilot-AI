
import json
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
WORKER_PATH = PROJECT_ROOT / "requests" / "rag_worker.py"


def answer_policy_question(question):
    if not isinstance(question, str) or not question.strip():
        raise ValueError("Please provide a non-empty question.")

    result = subprocess.run(
        [
            sys.executable,
            str(WORKER_PATH),
        ],
        input=json.dumps({"question": question.strip()}),
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=240,
        cwd=str(PROJECT_ROOT),
    )

    if result.returncode != 0:
        # Keep the detailed error in the Django server terminal.
        print("RAG worker error:", result.stderr)
        raise RuntimeError("The RAG worker failed.")

    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        print("Unexpected RAG worker output:", result.stdout)
        raise RuntimeError(
            "The RAG worker returned invalid JSON."
        ) from exc
