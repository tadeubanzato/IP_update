#!/usr/bin/env python3
"""
jnd_cloudflare_DDNS.py

Hyotoko DDNS updater:
- Checks public IP
- GeoIP lookup
- Updates Cloudflare DNS A record
- Records IP history locally
- Sends Okame notifications on IP change:
    - Email (template + context) using config.toml defaults
    - Push (optional) if OKAME_PUSH_TO is set in env

Config (TOML) required:

[jnd_cloudflare_ddns]
enabled = true
interval_seconds = 120
okame_endpoint = "https://api.okame.xyz/v1/messages"
email_type = "html"
email_template = "welcome"
email_recipient = "tadeubanzato@gmail.com"

Env required:
- CF_TOKEN
- CF_ZONE
- CF_SUBDOMAIN

Okame env required:
- OKAME_USER_KEY
- OKAME_API_TOKEN

Okame env optional:
- OKAME_EMAIL_NAME (default "Tadeu")
- OKAME_LOCATION_LABEL (default "Brazil")
- OKAME_PUSH_TO (if set, push will be sent)
- OKAME_PUSH_APP (default "hyotoko")
"""

from __future__ import annotations

import os
import sys
import json
import time
import signal
import logging
from datetime import datetime, timezone
from os.path import abspath, dirname
from typing import Any, Dict, Optional

import requests
import toml
from dotenv import load_dotenv


# === Set working directory ===
os.chdir(dirname(abspath(__file__)))

# === Load environment variables ===
load_dotenv()

# === Files ===
CONFIG_FILE = "/home/tadeu/Python/IP_update/config.toml"
HISTORY_FILE = "/home/tadeu/Python/IP_update/ip_history.json"

# === Cloudflare (env) ===
CF_TOKEN = os.getenv("CF_TOKEN")
CF_ZONE = os.getenv("CF_ZONE", "example.com")
CF_SUBDOMAIN = os.getenv("CF_SUBDOMAIN", "matrix")

# === Okame (env secrets) ===
OKAME_USER_KEY = os.getenv("OKAME_USER_KEY")
OKAME_API_TOKEN = os.getenv("OKAME_API_TOKEN")

# === Okame (env optional) ===
OKAME_EMAIL_NAME = os.getenv("OKAME_EMAIL_NAME", "Tadeu")
OKAME_LOCATION_LABEL = os.getenv("OKAME_LOCATION_LABEL", "Brazil")

OKAME_PUSH_TO = os.getenv("OKAME_PUSH_TO")  # if unset, push is skipped
OKAME_PUSH_APP = os.getenv("OKAME_PUSH_APP", "hyotoko")

SCRIPT_NAME = "jnd_cloudflare_DDNS"
SCRIPT_VERSION = "3.5"
ENVIRONMENT = os.getenv("ENVIRONMENT", "production")

CF_HEADERS = {
    "Authorization": f"Bearer {CF_TOKEN}" if CF_TOKEN else "",
    "Content-Type": "application/json",
}

# === Setup logging (stdout only) ===
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
log = logging.getLogger(SCRIPT_NAME)

# === Graceful shutdown ===
shutdown_requested = False


def signal_handler(signum, frame):
    global shutdown_requested
    shutdown_requested = True
    log.info("🛑 Shutdown signal received. Exiting after current cycle...")


signal.signal(signal.SIGTERM, signal_handler)
signal.signal(signal.SIGINT, signal_handler)


# === Helpers ===
def safe_load_json(path: str) -> Any:
    if not os.path.exists(path):
        return None
    try:
        with open(path, "r") as f:
            return json.load(f)
    except Exception:
        return None


def safe_write_json(path: str, data: Any) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        json.dump(data, f, indent=2)


def check_ip() -> str:
    resp = requests.get("https://api.ipify.org", timeout=10)
    resp.raise_for_status()
    return resp.text.strip()


def get_geo(ip: str) -> Dict[str, Any]:
    resp = requests.get(f"http://ip-api.com/json/{ip}", timeout=10)
    resp.raise_for_status()
    return resp.json()


def update_cloudflare_dns(ip: str) -> str:
    if not CF_TOKEN:
        log.error("❌ CF_TOKEN is not set. Cannot update Cloudflare.")
        return "failed"

    log.info("☁️ Checking Cloudflare DNS...")

    zone_resp = requests.get(
        f"https://api.cloudflare.com/client/v4/zones?name={CF_ZONE}",
        headers=CF_HEADERS,
        timeout=10,
    ).json()

    if not zone_resp.get("result"):
        log.error(f"❌ Could not find zone '{CF_ZONE}'. Response: {json.dumps(zone_resp, indent=2)}")
        return "failed"

    zone_id = zone_resp["result"][0]["id"]

    record_name = f"{CF_SUBDOMAIN}.{CF_ZONE}"
    record_resp = requests.get(
        f"https://api.cloudflare.com/client/v4/zones/{zone_id}/dns_records?name={record_name}",
        headers=CF_HEADERS,
        timeout=10,
    ).json()

    if not record_resp.get("result"):
        log.error(f"❌ Could not find DNS record '{record_name}'. Response: {json.dumps(record_resp, indent=2)}")
        return "failed"

    record_id = record_resp["result"][0]["id"]
    current_cf_ip = record_resp["result"][0].get("content")

    if current_cf_ip == ip:
        log.info(f"✅ Cloudflare DNS already set to {ip}")
        return "skipped"

    update_resp = requests.put(
        f"https://api.cloudflare.com/client/v4/zones/{zone_id}/dns_records/{record_id}",
        headers=CF_HEADERS,
        json={
            "type": "A",
            "name": record_name,
            "content": ip,
            "ttl": 120,
            "proxied": False,
        },
        timeout=10,
    ).json()

    if update_resp.get("success"):
        log.info(f"✅ Cloudflare DNS updated to {ip}")
        return "success"

    log.error(f"❌ Failed to update DNS. Response: {json.dumps(update_resp, indent=2)}")
    return "failed"


