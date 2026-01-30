# send_push_notification.py
#
# Okame Push sender for Hyotoko
#
# Sends through:
#   POST {okame_endpoint}   (example: https://api.okame.xyz/v1/messages)
#
# Secrets (env required):
#   OKAME_USER_KEY
#   OKAME_API_TOKEN
#
# NOTE:
# - Subject is passed from TOML by the caller.
# - push_app is passed from TOML by the caller.
# - Does NOT require "to" (matches your known-good baseline).
# - Legacy signature preserved so existing callers don't break.

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
    subject: str,
    push_app: str,
    body: Optional[str] = None,
    timeout_seconds: int = 10,
) -> None:
    """
    Send a push notification through Okame.

    - user/token are ignored (legacy compatibility only).
    - subject MUST come from TOML.
    - push_app MUST come from TOML.
    - Does NOT include "to" unless your gateway requires it (baseline does not).
    """
    print(f"[{datetime.now().strftime('%H:%M:%S')}] 📲 Sending push via Okame...")

    if not okame_endpoint:
        raise RuntimeError("okame_endpoint is required (from TOML).")
    if not subject:
        raise RuntimeError("subject is required (from TOML).")
    if not push_app:
        raise RuntimeError("push_app is required (from TOML).")

    ok_user_key = _require_env("OKAME_USER_KEY")
    ok_api_token = _require_env("OKAME_API_TOKEN")

    if body is None:
        city = location.get("city", "Unknown")
        country = location.get("country", "Unknown")
        body = f"New Hyotoko IP: {current_ip} — {city}, {country}"

    payload = {
        "channel": "push",
        "app": push_app,   # from TOML
        "subject": subject,  # from TOML (shared with email)
        "body": body,
    }

    headers = {
        "Content-Type": "application/json",
        "X-User-Key": ok_user_key,
        "X-API-Token": ok_api_token,
    }

    resp = requests.post(okame_endpoint, json=payload, headers=headers, timeout=timeout_seconds)

    print("Status:", resp.status_code)
    print("Response:", resp.text)

    if 200 <= resp.status_code < 300:
        print(f"[{datetime.now().strftime('%H:%M:%S')}] ✅ Push sent via Okame.")
        return

    raise RuntimeError(f"Okame push failed: {resp.status_code} {resp.text}")
