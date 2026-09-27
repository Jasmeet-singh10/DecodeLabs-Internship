"""
DecodeLabs Project 2 — Automated Copywriting & Tone Transformer
------------------------------------------------------------------
Takes a raw product description plus user-chosen variables
(Product_Name, Platform, Tone) and compiles them into a dynamic
prompt template, then calls Gemini with adjustable Temperature/Top_P
to control creative variance.

Run:
    pip install -r requirements.txt
    cp .env.example .env      # then fill in your GEMINI_API_KEY
    python app.py
"""

import os
import random
import time

from dotenv import load_dotenv
from flask import Flask, jsonify, render_template, request
from google import genai
from google.genai import types

load_dotenv()

app = Flask(__name__)

client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))

MODEL = "gemini-3.6-flash"

RETRYABLE_MARKERS = ("503", "UNAVAILABLE", "overloaded", "high demand")
MAX_RETRIES = 3
BASE_DELAY_SECONDS = 1.5

# --- Platform-specific rules ---------------------------------------
# This is the "Application Layer as Gatekeeper" from the brief: the
# end user only ever supplies raw facts (product, description, tone).
# The structural/formatting requirements per platform are fixed here
# in code, not something the user can override, so brand/format
# consistency is enforced no matter what the user types.
PLATFORM_RULES = {
    "LinkedIn": (
        "Write a professional LinkedIn post. 80-180 words. "
        "End with 3-5 relevant hashtags. At most one emoji."
    ),
    "Instagram": (
        "Write a catchy Instagram caption. Under 120 words. "
        "Use emojis naturally throughout. End with 5-8 relevant hashtags."
    ),
    "Email": (
        "Write a marketing email. First line must be 'Subject: <subject line>'. "
        "Follow with a short body under 120 words. End with a clear call-to-action."
    ),
}

# --- The Master Instruction Template --------------------------------
# User variables are injected into this fixed template via an f-string.
# The model never sees a "system prompt" the user controls directly —
# only their raw Product_Name / Description / Tone values.
MASTER_TEMPLATE = """You are an expert marketing copywriter.

Product Name: {product_name}
Product Description: {description}
Target Tone: {tone}

Platform requirements:
{platform_rules}

Write ONLY the final, publish-ready copy. No explanations, no preamble, no markdown headers."""


def build_prompt(product_name, description, tone, platform):
    return MASTER_TEMPLATE.format(
        product_name=product_name,
        description=description,
        tone=tone,
        platform_rules=PLATFORM_RULES[platform],
    )


def call_gemini_with_retry(prompt, temperature, top_p):
    """Call the API, retrying with exponential backoff on transient
    'server overloaded' errors."""
    config = types.GenerateContentConfig(temperature=temperature, top_p=top_p)
    last_error = None
    for attempt in range(MAX_RETRIES):
        try:
            return client.models.generate_content(
                model=MODEL, contents=prompt, config=config
            )
        except Exception as exc:
            last_error = exc
            if not any(marker in str(exc) for marker in RETRYABLE_MARKERS):
                raise
            if attempt == MAX_RETRIES - 1:
                break
            delay = BASE_DELAY_SECONDS * (2 ** attempt) + random.uniform(0, 0.5)
            time.sleep(delay)
    raise last_error


@app.route("/")
def index():
    return render_template("index.html", platforms=list(PLATFORM_RULES.keys()))


@app.route("/api/generate", methods=["POST"])
def generate():
    data = request.get_json(silent=True) or {}

    product_name = (data.get("product_name") or "").strip()
    description = (data.get("description") or "").strip()
    tone = (data.get("tone") or "").strip()
    platform = (data.get("platform") or "").strip()

    # --- Structural validation gate --------------------------------
    if not product_name or not description or not tone:
        return jsonify({"error": "Product name, description, and tone are all required."}), 400
    if platform != "All" and platform not in PLATFORM_RULES:
        return jsonify({"error": f"Unknown platform: {platform}"}), 400

    try:
        temperature = float(data.get("temperature", 0.7))
        top_p = float(data.get("top_p", 0.95))
    except (TypeError, ValueError):
        return jsonify({"error": "Temperature and Top_P must be numbers."}), 400

    temperature = max(0.0, min(temperature, 2.0))
    top_p = max(0.0, min(top_p, 1.0))

    targets = list(PLATFORM_RULES.keys()) if platform == "All" else [platform]
    results = {}

    for target in targets:
        prompt = build_prompt(product_name, description, tone, target)
        try:
            response = call_gemini_with_retry(prompt, temperature, top_p)
        except Exception as exc:
            message = str(exc)
            print(f"[Gemini API error] {message}")  # check your terminal for this
            if any(marker in message for marker in RETRYABLE_MARKERS):
                friendly = "The AI is a bit busy right now — please try again in a moment."
            else:
                friendly = "Something went wrong talking to the model."
            return jsonify({"error": friendly}), 502

        results[target] = response.text

    return jsonify({"results": results})


if __name__ == "__main__":
    app.run(debug=True, port=5001)
