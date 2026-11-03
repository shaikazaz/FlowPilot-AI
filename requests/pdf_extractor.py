
import sys
from pathlib import Path
import json
import urllib.request

# Avoid conflict with your Django app named "requests"
if "" in sys.path:
    sys.path.remove("")

import pymupdf
import numpy as np
from fastembed import TextEmbedding


# 1. PDF file location
PDF_PATH = Path("company_policy.pdf")

# 2. Initial similarity threshold (to be evaluated)
SIMILARITY_THRESHOLD = 0.60


# 3. Extract PDF text and split it into chunks
def extract_pdf_text(pdf_path):
    documents = []

    with pymupdf.open(pdf_path) as pdf:
        for page_number, page in enumerate(pdf, start=1):
            text = page.get_text().strip()

            if not text:
                continue

            print(f"\nPage {page_number}")
            print(text)

            chunks = [
                chunk.strip()
                for chunk in text.split(".")
                if chunk.strip()
            ]

            for chunk in chunks:
                documents.append({
                    "text": chunk,
                    "page": page_number
                })

    return documents


# 4. Create embeddings for document chunks
def create_embeddings(model, documents):
    texts = [document["text"] for document in documents]

    if not texts:
        return np.array([])

    return np.array(list(model.embed(texts)))


# 5. Calculate cosine similarity
def cosine_similarity(vector_a, vector_b):
    denominator = (
        np.linalg.norm(vector_a) * np.linalg.norm(vector_b)
    )

    if denominator == 0:
        return 0.0

    return float(
        np.dot(vector_a, vector_b) / denominator
    )


# 6. Retrieve the most relevant chunks
def search_documents(
    question, model, documents, document_vectors, top_k=2
):
    question_vector = np.array(
        list(model.embed([question]))[0]
    )

    results = []

    for document, vector in zip(documents, document_vectors):
        score = cosine_similarity(question_vector, vector)

        results.append({
            "text": document["text"],
            "page": document["page"],
            "score": score
        })

    results.sort(
        key=lambda result: result["score"],
        reverse=True
    )

    return results[:top_k]


# 7. Generate an answer using Qwen through Ollama
def generate_answer(question, context):
    prompt = f"""
You are a helpful assistant answering questions about a company policy.

Use only the context provided below.
Do not make up facts.
If the context does not contain the answer, say:
"I could not find the answer in the provided document."

Context:
{context}

Question:
{question}

Answer:
"""

    data = {
        "model": "qwen2.5:3b",
        "prompt": prompt,
        "stream": False
    }

    request_data = json.dumps(data).encode("utf-8")

    request = urllib.request.Request(
        "http://localhost:11434/api/generate",
        data=request_data,
        headers={"Content-Type": "application/json"}
    )

    with urllib.request.urlopen(
        request, timeout=180
    ) as response:
        result = json.loads(
            response.read().decode("utf-8")
        )

    return result["response"].strip()


# 8. Main RAG pipeline
def main():
    if not PDF_PATH.exists():
        print(f"PDF not found: {PDF_PATH.resolve()}")
        return

    print("Loading embedding model...")
    model = TextEmbedding(
        model_name="BAAI/bge-small-en-v1.5"
    )

    print("\nExtracting PDF text...")
    documents = extract_pdf_text(PDF_PATH)

    if not documents:
        print("No extractable text found in the PDF.")
        return

    print("\nCreating document embeddings...")
    document_vectors = create_embeddings(model, documents)

    print(f"Created {len(document_vectors)} embeddings.")
    print(f"Vector dimensions: {len(document_vectors[0])}")

    # 9. Interactive question-answering loop
    while True:
        question = input(
            "\nAsk a question about the PDF (type 'exit' to stop): "
        ).strip()

        if question.lower() == "exit":
            print("Exiting FlowPilot AI. Goodbye!")
            break

        if not question:
            print("Please enter a question.")
            continue

        print(f"\nQuestion: {question}")
        print("\nSearching for relevant chunks...")

        results = search_documents(
            question=question,
            model=model,
            documents=documents,
            document_vectors=document_vectors,
            top_k=1
        )

        if not results:
            print("\nFinal Answer:")
            print("I could not find the answer in the provided document.")
            continue

        # Display the best similarity score
        best_score = results[0]["score"]

        print(f"Best similarity score: {best_score:.4f}")
        print(f"Required threshold: {SIMILARITY_THRESHOLD:.2f}")

        if best_score >= SIMILARITY_THRESHOLD:
            print("Retrieval decision: ACCEPT")
        else:
           print("Retrieval decision: REJECT")

        # 10. Reject weak retrieval matches
        if best_score < SIMILARITY_THRESHOLD:
            print("\nFinal Answer:")
            print("I could not find the answer in the provided document.")
            continue

        # Combine retrieved chunks into context
        context = "\n".join(
        f"[Source: {PDF_PATH.name}, Page {result['page']}]\n"
        f"{result['text']}"
        for result in results
        )

        # Ask Qwen to generate an answer
        print("\nGenerating answer with Qwen...")

        try:
            answer = generate_answer(question, context)

            print("\nFinal Answer:")
            print(answer)
            print("\nSources:")

            unique_sources = set()

            for result in results:
               source = (PDF_PATH.name, result["page"])

            if source not in unique_sources:
              unique_sources.add(source)
            print(f"- {source[0]}, Page {source[1]}")

        except Exception as error:
           print("\nCould not generate an answer.")

           print(
            "Check that Ollama is running and "
           "the qwen2.5:3b model is available."
            )

           print(f"Technical details: {error}")
           continue
   
        # Display retrieved sources
        print("\nRetrieved Evidence:")

    for rank, result in enumerate(results, start=1):
       print(f"\nEvidence {rank}")
       print(f"Source: {PDF_PATH.name}, Page {result['page']}")
       print(f"Similarity: {result['score']:.4f}")
       print(f"Content: {result['text']}")

if __name__ == "__main__":
    main()
