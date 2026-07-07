from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from dotenv import load_dotenv
import os
from langchain_groq import ChatGroq
from utils import Utils


app = Flask(__name__)
CORS(app)
utils = Utils()

@app.route("/ask", methods=["POST"])
def ask():
    payload = request.get_json()
    user_query = payload.get("query", "").strip()
    utils = Utils()
    if not user_query:
        return jsonify({"error": "Query is required"}), 400
    
    context = utils.context_builder(user_query)
    if context is None:
        return jsonify({"error": "No relevant context found"}), 404

    answer = utils.generate_answer(user_query, context)
    return jsonify({"answer": answer}), 200

from flask import request, jsonify

@app.route("/contradict", methods=["POST"])
def contradict():
    try:
        payload = request.get_json()

        if not payload:
            return jsonify({"error": "Request body is required."}), 400

        contents = payload.get("contents")

        if not contents:
            return jsonify({"error": "'contents' field is required."}), 400

        if not isinstance(contents, list):
            return jsonify({"error": "'contents' must be a list."}), 400

        if len(contents) < 2:
            return jsonify({"error": "Provide at least two contents to compare."}), 400

        prompt = f"""
        You are an expert document comparison assistant.

        Your task is to compare the following pieces of text.

        Determine:
        1. Whether there are any contradictions or conflicts.
        2. What topic(s) they conflict on.
        3. Explain the reasoning.
        4. If they do not conflict, explain why.
        5. Ignore wording differences and focus on factual meaning.

        Return ONLY valid JSON in the following format:

        {{
            "contradiction": true,
            "reason": "...",
            "conflicting_topics": [
                "Topic 1",
                "Topic 2"
            ]
        }}

        Contents:

        """

        for idx, content in enumerate(contents, start=1):
            prompt += f"\nContent {idx}:\n{content}\n"
        llm = utils.load_llm()
        response = llm.invoke(prompt)

        return jsonify({
            "result": response.content
        })

    except Exception as e:
        return jsonify({
            "error": str(e)
        }), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)