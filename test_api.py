import os
import json
import time
import requests
from dotenv import load_dotenv

load_dotenv()

BASE_URL       = os.getenv("AI_CORE_BASE_URL", "").rstrip("/")
AUTH_URL       = os.getenv("AI_CORE_AUTH_URL", "").rstrip("/")
CLIENT_ID      = os.getenv("AI_CORE_CLIENT_ID", "")
CLIENT_SECRET  = os.getenv("AI_CORE_CLIENT_SECRET", "")
RESOURCE_GROUP = os.getenv("AI_CORE_RESOURCE_GROUP", "default")
DEPLOYMENT_ID  = os.getenv("AI_CORE_DEPLOYMENT_ID", "")
EMBEDDING_ID   = os.getenv("AI_CORE_EMBEDDING_ID", "")


def test_env():
    print("\n1. ENV VARIABLES")
    required = {
        "AI_CORE_BASE_URL":       BASE_URL,
        "AI_CORE_AUTH_URL":       AUTH_URL,
        "AI_CORE_CLIENT_ID":      CLIENT_ID,
        "AI_CORE_CLIENT_SECRET":  CLIENT_SECRET,
        "AI_CORE_DEPLOYMENT_ID":  DEPLOYMENT_ID,
        "AI_CORE_EMBEDDING_ID":   EMBEDDING_ID,
    }
    all_ok = True
    for key, val in required.items():
        status = "OK" if val else "MISSING"
        print(f"  {status}  {key}")
        if not val:
            all_ok = False
    return all_ok


def test_token():
    print("\n2. TOKEN FETCH")
    try:
        resp = requests.post(
            f"{AUTH_URL}/oauth/token",
            data={
                "grant_type":    "client_credentials",
                "client_id":     CLIENT_ID,
                "client_secret": CLIENT_SECRET,
            },
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()
        token = data["access_token"]
        expires = data.get("expires_in", "?")
        print(f"OK  Token received  (expires_in: {expires}s)")
        print(f"Token prefix: {token[:20]}...")
        return token
    except Exception as e:
        print(f"FAIL  {e}")
        return None


def test_claude(token: str):
    print("\n3. CLAUDE INVOKE")
    url = f"{BASE_URL}/v2/inference/deployments/{DEPLOYMENT_ID}/invoke"
    headers = {
        "Authorization":     f"Bearer {token}",
        "AI-Resource-Group":  RESOURCE_GROUP,
        "Content-Type":      "application/json",
    }
    body = {
        "anthropic_version": "bedrock-2023-05-31",   # ← this line added
        "max_tokens": 64,
        "messages": [
            {"role": "user", "content": "Reply with exactly: CLAUDE_OK"}
        ],
    }
    try:
        start = time.time()
        resp = requests.post(url, headers=headers, json=body, timeout=60)
        elapsed = round(time.time() - start, 2)
        resp.raise_for_status()
        reply = resp.json()["content"][0]["text"].strip()
        print(f"OK  Response in {elapsed}s")
        print(f"Reply: {reply}")
    except Exception as e:
        print(f"FAIL  {e}")
        if hasattr(e, "response") and e.response is not None:
            print(f"Status: {e.response.status_code}")
            print(f"Body:   {e.response.text[:300]}")


def test_embedding(token: str):
    print("\n4. EMBEDDING INVOKE")
    url = f"{BASE_URL}/v2/inference/deployments/{EMBEDDING_ID}/invoke"
    headers = {
        "Authorization":     f"Bearer {token}",
        "AI-Resource-Group":  RESOURCE_GROUP,
        "Content-Type":      "application/json",
    }
    body = {"input": "Hemoglobin level is low."}
    try:
        start = time.time()
        resp = requests.post(url, headers=headers, json=body, timeout=30)
        elapsed = round(time.time() - start, 2)
        resp.raise_for_status()
        data = resp.json()
        vector = data["data"][0]["embedding"]
        print(f"OK  Response in {elapsed}s")
        print(f"Vector dimensions: {len(vector)}")
        print(f"First 5 values:    {vector[:5]}")
    except Exception as e:
        print(f"FAIL  {e}")
        if hasattr(e, "response") and e.response is not None:
            print(f"Status: {e.response.status_code}")
            print(f"Body:   {e.response.text[:300]}")


if __name__ == "__main__":
    print("AI Core Connection Test")

    env_ok = test_env()
    if not env_ok:
        print("\nFix missing env variables in .env before continuing.")
        exit(1)

    token = test_token()
    if not token:
        print("\nCannot proceed without a valid token.")
        exit(1)

    test_claude(token)
    test_embedding(token)
    print("Done")