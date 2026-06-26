# Medical Risk Analyzer
An AI-powered pipeline that reads medical lab report PDFs, extracts
health indicators, scores patient risk (0–100), and produces a plain-
English clinical summary — all via Claude's native document API.
---
## Quickstart
```bash
git clone <repo-url>
cd risk-analysis-usecase
pip install -r requirements.txt
cp .env.example .env        # paste your Anthropic API key
streamlit run app.py
```
Then open http://localhost:8501 in your browser.
## Stage 1 — Full Pipeline
### Step 1: Document Input
- **Sample tab:** choose from pre-loaded patient PDFs in `Documents/`
- **Upload tab:** drag-and-drop any medical lab PDF
### Step 2: Health Indicator Extraction (Claude API)
The PDF is base64-encoded and sent to `claude-sonnet-4-6` as a native
document content block. Claude extracts every measurable indicator and
returns structured JSON:
```json
{
  "patient_name": "John Doe",
  "report_date": "2024-01-15",
  "indicators": [
    {
      "name": "Hemoglobin",
      "value": "11.2",
      "unit": "g/dL",
      "reference_range": "13.5–17.5",
      "status": "abnormal",
      "note": "Mild anemia"
    }
  ]
}
```
Status classification rules:
| Status   | Meaning                                                        |
|----------|----------------------------------------------------------------|
| normal   | Value within reference range                                   |
| abnormal | Value outside reference range                                  |
| critical | Outside range AND flagged H*/L*/CRITICAL/PANIC in report       |
### Step 3: Results Display
- 4-column metrics: Risk Score / Risk Tier / Total Indicators / Flagged count
- Color banner: green → orange → red based on tier
- Indicator table: color-coded by status (green / orange / red rows)
### Step 4: AI Risk Analysis (Claude API)
A second Claude call receives the risk score, tier, and all flagged
indicators, then returns three sections:
- **SUMMARY** — 2–3 sentence plain-English overview
- **FLAGGED INDICATORS** — bullet list of abnormal/critical findings
- **RECOMMENDATIONS** — bullet list of suggested follow-up actions
## Stage 2 — Risk Scoring Logic
Scoring is deterministic (no LLM involved):
| Indicator Type | Points Each | Cap    |
|----------------|-------------|--------|
| abnormal       | +8 pts      | max 40 |
| critical       | +20 pts     | max 60 |
| Total          |             | 100    |
### Risk Tiers
| Score    | Tier       | Color  |
|----------|------------|--------|
| 0 – 49   | Low        | Green  |
| 50 – 69  | Moderate   | Yellow |
| 70 – 79  | Borderline | Orange |
| 80 – 100 | High       | Red    |
Borderline threshold = 70 — a score of 70+ indicates clinically
significant findings that warrant prompt medical review.
### Scoring Examples
| Scenario                        | Score | Tier       |
|---------------------------------|-------|------------|
| All indicators normal           | 0     | Low        |
| 3 abnormal, 0 critical          | 24    | Low        |
| 6 abnormal, 0 critical          | 40    | Moderate   |
| 3 critical, 2 abnormal          | 76    | Borderline |
| 3 critical, 5 abnormal (maxed)  | 100   | High       |
## Project Structure
```
risk-analysis-usecase/
├── app.py                  # Streamlit UI entry point
├── requirements.txt
├── .env.example            # Copy to .env and add API key
├── Documents/
│   ├── John Doe/
│   │   └── CBC-sample-report-with-notes_0.pdf
│   └── Wayne Rooney/
│       └── AI Medical test New.pdf
└── src/
    ├── __init__.py
    ├── claude_client.py    # PDF extraction + AI analysis via Claude
    ├── risk_scorer.py      # Risk score computation & tier logic
    ├── pdf_utils.py        # PDF → base64 encoding, Documents/ scanner
    └── ui_components.py    # Streamlit widgets (banner, table, sections)
```
## Environment Setup
Create a `.env` file (gitignored):
```
ANTHROPIC_API_KEY=sk-ant-api03-...
```
Or enter the key directly in the Streamlit sidebar at runtime.
## Sample Documents
| Patient      | Document                        | Expected Finding              |
|--------------|---------------------------------|-------------------------------|
| John Doe     | CBC report with clinical notes  | Several flagged CBC values    |
| Wayne Rooney | AI medical test                 | Varies                        |