"""
send_email_notification.py

Okame Email sender for Hyotoko.

Sends email through:
POST https://api.okame.xyz/v1/messages

Secrets (must be in env):
- OKAME_USER_KEY
- OKAME_API_TOKEN

This module keeps the legacy function signature used by older code:
send_email(ip, timestamp, os_name, location, sender_email, receiver_email, google_pass)

But now it sends via Okame, not SMTP.

Preferred usage (from your jnd_cloudflare_DDNS.py):
- Pass okame_endpoint / email_type / template / recipient from TOML
- Pass name/location_label as optional overrides
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


def send_email(
    ip: str,
    timestamp: str,
    os_name: str,
    location: Dict[str, Any],
    sender_email: str,
    receiver_email: str,
    google_pass: str,
    *,
    okame_endpoint: str,
    email_type: str = "html",          # "html" or "txt"
    template: str = "welcome",
    recipient: Optional[str] = None,   # if None, falls back to receiver_email (legacy)
    subject: str = "📡 New IP from Hyotoko",
    name: Optional[str] = None,
    location_label: Optional[str] = None,
    timeout_seconds: int = 15,
) -> None:
    """
    Send an email via Okame.

    Compatibility notes:
    - sender_email + google_pass are ignored (kept only so old code doesn't break).
    - receiver_email is used ONLY if recipient isn't provided.

    Required:
    - okame_endpoint (pass from TOML)
    - OKAME_USER_KEY + OKAME_API_TOKEN in environment
    """
    now = datetime.now().strftime("%H:%M:%S")
    print(f"[{now}] 📧 Sending email via Okame...")

    if not okame_endpoint:
        raise RuntimeError("okame_endpoint is required (pass from TOML).")

    ok_user_key = _require_env("OKAME_USER_KEY")
    ok_api_token = _require_env("OKAME_API_TOKEN")

    # recipient priority: explicit param -> legacy receiver_email
    to_email = (recipient or "").strip() or (receiver_email or "").strip()
    if not to_email:
        raise RuntimeError("Missing email recipient. Provide recipient=... or receiver_email.")

    # Defaults that can still be overridden by caller/env
    if name is None:
        name = os.getenv("OKAME_EMAIL_NAME", "Tadeu")
    if location_label is None:
        # Prefer explicit label, else use geo country if available, else env default, else Brazil
        location_label = (
            os.getenv("OKAME_LOCATION_LABEL")
            or (location or {}).get("country")
            or "Brazil"
        )

    payload = {
        "channel": "email",
        "emailType": email_type,
        "to": to_email,
        "subject": subject,
        "template": template,
        "context": {
            "name": name,
            "ip_address": ip,
            "location": f'{location_label} 🇧🇷',
        },
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
        print(f"[{datetime.now().strftime('%H:%M:%S')}] ✅ Email sent via Okame.")
        return

    print(f"[{datetime.now().strftime('%H:%M:%S')}] ❌ Okame email failed: {resp.status_code}")
    print(resp.text)
    resp.raise_for_status()
