# send_email_notification.py
#
# Okame Email sender for Hyotoko
#
# Sends through:
#   POST {okame_endpoint}   (example: https://api.okame.xyz/v1/messages)
#
# Secrets (env required):
#   OKAME_USER_KEY
#   OKAME_API_TOKEN
#
# Legacy signature preserved so existing callers don't break.

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
    email_type: str,
    email_template: str,
    email_recipient: str,
    subject: str = "📡 New IP from Hyotoko",
    name: Optional[str] = None,
    location_label: Optional[str] = None,
    timeout_seconds: int = 10,
) -> None:
    """
    Send an email through Okame.

    - sender_email / google_pass are ignored (legacy compatibility only).
    - email_recipient MUST come from TOML (single source of truth).
    """
    print(f"[{datetime.now().strftime('%H:%M:%S')}] 📧 Sending email via Okame...")

    if not okame_endpoint:
        raise RuntimeError("okame_endpoint is required (from TOML).")
    if not email_type:
        raise RuntimeError("email_type is required (from TOML).")
    if not email_template:
        raise RuntimeError("email_template is required (from TOML).")
    if not email_recipient:
        raise RuntimeError("email_recipient is required (from TOML).")

    ok_user_key = _require_env("OKAME_USER_KEY")
    ok_api_token = _require_env("OKAME_API_TOKEN")

    if name is None:
        name = os.getenv("OKAME_EMAIL_NAME", "Tadeu")

    if location_label is None:
        # Prefer env override, else geo country, else a safe default
        location_label = os.getenv("OKAME_LOCATION_LABEL") or location.get("country") or "Brazil"

    payload = {
        "channel": "email",
        "emailType": email_type,     # "html" or "txt"
        "to": email_recipient,
        "subject": subject,
        "template": email_template,  # e.g. "ip_update"
        "context": {
            "name": name,
            "ip_address": ip,
            "location": location_label,
        },
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
        print(f"[{datetime.now().strftime('%H:%M:%S')}] ✅ Email sent via Okame.")
        return

    raise RuntimeError(f"Okame email failed: {resp.status_code} {resp.text}")