def append_ip_history(ip: str, location: Dict[str, Any], cf_status: str) -> None:
    timestamp = datetime.now(timezone.utc).isoformat()
    entry = {
        "ip": ip,
        "timestamp": timestamp,
        "location": location,
        "cloudflare_update": cf_status,
    }

    history = safe_load_json(HISTORY_FILE)
    if not isinstance(history, list):
        history = []
    history.append(entry)

    safe_write_json(HISTORY_FILE, history)
    log.info(f"📝 IP history updated: ip={ip} cf={cf_status}")


def okame_headers() -> Dict[str, str]:
    if not OKAME_USER_KEY or not OKAME_API_TOKEN:
        raise RuntimeError("Missing OKAME_USER_KEY / OKAME_API_TOKEN in environment.")
    return {
        "Content-Type": "application/json",
        "X-User-Key": OKAME_USER_KEY,
        "X-API-Token": OKAME_API_TOKEN,
    }


def send_okame_email(
    *,
    okame_endpoint: str,
    email_type: str,
    email_template: str,
    email_recipient: str,
    ip: str,
) -> None:
    payload = {
        "channel": "email",
        "emailType": email_type,
        "to": email_recipient,
        "subject": "📡 New IP from Hyotoko",
        "template": email_template,
        "context": {
            "name": OKAME_EMAIL_NAME,
            "ip_address": ip,
            "location": OKAME_LOCATION_LABEL,
        },
    }

    resp = requests.post(okame_endpoint, json=payload, headers=okame_headers(), timeout=15)
    if 200 <= resp.status_code < 300:
        log.info("📧 Email sent via Okame.")
        return

    log.error(f"❌ Okame email failed: {resp.status_code} {resp.text}")
    resp.raise_for_status()


def send_okame_push(*, okame_endpoint: str, ip: str, location: Dict[str, Any]) -> None:
    if not OKAME_PUSH_TO:
        log.info("ℹ️ OKAME_PUSH_TO not set — skipping push.")
        return

    city = (location or {}).get("city") or "Unknown"
    country = (location or {}).get("country") or (location or {}).get("countryCode") or "Unknown"

    payload = {
        "channel": "push",
        "app": OKAME_PUSH_APP,
        "to": OKAME_PUSH_TO,
        "subject": "📡 Hyotoko IP Change Alert",
        "body": f"New IP: {ip} — {city}, {country}",
    }

    resp = requests.post(okame_endpoint, json=payload, headers=okame_headers(), timeout=15)
    if 200 <= resp.status_code < 300:
        log.info("📲 Push sent via Okame.")
        return

    log.error(f"❌ Okame push failed: {resp.status_code} {resp.text}")
    resp.raise_for_status()


# === Main loop ===
def main_loop():
    while not shutdown_requested:
        interval = 30  # default fallback

        try:
            # Load config (every loop so you can change interval without restart)
            if os.path.exists(CONFIG_FILE):
                config = toml.load(CONFIG_FILE)
            else:
                log.warning("⚠️ Config file not found. Using defaults.")
                config = {"jnd_cloudflare_ddns": {"enabled": True, "interval_seconds": 30}}

            cfg = config.get("jnd_cloudflare_ddns", {})
            enabled = bool(cfg.get("enabled", False))
            interval = int(cfg.get("interval_seconds", 30))

            if not enabled:
                log.info("🚫 Feature disabled in config.toml. Exiting.")
                break

            # Okame config from TOML (as you specified)
            okame_endpoint = cfg.get("okame_endpoint")
            email_type = cfg.get("email_type", "html")
            email_template = cfg.get("email_template", "welcome")
            email_recipient = cfg.get("email_recipient")

            if not okame_endpoint:
                raise RuntimeError("config.toml missing: jnd_cloudflare_ddns.okame_endpoint")
            if not email_recipient:
                raise RuntimeError("config.toml missing: jnd_cloudflare_ddns.email_recipient")

            ip = check_ip()

            # Load last IP from history
            last_ip = None
            history = safe_load_json(HISTORY_FILE)
            if isinstance(history, list) and history:
                last_ip = history[-1].get("ip")

            if ip == last_ip:
                log.info("ℹ️ IP has not changed. Skipping GeoIP, Cloudflare, and notifications.")
            else:
                log.info("🔄 IP has changed. Proceeding with GeoIP and updates...")
                location = get_geo(ip)

                # Update Cloudflare
                cf_status = update_cloudflare_dns(ip)

                # Send notifications only if update was successful
                if cf_status == "success":
                    try:
                        send_okame_email(
                            okame_endpoint=okame_endpoint,
                            email_type=email_type,
                            email_template=email_template,
                            email_recipient=email_recipient,
                            ip=ip,
                        )
                    except Exception as e:
                        log.error(f"❌ Email notification failed: {e}")

                    try:
                        send_okame_push(okame_endpoint=okame_endpoint, ip=ip, location=location)
                    except Exception as e:
                        log.error(f"❌ Push notification failed: {e}")

                # Record in history (even if skipped or failed)
                append_ip_history(ip, location, cf_status)

        except Exception as e:
            log.error(f"❌ Error: {e}")

        if not shutdown_requested:
            log.info(f"🕒 Sleeping for {interval}s before next check...")
            time.sleep(interval)


if __name__ == "__main__":
    log.info(f"🚀 Starting {SCRIPT_NAME} v{SCRIPT_VERSION} ({ENVIRONMENT})")
    main_loop()
