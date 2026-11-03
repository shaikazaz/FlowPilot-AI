
import json
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
WORKER_PATH = PROJECT_ROOT / "requests" / "ticket_worker.py"


def generate_ticket_details(issue):
    if not isinstance(issue, str) or not issue.strip():
        raise ValueError("Please describe your issue.")

    result = subprocess.run(
        [sys.executable, str(WORKER_PATH)],
        input=json.dumps({"issue": issue.strip()}),
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=240,
        cwd=str(PROJECT_ROOT),
    )

    if result.returncode != 0:
        print("Ticket worker error:", result.stderr)
        raise RuntimeError("The AI ticket generator failed.")

    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        print("Unexpected ticket worker output:", result.stdout)
        raise RuntimeError(
            "The ticket worker returned invalid JSON."
        ) from exc
