
import json
import os
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
WORKER_PATH = PROJECT_ROOT / "requests" / "ticket_worker.py"


def generate_ticket_details(issue):
    if not isinstance(issue, str) or not issue.strip():
        raise ValueError("Please describe your issue.")

    if not os.getenv("GEMINI_API_KEY"):
        raise RuntimeError(
            "GEMINI_API_KEY is missing from the Django environment."
        )

    if not WORKER_PATH.exists():
        raise FileNotFoundError(
            f"Ticket worker not found: {WORKER_PATH}"
        )

    worker_env = os.environ.copy()

    result = subprocess.run(
        [sys.executable, str(WORKER_PATH)],
        input=json.dumps({"issue": issue.strip()}),
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=120,
        cwd=str(PROJECT_ROOT),
        env=worker_env,
    )

    if result.returncode != 0:
        print("Ticket worker error:", result.stderr)
        raise RuntimeError("Gemini ticket generation failed.")

    try:
        ticket = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        print("Unexpected ticket worker output:", result.stdout)
        raise RuntimeError(
            "The ticket worker returned invalid JSON."
        ) from exc

    if not isinstance(ticket, dict):
        raise RuntimeError("The AI returned an invalid ticket.")

    return ticket
