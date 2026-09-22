# Automated Copywriting & Tone Transformer — DecodeLabs Project 2

## Description

A Flask web app that compiles a product description into platform-ready
marketing copy, using a dynamic prompt template and adjustable
Temperature / Top_P parameters.

## How to Run

```bash
cd copywriter
python3 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env
# then edit .env and paste in your GEMINI_API_KEY (aistudio.google.com/apikey)

python app.py
```

Open http://127.0.0.1:5001 in your browser. (Different port from Project 1's
5000, so you can run both at once if needed.)

## How it maps to the assignment

| Requirement | Where it lives |
|---|---|
| Python script taking Product_Name, Platform, Tone as variables | The form in `index.html` posts these to `/api/generate` in `app.py` |
| Inject variables into a dynamic string template | `MASTER_TEMPLATE.format(...)` in `build_prompt()` — an f-string-style template compiled per request |
| Handle Temperature / Top_P system parameters | Sliders in the UI, passed through to `types.GenerateContentConfig(temperature=..., top_p=...)` |
| Tailored to different platforms | `PLATFORM_RULES` dict — fixed, code-enforced formatting rules per platform (LinkedIn/Instagram/Email), so the user can't accidentally break brand formatting | 
| Key skills: prompt template compilation, inference parameter tuning | `build_prompt()` + `call_gemini_with_retry()` |

**Bonus feature beyond the base spec:** selecting "All platforms" runs the
same product through all three templates in one click and shows them
side by side — a nice way to demonstrate the "Dynamic Orchestration"
idea from the brief (one input, multiple tailored outputs).

## What was intentionally left out

The assignment slide deck also covers async batch processing
(`asyncio`, semaphores, the OpenAI Batch API, `argparse` CLIs,
Pydantic schema validation). Those are "enterprise scale" extensions
for processing many products at once — this project handles one
product per request, which is what the stated Key Requirements ask
for. Worth exploring later if you want to extend this into a bulk
CSV-processing tool.

## Testing it

Try a few different tones on the same product and compare:
- Product: "AquaFlow Smart Water Bottle"
- Description: "Tracks hydration, glows to remind you to drink, syncs to an app."
- Tone: try "Professional" vs "Witty" vs "Luxurious" and compare the LinkedIn output
- Temperature: try 0.2 vs 1.2 on the same inputs and see how much the wording varies between runs
