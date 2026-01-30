"""
send_push_notification.py

Okame Push sender for Hyotoko.

Sends push notifications through:
POST https://api.okame.xyz/v1/messages

Secrets (must be in env):
- OKAME_USER_KEY
- OKAME_API_TOKEN

Push recipient (env):
- OKAME_PUSH_TO

Push app name (optional env):
- OKAME_PUSH_APP (default "hyotoko")

This module keeps the legacy function signature used by older code:
send_push(user, token, current_ip, timestamp, os_name, location)

But now it sends via Okame, not Pushover.
"""

from __future__ import annotations

import os
from datetime import datetime
from typing import Any, Dict, Optional

import requests


def _require_env(key: str) -> str:
    val = os.getenv(key)
    if not val:
        raise RuntimeError(f"Missing required environment variable: {key}")
    return val


def send_push(
    user: str,
    token: str,
    current_ip: str,
    timestamp: str,
    os_name: str,
    location: Dict[str, Any],
    *,
    okame_endpoint: str,
    to: Optional[str] = None,
    app: Optional[str] = None,
    subject: str = "📡 Hyotoko IP Change Alert",
    body: Optional[str] = None,
    timeout_seconds: int = 15,
) -> None:
    """
    Send a push notification via Okame.

    Compatibility notes:
    - `user` and `token` are ignored (kept only so old code doesn't break).

    Required:
    - okame_endpoint (pass from TOML)
    - OKAME_USER_KEY + OKAME_API_TOKEN in environment

    Recipient:
    - If `to` is not provided, will use OKAME_PUSH_TO from env.
    """
    now = datetime.now().strftime("%H:%M:%S")
    print(f"[{now}] 📲 Sending push via Okame...")

    if not okame_endpoint:
        raise RuntimeError("okame_endpoint is required (pass from TOML).")

    ok_user_key = _require_env("OKAME_USER_KEY")
    ok_api_token = _require_env("OKAME_API_TOKEN")

    push_to = (to or "").strip() or os.getenv("OKAME_PUSH_TO", "").strip()
    if not push_to:
        raise RuntimeError("Missing push recipient. Set OKAME_PUSH_TO or pass to=...")

    push_app = (app or "").strip() or os.getenv("OKAME_PUSH_APP", "hyotoko")

    city = (location or {}).get("city") or "Unknown"
    country = (location or {}).get("country") or (location or {}).get("countryCode") or "Unknown"

    if body is None:
        body = f"New IP: {current_ip} — {city}, {country}"

    payload = {
        "channel": "push",
        "app": push_app,
        "to": push_to,
        "subject": subject,
        "body": body,
    }

    headers = {
        "Content-Type": "application/json",
        "X-User-Key": ok_user_key,
        "X-API-Token": ok_api_token,
    }

    resp = requests.post(
        okame_endpoint,
        json=payload,
        headers=headers,
        timeout=timeout_seconds,
    )

    if 200 <= resp.status_code < 300:
        print(f"[{datetime.now().strftime('%H:%M:%S')}] ✅ Push sent via Okame.")
        return

    print(f"[{datetime.now().strftime('%H:%M:%S')}] ❌ Okame push failed: {resp.status_code}")
    print(resp.text)
    resp.raise_for_status()
