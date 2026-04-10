"""
Zürich News Connector
- Raw data from SRGSSR Articles API (SRF, SWI, RTS, RSI, RTR)
- Requires OAuth2 client credentials from developer.srgssr.ch
"""

import requests
import os
import time
import base64
from dotenv import load_dotenv

load_dotenv()

SRGSSR_CLIENT_ID = os.environ.get("SRGSSR_CLIENT_ID", "")
SRGSSR_CLIENT_SECRET = os.environ.get("SRGSSR_CLIENT_SECRET", "")
SRGSSR_TOKEN_URL = "https://api.srgssr.ch/oauth/v1/accesstoken?grant_type=client_credentials"
SRGSSR_ARTICLES_URL = "https://api.srgssr.ch/srgssr-articles/v2/articles/articles/"

_token_cache = {"token": None, "expires": 0}


def _get_access_token():
    """Get OAuth2 access token using Basic Auth with Base64 encoded credentials."""
    global _token_cache

    if _token_cache["token"] and time.time() < _token_cache["expires"] - 86400:
        return _token_cache["token"]

    if not SRGSSR_CLIENT_ID or not SRGSSR_CLIENT_SECRET:
        return None

    try:
        credentials = base64.b64encode(f"{SRGSSR_CLIENT_ID}:{SRGSSR_CLIENT_SECRET}".encode()).decode()

        resp = requests.post(
            SRGSSR_TOKEN_URL,
            headers={
                "Authorization": f"Basic {credentials}",
                "Content-Length": "0",
                "Cache-Control": "no-cache",
            },
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()
        _token_cache["token"] = data.get("access_token")
        expires_in = data.get("expires_in", 604800)
        _token_cache["expires"] = time.time() + expires_in
        return _token_cache["token"]
    except Exception as e:
        print(f"Token error: {e}")
        return None


def get_news(limit=10, publisher="SRF"):
    """Get latest articles from SRGSSR (SRF, SWI, RTS, RSI, RTR)."""
    try:
        token = _get_access_token()
        if not token:
            return {
                "success": False,
                "data": None,
                "source": {"name": "SRGSSR", "type": "official"},
                "error": "No API credentials configured. Set SRGSSR_CLIENT_ID and SRGSSR_CLIENT_SECRET environment variables. Register at https://developer.srgssr.ch"
            }

        headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/json",
        }

        params = {
            "limit": min(limit, 10),
            "publisher": publisher,
        }

        resp = requests.get(SRGSSR_ARTICLES_URL, headers=headers, params=params, timeout=15)
        resp.raise_for_status()
        data = resp.json()

        articles = []
        for article in data.get("results", []):
            articles.append({
                "id": article.get("id", ""),
                "title": article.get("title", ""),
                "description": article.get("lead", "") or article.get("description", ""),
                "url": article.get("url", "") or article.get("webUrl", ""),
                "date": article.get("date", "") or article.get("publishedDate", ""),
                "category": article.get("category", "") or article.get("rubric", ""),
                "publisher": article.get("publisher", publisher),
            })

        return {
            "success": True,
            "data": {
                "articles": articles,
                "cursor": data.get("cursor"),
            },
            "source": {"name": "SRGSSR", "type": "official"},
            "error": None,
        }
    except Exception as e:
        return {"success": False, "data": None, "source": {"name": "SRGSSR", "type": "official"}, "error": str(e)}
