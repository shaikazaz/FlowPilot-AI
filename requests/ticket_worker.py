
import json
import sys
import traceback
import urllib.request

OLLAMA_URL = "http://localhost:11434/api/generate"
OLLAMA_MODEL = "qwen2.5:3b"


def generate_ticket(issue):
    if not isinstance(issue, str) or not issue.strip():
        raise ValueError("Please describe your issue.")

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

    payload = json.dumps({
        "model": OLLAMA_MODEL,
        "prompt": prompt,
        "stream": False,
        "format": "json",
    }).encode("utf-8")

    request = urllib.request.Request(
        OLLAMA_URL,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    with urllib.request.urlopen(request, timeout=180) as response:
        result = json.loads(response.read().decode("utf-8"))

    model_response = result.get("response", "").strip()

    if not model_response:
        raise RuntimeError("Ollama returned an empty response.")

    ticket = json.loads(model_response)

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

    priority = ticket.get("priority")

    if not isinstance(priority, str):
       raise ValueError("AI returned an invalid priority.")

    priority = priority.strip().capitalize()
  
    if priority not in ("Low", "Medium", "High"):
       raise ValueError("AI returned an invalid priority.")
 
    ticket["priority"] = priority

    if not all(
        isinstance(ticket[field], str) and ticket[field].strip()
        for field in required_fields
    ):
        raise ValueError("AI returned empty or invalid ticket fields.")

    ticket["title"] = ticket["title"].strip()[:200]
    ticket["category"] = ticket["category"].strip()[:50]
    ticket["description"] = ticket["description"].strip()

    return ticket


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
