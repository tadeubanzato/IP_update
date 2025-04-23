#!/usr/bin/env python3
# ip_update.py

import sys
import os
import json
import timeit
import requests
import ssl
import socket
import uuid
from datetime import datetime, timezone, timedelta
from dotenv import load_dotenv
from os.path import abspath, dirname

from send_push_notification import send_push
from send_email_notification import send_email

# Set working directory
os.chdir(dirname(abspath(__file__)))

# Load environment variables
load_dotenv()

# Constants
SCRIPT_NAME = "jnd_cloudflare_DDNS"
GOOGLE_PASS = os.getenv("GOOGLE_PASS")
SENDER_EMAIL = os.getenv("SENDER_EMAIL")
RECEIVER_EMAIL = os.getenv("RECEIVER_EMAIL")
PUSHOVER_USER = os.getenv("PUSHOVER_USER")
PUSHOVER_TOKEN = os.getenv("PUSHOVER_TOKEN")
ENVIRONMENT = os.getenv("ENVIRONMENT", "dev")
SCRIPT_VERSION = os.getenv("SCRIPT_VERSION", "2.0")
LOGGING_ENDPOINT = os.getenv("LOGGING_ENDPOINT", "https://gakai.co/api/event")
CLIENT_API_TOKEN = os.getenv("CLIENT_API_TOKEN")
CF_TOKEN = os.getenv("CF_TOKEN")
CF_ZONE = os.getenv("CF_ZONE", "example.com")
CF_SUBDOMAIN = os.getenv("CF_SUBDOMAIN", "matrix")
TRACKER_FILE = "jnd_IPUpdate_tracker.json"

CF_HEADERS = {
    "Authorization": f"Bearer {CF_TOKEN}",
    "Content-Type": "application/json"
}

def log(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")

def check_ip():
    return requests.get('https://api.ipify.org').text.strip()

def get_geo(ip):
    return requests.get(f'http://ip-api.com/json/{ip}').json()

def update_cloudflare_dns(ip):
    log("☁️ Updating Cloudflare DNS...")
    zone = requests.get(f"https://api.cloudflare.com/client/v4/zones?name={CF_ZONE}", headers=CF_HEADERS).json()
    zone_id = zone["result"][0]["id"]

    record = requests.get(f"https://api.cloudflare.com/client/v4/zones/{zone_id}/dns_records?name={CF_SUBDOMAIN}.{CF_ZONE}", headers=CF_HEADERS).json()
    record_id = record["result"][0]["id"]
    current_ip = record["result"][0]["content"]

    if current_ip == ip:
        log(f"✅ Cloudflare DNS already set to {ip}")
        return False

    update = requests.put(
        f"https://api.cloudflare.com/client/v4/zones/{zone_id}/dns_records/{record_id}",
        headers=CF_HEADERS,
        json={
            "type": "A",
            "name": f"{CF_SUBDOMAIN}.{CF_ZONE}",
            "content": ip,
            "ttl": 120,
            "proxied": False
        }).json()

    if update.get("success"):
        log(f"✅ Cloudflare DNS updated to {ip}")
        return True
    else:
        log(f"❌ Failed to update DNS: {update}")
        return False

def delta_t(seconds):
    if seconds < 60:
        return f"{seconds:.1f} seconds"
    minutes = seconds / 60
    if minutes < 60:
        return f"{minutes:.1f} minutes"
    hours = minutes / 60
    if hours < 24:
        return f"{hours:.1f} hours"
    return f"{hours / 24:.1f} days"

def load_previous_data():
    if os.path.exists(TRACKER_FILE):
        with open(TRACKER_FILE, 'r') as f:
            return json.load(f)
    return None

# === MAIN ===
if __name__ == '__main__':
    log("🚀 Script started")
    start = timeit.default_timer()
    now = datetime.now(timezone.utc)
    timestamp = now.strftime("%Y-%m-%dT%H:%M:%SZ")
    hostname = socket.gethostname()
    os_name = sys.platform
    ip = check_ip()
    location = get_geo(ip)

    log(f"🖥️ OS: {os_name}")
    log(f"🌐 IP: {ip}")
    log(f"📍 Location: {location.get('city', 'Unknown')}, {location.get('country', 'Unknown')}")

    data = load_previous_data()
    updated = False
    media_sent = []
    errors = ""

    if not data or ip != data['new-status']['new-ip']:
        log("🔄 IP has changed or no record exists")
        try:
            send_email(ip, timestamp, os_name, location, SENDER_EMAIL, RECEIVER_EMAIL, GOOGLE_PASS)
            media_sent.append("email")
        except Exception as e:
            errors += f"Email error: {e}; "

        try:
            send_push(PUSHOVER_USER, PUSHOVER_TOKEN, ip, timestamp, os_name, location)
            media_sent.append("push")
        except Exception as e:
            errors += f"Push error: {e}; "

        try:
            if update_cloudflare_dns(ip):
                media_sent.append("cloudflare")
        except Exception as e:
            errors += f"Cloudflare error: {e}; "

        updated = True

    new_ts = now.timestamp()
    old_ts = data['new-status']['new-ts'] if data else new_ts
    time_diff = delta_t(new_ts - old_ts)

    state = {
        "last-run": {
            "processDate": timestamp,
            "os": os_name,
            "ip-update": updated,
            "location": location,
            "processTime": timeit.default_timer() - start,
            "time-delta": time_diff,
            "notification-sent": timestamp
        },
        "new-status": {
            "new-date": timestamp,
            "new-ip": ip,
            "new-ts": new_ts
        },
        "old-status": data["new-status"] if data else {}
    }

    with open(TRACKER_FILE, 'w') as f:
        json.dump(state, f, indent=2)

    log("📡 Sending log to remote API...")
    try:
        response = requests.post(LOGGING_ENDPOINT, headers={
            "Authorization": f"Bearer {CLIENT_API_TOKEN}",
            "Content-Type": "application/json"
        }, json={
            "meta": {
                "project": "gakai.co",
                "db": "serviceDashboard",
                "collection": "clientStatus"
            },
            "payload": {
                "timestamp": timestamp,
                "duration": state['last-run']['processTime'],
                "success": True,
                "device": "Ubuntu-Hyotoko",
                "media": media_sent,
                "script_name": SCRIPT_NAME,
                "script_version": SCRIPT_VERSION,
                "environment": ENVIRONMENT,
                "error_details": errors,
                "changes_count": 1 if updated else 0,
                "host": hostname,
                "process_id": os.getpid(),
                "correlation_id": str(uuid.uuid4())
            }
        }, timeout=5)

        if response.status_code in [200, 201]:
            log("✅ Remote logging success")
        else:
            log(f"⚠️ Logging failed: {response.status_code} {response.text}")
    except Exception as e:
        log(f"🚫 Logging exception: {e}")

    log("🏁 Script finished")
