#!/usr/bin/env python3
# jnd_cloudflare_DDNS.py
#
# Cloudflare DDNS updater + Okame notifications (email + push)
#
# Config (TOML):
#   [jnd_cloudflare_ddns]
#   enabled = true
#   interval_seconds = 120
#   okame_endpoint = "https://api.okame.xyz/v1/messages"
#   subject = "⚡️ New IP from Hyotoko"
#   email_type = "html"
#   email_template = "ip_update"
#   email_recipient = "tadeubanzato@gmail.com"
#   push_app = "hyotoko"
#
# Secrets (ENV):
#   CF_TOKEN
#   OKAME_USER_KEY
#   OKAME_API_TOKEN
#
# Optional ENV:
#   OKAME_EMAIL_NAME (default "Tadeu")
#   OKAME_LOCATION_LABEL (default from geo country, else "Brazil")

from __future__ import annotations

import sys
import os
import json
import time
import signal
import requests
import toml
import logging
from datetime import datetime, timezone
from dotenv import load_dotenv
from os.path import abspath, dirname
from typing import Any, Dict, Optional

from send_push_notification import send_push
from send_email_notification import send_email


# === Set working directory ===
os.chdir(dirname(abspath(__file__)))

# === Load environment variables ===
load_dotenv()

# === Constants ===
CONFIG_FILE = "/home/tadeu/Python/IP_update/config.toml"
HISTORY_FILE = "/home/tadeu/Python/IP_update/ip_history.json"

# Cloudflare env
CF_TOKEN = os.getenv("CF_TOKEN")
CF_ZONE = os.getenv("CF_ZONE", "example.com")
CF_SUBDOMAIN = os.getenv("CF_SUBDOMAIN", "matrix")

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


# === Helper functions ===
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

    os.makedirs(os.path.dirname(HISTORY_FILE), exist_ok=True)

    history: list = []
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, "r") as f:
                history = json.load(f) or []
        except Exception:
            history = []

    history.append(entry)

    with open(HISTORY_FILE, "w") as f:
        json.dump(history, f, indent=2)

    log.info(f"📝 IP history updated: ip={ip} cf={cf_status}")


def _load_cfg() -> Dict[str, Any]:
    if not os.path.exists(CONFIG_FILE):
        log.warning("⚠️ Config file not found. Using defaults.")
        return {"enabled": True, "interval_seconds": 30}
    config = toml.load(CONFIG_FILE)
    return config.get("jnd_cloudflare_ddns", {}) or {}


def _require_cfg(cfg: Dict[str, Any], key: str) -> Any:
    val = cfg.get(key)
    if val is None or (isinstance(val, str) and not val.strip()):
        raise RuntimeError(f"config.toml missing: [jnd_cloudflare_ddns].{key}")
    return val


# === Main loop ===
def main_loop():
    while not shutdown_requested:
        interval = 30

        try:
            cfg = _load_cfg()
            enabled = bool(cfg.get("enabled", False))
            interval = int(cfg.get("interval_seconds", 30))

            if not enabled:
                log.info("🚫 Feature disabled in config.toml. Exiting.")
                break

            # Required from TOML (your final spec)
            okame_endpoint = _require_cfg(cfg, "okame_endpoint")
            subject = _require_cfg(cfg, "subject")
            email_type = _require_cfg(cfg, "email_type")
            email_template = _require_cfg(cfg, "email_template")
            email_recipient = _require_cfg(cfg, "email_recipient")
            push_app = _require_cfg(cfg, "push_app")

            ip = check_ip()

            # Load last IP from history
            last_ip: Optional[str] = None
            if os.path.exists(HISTORY_FILE):
                try:
                    with open(HISTORY_FILE, "r") as f:
                        history = json.load(f) or []
                        if history:
                            last_ip = history[-1].get("ip")
                except Exception:
                    last_ip = None

            if ip == last_ip:
                log.info("ℹ️ IP has not changed. Skipping GeoIP, Cloudflare, and notifications.")
            else:
                log.info("🔄 IP has changed. Proceeding with GeoIP and updates...")
                location = get_geo(ip)

                cf_status = update_cloudflare_dns(ip)

                if cf_status == "success":
                    ts = datetime.now(timezone.utc).isoformat()

                    try:
                        send_email(
                            ip,
                            ts,
                            sys.platform,
                            location,
                            "", "", "",  # legacy args ignored
                            okame_endpoint=okame_endpoint,
                            subject=subject,
                            email_type=email_type,
                            email_template=email_template,
                            email_recipient=email_recipient,
                        )
                        log.info("📧 Email notification sent (Okame).")
                    except Exception as e:
                        log.error(f"❌ Email notification failed (Okame): {e}")

                    try:
                        send_push(
                            "", "",  # legacy args ignored
                            ip,
                            ts,
                            sys.platform,
                            location,
                            okame_endpoint=okame_endpoint,
                            subject=subject,
                            push_app=push_app,
                        )
                        log.info("📲 Push notification sent (Okame).")
                    except Exception as e:
                        log.error(f"❌ Push notification failed (Okame): {e}")

                append_ip_history(ip, location, cf_status)

        except Exception as e:
            log.error(f"❌ Error: {e}")

        if not shutdown_requested:
            log.info(f"🕒 Sleeping for {interval}s before next check...")
            time.sleep(interval)


if __name__ == "__main__":
    log.info(f"🚀 Starting {SCRIPT_NAME} v{SCRIPT_VERSION} ({ENVIRONMENT})")
    main_loop()
