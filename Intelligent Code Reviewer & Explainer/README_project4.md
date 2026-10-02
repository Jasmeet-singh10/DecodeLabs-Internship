# Intelligent Code Reviewer & Explainer

DecodeLabs — Generative AI Project 4

A Streamlit app that ingests source code, analyzes it using Google's Gemini API, and returns a structured bug report plus a refactored, corrected version — rendered with Markdown and syntax highlighting.

## Features
- Ingests `.py`, `.js`, or `.java` files (upload or paste directly)
- Strict system instruction forces a deterministic two-part output: `## BUG_REPORT` and `## REFACTORED_CODE`
- Rejects malformed responses missing required section headers
- Split connect/read timeouts to avoid hanging requests
- Exponential backoff retries on rate limits / server errors
- Automatic fallback from `gemini-3.8-flash` to `gemini-3.5-flash-lite` if the primary model is overloaded
- Graceful handling of content-safety blocks (input & output)
- Clean web UI — no terminal required

## Setup

```bash
pip install -r requirements_project4.txt
streamlit run app_code_reviewer.py
```

## Getting a Gemini API Key
1. Go to https://aistudio.google.com/apikey
2. Sign in with your Google account
3. Click "Create API Key" — free tier available, no billing required

## Usage
1. Run the app
2. Paste your Gemini API key in the sidebar
3. Upload a code file, or paste code directly and select its language
4. Click **Review Code**
5. View the bug report and refactored code in the app

## How It Works
1. **Ingest** — reads the source file as a raw string, with error handling for missing files, permission issues, and encoding problems
2. **Orchestrate** — sends the code to Gemini with a locked system instruction defining the exact output format
3. **Validate** — checks the response contains both `## BUG_REPORT` and `## REFACTORED_CODE` headers; rejects anything malformed
4. **Render** — displays the structured Markdown output with syntax-highlighted code blocks

## Project Structure
```
.
├── app_code_reviewer.py        # Streamlit app
├── code_reviewer.py            # CLI version (terminal output)
├── requirements_project4.txt   # Python dependencies
└── README_project4.md
```

## Notes
- If you hit `503` errors, Gemini's servers are temporarily overloaded (a known, common issue on the free tier) — the app automatically retries and falls back to a lighter model before failing.
