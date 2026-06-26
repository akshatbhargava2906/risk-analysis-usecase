# Medical Risk Analysis — Claude Code Guide

## Project Overview
End-to-end medical PDF risk analysis pipeline. Accepts lab report PDFs,
extracts health indicators via Claude's native PDF API, computes a
deterministic risk score (0–100), and generates an AI-powered clinical
risk summary.

## Tech Stack
- Python 3.11+
- Streamlit (web UI)
- Anthropic SDK — model: `claude-sonnet-4-6`
- python-dotenv, pandas

## Run the App
```bash
pip install -r requirements.txt
cp .env.example .env          # add your ANTHROPIC_API_KEY
streamlit run app.py
File Structure
app.py                  # Streamlit entry point
src/
  claude_client.py      # Claude API calls (extraction + analysis)
  risk_scorer.py        # Deterministic scoring algorithm
  pdf_utils.py          # PDF → base64, Documents/ scanner
  ui_components.py      # Reusable Streamlit widgets
Documents/
  John Doe/             # Sample CBC report
  Wayne Rooney/         # Sample AI medical test
Pipeline — Stage 1: Extraction & Analysis
User selects a sample PDF or uploads one
PDF bytes → base64 → Claude Messages API (type: document)
Claude returns strict JSON: {patient_name, report_date, indicators[]}
Each indicator has: name, value, unit, reference_range, status (normal|abnormal|critical), note
Risk score computed (Stage 2)
Second Claude call: score + flagged indicators → SUMMARY / FLAGGED INDICATORS / RECOMMENDATIONS
Pipeline — Stage 2: Risk Scoring
Each abnormal indicator: +8 pts (capped at 40)
Each critical indicator: +20 pts (capped at 60)
Total max: 100
Score	Tier
0–49	Low
50–69	Moderate
70–79	Borderline
80–100	High
Borderline threshold = 70 (as specified).

Claude PDF API — Key Detail
PDFs are sent as document content blocks (NOT image):

{"type": "document", "source": {"type": "base64", "media_type": "application/pdf", "data": <b64>}}
No beta header required. Document block must come before the text block in the content array.

Environment
ANTHROPIC_API_KEY — in .env file or entered in Streamlit sidebar
API key entered in sidebar overrides .env at call time