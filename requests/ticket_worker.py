
import json
import os
import sys
import time
import traceback
from pathlib import Path

from dotenv import load_dotenv
from google import genai
from google.genai import types, errors


# --------------------------------------------------
# ENVIRONMENT CONFIGURATION
# --------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parent.parent

load_dotenv(PROJECT_ROOT / ".env")

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Primary model and fallback model
GEMINI_MODELS = [
    "gemini-3.1-flash-lite",
    "gemini-2.5-flash-lite",
]


# --------------------------------------------------
# TICKET GENERATION
# --------------------------------------------------

def generate_ticket(issue):

    if not isinstance(issue, str) or not issue.strip():
        raise ValueError("Please describe your issue.")

    if not GEMINI_API_KEY:
        raise RuntimeError("GEMINI_API_KEY is not configured.")

    client = genai.Client(api_key=GEMINI_API_KEY)

    prompt = f"""
You are FlowPilot AI, an intelligent business ticket assistant.

Analyze the user's issue and generate a ticket.

Return ONLY a valid JSON object with these four fields:
- title: concise ticket title, maximum 200 characters
- category: a suitable category, maximum 50 characters
- priority: exactly one of Low, Medium, High
- description: clear description of the reported issue

Priority guidelines:
- High: urgent issues, major work disruption, security incidents
- Medium: significant issues affecting normal work
- Low: minor issues or general requests

Do not invent facts. Use only the information provided.
Do not include Markdown or text outside the JSON object.

User's issue:
{issue.strip()}
""".strip()

    response = None
    last_error = None

    # --------------------------------------------------
    # GEMINI API WITH RETRIES AND FALLBACK
    # --------------------------------------------------

    for model in GEMINI_MODELS:

        for attempt in range(2):

            try:
                print(
                    f"Trying Gemini model: {model}, attempt {attempt + 1}",
                    file=sys.stderr,
                )

                response = client.models.generate_content(
                    model=model,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json"
                    ),
                )

                if response and response.text:
                    break

                raise RuntimeError("Gemini returned an empty response.")

            except errors.ServerError as exc:
                last_error = exc

                if attempt == 0:
                    time.sleep(3)
                    continue

                break

            except errors.ClientError as exc:
                last_error = exc
                break

            except Exception as exc:
                last_error = exc
                break

        if response and response.text:
            break

    if not response or not response.text:
        raise RuntimeError(
            f"All Gemini model attempts failed: {last_error}"
        )

    # --------------------------------------------------
    # PARSE JSON RESPONSE
    # --------------------------------------------------

    try:
        ticket = json.loads(response.text.strip())
    except json.JSONDecodeError as exc:
        raise ValueError("Gemini returned invalid JSON.") from exc

    required_fields = {
        "title",
        "category",
        "priority",
        "description",
    }

    if not isinstance(ticket, dict):
        raise ValueError("AI returned an invalid ticket.")

    if not required_fields.issubset(ticket.keys()):
        raise ValueError("AI response is missing ticket fields.")

    # --------------------------------------------------
    # VALIDATE PRIORITY
    # --------------------------------------------------

    priority = ticket.get("priority")

    if not isinstance(priority, str):
        raise ValueError("AI returned an invalid priority.")

    priority = priority.strip().capitalize()

    if priority not in ("Low", "Medium", "High"):
        raise ValueError("AI returned an invalid priority.")

    ticket["priority"] = priority

    # --------------------------------------------------
    # VALIDATE TICKET FIELDS
    # --------------------------------------------------

    if not all(
        isinstance(ticket[field], str) and ticket[field].strip()
        for field in required_fields
    ):
        raise ValueError("AI returned empty or invalid ticket fields.")

    ticket["title"] = ticket["title"].strip()[:200]
    ticket["category"] = ticket["category"].strip()[:50]
    ticket["description"] = ticket["description"].strip()

    return ticket


# --------------------------------------------------
# COMMAND LINE EXECUTION
# --------------------------------------------------

if __name__ == "__main__":

    try:
        payload = json.loads(sys.stdin.read())

        issue = payload.get("issue", "")

        ticket = generate_ticket(issue)

        print(json.dumps(ticket, ensure_ascii=False))

    except Exception as exc:

        print(
            f"Ticket worker failed: {exc}\n{traceback.format_exc()}",
            file=sys.stderr,
        )

        sys.exit(1)
