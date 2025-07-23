#!/usr/bin/env python3
# jnd_cloudflare_DDNS.py

import sys
import os
import json
import time
import signal
import socket
import uuid
import requests
import toml
import logging
from datetime import datetime, timezone
from dotenv import load_dotenv
from os.path import abspath, dirname

from send_push_notification import send_push
from send_email_notification import send_email

# === Set working directory ===
os.chdir(dirname(abspath(__file__)))

# === Load environment variables ===
load_dotenv()

# === Constants ===
CONFIG_FILE = "/home/tadeu/Python/IP_update/config.toml"
HISTORY_FILE = "/home/tadeu/Python/IP_update/ip_history.json"

CF_TOKEN = os.getenv("CF_TOKEN")
CF_ZONE = os.getenv("CF_ZONE", "example.com")
CF_SUBDOMAIN = os.getenv("CF_SUBDOMAIN", "matrix")
LOGGING_ENDPOINT = os.getenv("LOGGING_ENDPOINT")
CLIENT_API_TOKEN = os.getenv("CLIENT_API_TOKEN")
SENDER_EMAIL = os.getenv("SENDER_EMAIL")
RECEIVER_EMAIL = os.getenv("RECEIVER_EMAIL")
GOOGLE_PASS = os.getenv("GOOGLE_PASS")
PUSHOVER_USER = os.getenv("PUSHOVER_USER")
PUSHOVER_TOKEN = os.getenv("PUSHOVER_TOKEN")
SCRIPT_NAME = "jnd_cloudflare_DDNS"
SCRIPT_VERSION = "3.3"
ENVIRONMENT = os.getenv("ENVIRONMENT", "production")

CF_HEADERS = {
    "Authorization": f"Bearer {CF_TOKEN}",
    "Content-Type": "application/json"
}

# === Setup logging (stdout only) ===
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
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
def check_ip():
    response = requests.get('https://api.ipify.org', timeout=5)
    response.raise_for_status()
    return response.text.strip()

def get_geo(ip):
    response = requests.get(f'http://ip-api.com/json/{ip}', timeout=5)
    response.raise_for_status()
    return response.json()

def update_cloudflare_dns(ip):
    log.info("☁️ Checking Cloudflare DNS...")
    zone_resp = requests.get(
        f"https://api.cloudflare.com/client/v4/zones?name={CF_ZONE}",
        headers=CF_HEADERS, timeout=5
    ).json()
    zone_id = zone_resp["result"][0]["id"]

    record_resp = requests.get(
        f"https://api.cloudflare.com/client/v4/zones/{zone_id}/dns_records?name={CF_SUBDOMAIN}.{CF_ZONE}",
        headers=CF_HEADERS, timeout=5
    ).json()
    record_id = record_resp["result"][0]["id"]
    current_cf_ip = record_resp["result"][0]["content"]

    if current_cf_ip == ip:
        log.info(f"✅ Cloudflare DNS already set to {ip}")
        return "skipped"  # No update needed

    update_resp = requests.put(
        f"https://api.cloudflare.com/client/v4/zones/{zone_id}/dns_records/{record_id}",
        headers=CF_HEADERS,
        json={
            "type": "A",
            "name": f"{CF_SUBDOMAIN}.{CF_ZONE}",
            "content": ip,
            "ttl": 120,
            "proxied": False
        },
        timeout=5
    ).json()

    if update_resp.get("success"):
        log.info(f"✅ Cloudflare DNS updated to {ip}")
        return "success"
    else:
        log.error(f"❌ Failed to update DNS. Response: {json.dumps(update_resp, indent=2)}")
        return "failed"

def append_ip_history(ip, location, cf_status):
    timestamp = datetime.now(timezone.utc).isoformat()
    entry = {
        "ip": ip,
        "timestamp": timestamp,
        "location": location,
        "cloudflare_update": cf_status
    }
    os.makedirs(os.path.dirname(HISTORY_FILE), exist_ok=True)
    history = []
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, 'r') as f:
            history = json.load(f)
    history.append(entry)
    with open(HISTORY_FILE, 'w') as f:
        json.dump(history, f, indent=2)
    log.info(f"📝 IP history updated: {entry}")

# === Main loop ===
def main_loop():
    while not shutdown_requested:
        try:
            # Load config
            if os.path.exists(CONFIG_FILE):
                config = toml.load(CONFIG_FILE)
            else:
                log.warning("⚠️ Config file not found. Using defaults.")
                config = {"jnd_cloudflare_ddns": {"enabled": True, "interval_seconds": 30}}

            enabled = config.get("jnd_cloudflare_ddns", {}).get("enabled", False)
            interval = config.get("jnd_cloudflare_ddns", {}).get("interval_seconds", 30)

            if not enabled:
                log.info("🚫 Feature disabled in config.toml. Exiting.")
                break

            ip = check_ip()

            # Load last IP from history
            last_ip = None
            if os.path.exists(HISTORY_FILE):
                with open(HISTORY_FILE, 'r') as f:
                    history = json.load(f)
                    if history:
                        last_ip = history[-1]["ip"]

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
                        send_email(ip, datetime.now(timezone.utc).isoformat(), sys.platform, location, SENDER_EMAIL, RECEIVER_EMAIL, GOOGLE_PASS)
                        log.info("📧 Email notification sent.")
                    except Exception as e:
                        log.error(f"❌ Email notification failed: {e}")

                    try:
                        send_push(PUSHOVER_USER, PUSHOVER_TOKEN, ip, datetime.now(timezone.utc).isoformat(), sys.platform, location)
                        log.info("📲 Push notification sent.")
                    except Exception as e:
                        log.error(f"❌ Push notification failed: {e}")

                # Record in history (even if skipped or failed)
                append_ip_history(ip, location, cf_status)

        except Exception as e:
            log.error(f"❌ Error: {e}")

        # Sleep before next check
        if not shutdown_requested:
            log.info(f"🕒 Sleeping for {interval}s before next check...")
            time.sleep(interval)

if __name__ == "__main__":
    log.info("🚀 Starting JND Cloudflare DDNS Updater")
    main_loop()
