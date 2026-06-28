import os
import json
import time
import requests
from dotenv import load_dotenv

load_dotenv()

_BASE_URL      = os.getenv("AI_CORE_BASE_URL", "").rstrip("/")
_AUTH_URL      = os.getenv("AI_CORE_AUTH_URL", "").rstrip("/")
_CLIENT_ID     = os.getenv("AI_CORE_CLIENT_ID", "")
_CLIENT_SECRET = os.getenv("AI_CORE_CLIENT_SECRET", "")
_RESOURCE_GROUP = os.getenv("AI_CORE_RESOURCE_GROUP", "default")
_DEPLOYMENT_ID  = os.getenv("AI_CORE_DEPLOYMENT_ID", "")
_EMBEDDING_ID   = os.getenv("AI_CORE_EMBEDDING_ID", "")

_token_cache: dict = {"token": None, "expires_at": 0.0}


#  Auth 

def _get_token() -> str:
    if _token_cache["token"] and time.time() < _token_cache["expires_at"] - 60:
        return _token_cache["token"]

    resp = requests.post(
        f"{_AUTH_URL}/oauth/token",
        data={
            "grant_type":    "client_credentials",
            "client_id":     _CLIENT_ID,
            "client_secret": _CLIENT_SECRET,
        },
        timeout=30,
    )
    resp.raise_for_status()
    data = resp.json()
    _token_cache["token"]      = data["access_token"]
    _token_cache["expires_at"] = time.time() + data.get("expires_in", 3600)
    return _token_cache["token"]


def _headers() -> dict:
    return {
        "Authorization":    f"Bearer {_get_token()}",
        "AI-Resource-Group": _RESOURCE_GROUP,
        "Content-Type":     "application/json",
    }


#  Core invoke 

def _invoke(deployment_id: str, body: dict, timeout: int = 120) -> dict:
    url = f"{_BASE_URL}/v2/inference/deployments/{deployment_id}"
    resp = requests.post(url, headers=_headers(), json=body, timeout=timeout)
    resp.raise_for_status()
    return resp.json()


#  Claude calls 

def extract_indicators(pdf_b64: str) -> dict:
    system = """You are a medical data extraction assistant.
Extract ALL measurable health indicators from the lab report PDF.
Return ONLY valid JSON with no explanation or any markdown fences:
{
  "patient_name": "string",
  "report_date":  "string",
  "indicators": [
    {
      "name":            "string",
      "value":           "string",
      "unit":            "string",
      "reference_range": "string",
      "status":          "normal|abnormal|critical",
      "note":            "string"
    }
  ]
}
Status rules:
- normal:   value within reference range
- abnormal: value outside reference range
- critical: outside range AND marked H* / L* / CRITICAL / PANIC"""

    body = {
        "max_tokens": 4096,
        "system":     system,
        "messages": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "document",
                        "source": {
                            "type":       "base64",
                            "media_type": "application/pdf",
                            "data":       pdf_b64,
                        },
                    },
                    {
                        "type": "text",
                        "text": "Extract all health indicators and return the JSON.",
                    },
                ],
            }
        ],
    }

    raw = _invoke(_DEPLOYMENT_ID, body)["content"][0]["text"].strip()
    raw = raw.removeprefix("```json").removeprefix("```").removesuffix("```").strip()
    return json.loads(raw)


def generate_analysis(risk_score: int, risk_tier: str, flagged: list) -> str:
    lines = "\n".join(
        f"- {i['name']}: {i['value']} {i['unit']} "
        f"(ref: {i['reference_range']}) — {i.get('note', '')}"
        for i in flagged
    )

    body = {
        "max_tokens": 1024,
        "system": "You are a clinical risk analyst. Write plain-English summaries for non-specialist readers.",
        "messages": [
            {
                "role": "user",
                "content": (
                    f"Risk Score: {risk_score}/100\nRisk Tier: {risk_tier}\n\n"
                    f"Flagged Indicators:\n{lines}\n\n"
                    "Return exactly three sections:\n"
                    "SUMMARY\nFLAGGED INDICATORS\nRECOMMENDATIONS"
                ),
            }
        ],
    }

    return _invoke(_DEPLOYMENT_ID, body)["content"][0]["text"]


#  Embedding 

def get_embedding(text: str) -> list[float]:
    body = {"input": text}
    data = _invoke(_EMBEDDING_ID, body, timeout=30)
    return data["data"][0]["embedding"]