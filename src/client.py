import os
import json
import time
import requests
from requests.auth import HTTPBasicAuth
from dotenv import load_dotenv

load_dotenv()

_BASE_URL = os.getenv("AI_CORE_BASE_URL", "").rstrip("/")
_AUTH_URL = os.getenv("AI_CORE_AUTH_URL", "")
_CLIENT_ID = os.getenv("AI_CORE_CLIENT_ID", "")
_CLIENT_SECRET = os.getenv("AI_CORE_CLIENT_SECRET", "")
_RESOURCE_GROUP = os.getenv("AI_CORE_RESOURCE_GROUP", "default")
_DEPLOYMENT_ID = os.getenv("AI_CORE_DEPLOYMENT_ID", "")
_EMBEDDING_ID = os.getenv("AI_CORE_EMBEDDING_ID", "")

_AZ_ENDPOINT = os.getenv("AZURE_EMBEDDING_ENDPOINT", "").rstrip("/")
_AZ_API_KEY = os.getenv("AZURE_EMBEDDING_API_KEY", "")
_AZ_DEPLOYMENT = os.getenv("AZURE_EMBEDDING_DEPLOYMENT", "")
_AZ_API_VERSION = os.getenv("AZURE_EMBEDDING_API_VERSION", "2024-02-01")

_token_cache: dict = {"token": None, "expires_at": 0.0}


def _get_token() -> str:
    if _token_cache["token"] and time.time() < _token_cache["expires_at"] - 60:
        return _token_cache["token"]
    resp = requests.post(
        _AUTH_URL,
        auth=HTTPBasicAuth(_CLIENT_ID, _CLIENT_SECRET),
        data={"grant_type": "client_credentials"},
        verify=False,
        timeout=30,
    )
    resp.raise_for_status()
    data = resp.json()
    _token_cache["token"] = data["access_token"]
    _token_cache["expires_at"] = time.time() + data.get("expires_in", 3600)
    return _token_cache["token"]


def _headers() -> dict:
    return {
        "Authorization": f"Bearer {_get_token()}",
        "AI-Resource-Group": _RESOURCE_GROUP,
        "Content-Type": "application/json",
    }


def _invoke_claude(body: dict, timeout: int = 120) -> dict:
    url = f"{_BASE_URL}/v2/inference/deployments/{_DEPLOYMENT_ID}/invoke"
    resp = requests.post(url, headers=_headers(), json=body, verify=False, timeout=timeout)
    resp.raise_for_status()
    return resp.json()


def extract_indicators(pdf_b64: str) -> dict:
    system = """You are a medical data extraction assistant.
Extract ALL measurable health indicators from the lab report PDF.
Return ONLY valid JSON — no explanation, no markdown fences.
Keep ALL string values as short as possible. Notes must be 5 words max.
{
  "patient_name": "string",
  "report_date": "string",
  "indicators": [
    {
      "name": "string",
      "value": "string",
      "unit": "string",
      "reference_range": "string",
      "status": "normal|abnormal|critical",
      "note": "max 5 words"
    }
  ]
}
Status rules:
- normal: value within reference range
- abnormal: value outside reference range
- critical: outside range AND marked H* / L* / CRITICAL / PANIC"""

    body = {
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": 8192,
        "system": system,
        "messages": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "document",
                        "source": {
                            "type": "base64",
                            "media_type": "application/pdf",
                            "data": pdf_b64,
                        },
                    },
                    {"type": "text", "text": "Extract all health indicators and return the JSON."},
                ],
            }
        ],
    }

    import json
    from json_repair import repair_json

    raw = _invoke_claude(body)["content"][0]["text"].strip()
    raw = raw.removeprefix("```json").removeprefix("```").removesuffix("```").strip()

    start = raw.find("{")
    end = raw.rfind("}") + 1
    if start == -1 or end == 0:
        raise ValueError(f"No JSON object found. Raw start: {raw[:200]}")
    raw = raw[start:end]

    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return json.loads(repair_json(raw))


def generate_analysis(risk_score: int, risk_tier: str, flagged: list) -> str:
    lines = "\n".join(
        f"- {i['name']}: {i['value']} {i['unit']} "
        f"(ref: {i['reference_range']}) — {i.get('note', '')}"
        for i in flagged
    )
    body = {
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": 1024,
        "system": "You are a clinical risk analyst. Write plain-English summaries for non-specialist readers.",
        "messages": [
            {
                "role": "user",
                "content": (
                    f"Risk Score: {risk_score}/100\nRisk Tier: {risk_tier}\n\n"
                    f"Flagged Indicators:\n{lines}\n\n"
                    "Return exactly three sections:\nSUMMARY\nFLAGGED INDICATORS\nRECOMMENDATIONS"
                ),
            }
        ],
    }
    return _invoke_claude(body, timeout=60)["content"][0]["text"]


def get_embedding(text: str) -> list[float]:
    url = (
        f"{_AZ_ENDPOINT}/openai/deployments/{_AZ_DEPLOYMENT}"
        f"/embeddings?api-version={_AZ_API_VERSION}"
    )
    headers = {
        "api-key": _AZ_API_KEY,
        "Content-Type": "application/json",
    }
    resp = requests.post(url, headers=headers, json={"input": text}, verify=False, timeout=30)
    resp.raise_for_status()
    return resp.json()["data"][0]["embedding"]