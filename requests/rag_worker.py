import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Remove the project root so Python won't mistake the Django
# app named "requests" for the third-party requests library.
sys.path = [
    path
    for path in sys.path
    if Path(path or ".").resolve() != PROJECT_ROOT
]

import json
import sys
import traceback
import urllib.request
from functools import lru_cache
from pathlib import Path

import numpy as np
import pymupdf
from fastembed import TextEmbedding


PROJECT_ROOT = Path(__file__).resolve().parent.parent
PDF_PATH = PROJECT_ROOT / "company_policy.pdf"

EMBEDDING_MODEL = "BAAI/bge-small-en-v1.5"
OLLAMA_URL = "http://localhost:11434/api/generate"
OLLAMA_MODEL = "qwen2.5:3b"

SIMILARITY_THRESHOLD = 0.60
FALLBACK_ANSWER = (
    "I could not find the answer in the provided document."
)


def extract_pdf_text():
    if not PDF_PATH.exists():
        raise FileNotFoundError(f"PDF not found: {PDF_PATH}")

    documents = []

    with pymupdf.open(PDF_PATH) as pdf:
        for page_number, page in enumerate(pdf, start=1):
            for chunk in page.get_text("text").split("."):
                chunk = chunk.strip()
                if chunk:
                    documents.append({
                        "text": chunk,
                        "page": page_number,
                    })

    if not documents:
        raise ValueError("The PDF contains no readable text.")

    return documents


@lru_cache(maxsize=1)
def load_index():
    model = TextEmbedding(model_name=EMBEDDING_MODEL)
    documents = extract_pdf_text()

    vectors = np.asarray(
        list(model.embed([doc["text"] for doc in documents])),
        dtype=np.float32,
    )

    return model, documents, vectors


def cosine_similarity(a, b):
    denominator = np.linalg.norm(a) * np.linalg.norm(b)
    if denominator == 0:
        return 0.0
    return float(np.dot(a, b) / denominator)


def generate_answer(question, context):
    prompt = f"""
You are FlowPilot AI, a company-policy assistant.
Use ONLY the document context. Never invent facts.
If the context does not answer the question, respond exactly:
{FALLBACK_ANSWER}

Document context:
{context}

Question: {question}

Answer:
""".strip()

    payload = json.dumps({
        "model": OLLAMA_MODEL,
        "prompt": prompt,
        "stream": False,
    }).encode("utf-8")

    request = urllib.request.Request(
        OLLAMA_URL,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    with urllib.request.urlopen(request, timeout=180) as response:
        result = json.loads(response.read().decode("utf-8"))

    answer = result.get("response", "").strip()
    if not answer:
        raise RuntimeError("Ollama returned an empty answer.")

    return answer


def answer_question(question):
    model, documents, vectors = load_index()

    query_vector = np.asarray(
        list(model.embed([question]))[0],
        dtype=np.float32,
    )

    scores = [
        cosine_similarity(query_vector, vector)
        for vector in vectors
    ]

    best_index = int(np.argmax(scores))
    score = scores[best_index]
    document = documents[best_index]

    if score < SIMILARITY_THRESHOLD:
        return {
            "answer": FALLBACK_ANSWER,
            "source": None,
            "page": None,
            "similarity_score": round(score, 4),
            "retrieved_context": None,
        }

    context = (
        f"[Source: company_policy.pdf, Page {document['page']}]\n"
        f"{document['text']}"
    )

    return {
        "answer": generate_answer(question, context),
        "source": "company_policy.pdf",
        "page": document["page"],
        "similarity_score": round(score, 4),
        "retrieved_context": document["text"],
    }


if __name__ == "__main__":
    try:
        payload = json.loads(sys.stdin.read())
        question = payload.get("question", "")

        if not isinstance(question, str) or not question.strip():
            raise ValueError("Question cannot be empty.")

        result = answer_question(question.strip())
        print(json.dumps(result, ensure_ascii=False))

    except Exception as exc:
        print(
            f"RAG worker failed: {exc}\n{traceback.format_exc()}",
            file=sys.stderr,
        )
        sys.exit(1)
