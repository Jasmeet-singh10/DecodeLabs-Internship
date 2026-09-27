# Multimodal Image Generation Studio

DecodeLabs — Generative AI Project 3

A Streamlit app that turns text prompts into images using either **Stability AI (Stable Image Core)** or **OpenAI (gpt-image-1)**.

## Features
- Text-to-image generation via Stability AI or OpenAI
- Aspect ratio → resolution mapping (1:1, 16:9, 9:16, 3:2, 2:3, 4:5, 5:4)
- Split connect/read timeouts (3.05s connect, 60s read) to avoid hanging requests
- Exponential backoff + jitter retries on 429/5xx (fails fast on connection errors)
- Graceful handling of content-moderation blocks (input & output gates)
- Memory-safe chunked streaming of image bytes to disk
- Pixel-level integrity verification (`Image.load()`) to catch truncated downloads
- Multi-image generation with preview + download in the UI

## Setup

```bash
pip install -r requirements.txt
streamlit run app.py
```

If you hit `ModuleNotFoundError: No module named 'imghdr'` on Python 3.13+, run:

```bash
pip install --upgrade streamlit
# or, if that doesn't fix it:
pip install standard-imghdr
```

## Getting an API Key

**Stability AI** (recommended — has a free tier)
1. Sign up at https://platform.stability.ai
2. Go to "API Keys" in your dashboard
3. Generate a key

**OpenAI**
1. Sign up at https://platform.openai.com
2. Settings → API Keys → Create new secret key
3. Requires billing to be added

## Usage
1. Run the app (`streamlit run app.py`)
2. In the sidebar: choose an engine, paste your API key, pick an aspect ratio
3. Enter a prompt (and optional negative prompt for Stability)
4. Click **Generate**
5. Preview and download the resulting images

Generated images are also saved locally to the `generated_assets/` folder.

## Project Structure
```
.
├── app.py              # Main Streamlit app
├── requirements.txt    # Python dependencies
└── generated_assets/   # Output images (created at runtime)
```
