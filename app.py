from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from dotenv import load_dotenv
import os
from langchain_groq import ChatGroq
from utils import Utils


app = Flask(__name__)
CORS(app)
utils = Utils()
print("+++++++++++++++++++++++++++++++++")
@app.route("/ask", methods=["POST"])
def ask():
    print("Received request:", request.data)
    payload = request.get_json()
    user_query = payload.get("query", "").strip()
    if not user_query:
        return jsonify({"error": "Query is required"}), 400
    print("------------------------------------")
    context = utils.context_builder(user_query)
    if context is None:
        context = [{"source_id": 0, "content": "No relevant context found.", "metadata": {}, "score": 0.0}]

    print("Context:", context)
    answer = utils.generate_answer(user_query, context)

    print("Answer:", answer)

    sources = []

    for item in context:
        metadata = item.get("metadata", {})

        sources.append({
            "source_id": item.get("source_id"),
            "source": metadata.get("source"),
            "page": metadata.get("page")
        })

    return jsonify({
        "answer": answer.content,
        "sources": sources
    }), 200

from flask import request, jsonify

@app.route("/contradict", methods=["POST"])
def contradict():
    try:
        payload = request.get_json(force=True)

        if payload is None:
            return jsonify({"error": "Request body is required."}), 400

        contents = payload.get("contents")

        if not isinstance(contents, list):
            return jsonify({"error": "'contents' must be a list."}), 400

        if len(contents) != 2:
            return jsonify({"error": "'contents' must contain exactly two strings."}), 400

        question = str(contents[0]).strip()
        answer = str(contents[1]).strip()

        prompt = f"""
You are an expert document QA evaluator.

You are given:

1. A user's question.
2. An answer generated from retrieved documents.

Your job is to determine whether the answer contradicts the question or contains any internally contradictory statements.

Rules:
- Compare the factual meaning, not wording.
- Ignore formatting such as answer1, source1, answer2, etc.
- If the answer correctly answers the question and contains no conflicting facts, contradiction should be false.
- If the answer contains conflicting statements or contradicts the intent of the question, contradiction should be true.
- Return ONLY valid JSON.
- Do not include markdown or explanations outside the JSON.

Return this exact JSON format:

{{
    "contradiction": true,
    "reason": "...",
    "conflicting_topics": [
        "Topic 1",
        "Topic 2"
    ]
}}

Question:
{question}

Answer:
{answer}
"""

        response = utils.llm.invoke(prompt)

        return jsonify({
            "result": response.content
        }), 200

    except Exception as e:
        return jsonify({
            "error": str(e)
        }), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)