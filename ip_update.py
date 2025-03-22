#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ip_update.py

import sys
import os
import json
import timeit
import requests
import smtplib, ssl
from email.message import EmailMessage
from datetime import datetime, timezone, timedelta
import socket
import uuid
from push_notification import send_push  # Push Notification Enablement
from dotenv import load_dotenv
from os.path import abspath, dirname

# Set working directory to the script's directory
os.chdir(dirname(abspath(__file__)))

# Load environment variables
load_dotenv()

# === Constants ===
SCRIPT_NAME = "ip_update"
GOOGLE_PASS = os.environ.get("GOOGLE_PASS")
SENDER_EMAIL = os.environ.get("SENDER_EMAIL")
RECEIVER_EMAIL = os.environ.get("RECEIVER_EMAIL")
PUSHOVER_USER = os.getenv("PUSHOVER_USER")
PUSHOVER_TOKEN = os.getenv("PUSHOVER_TOKEN")
ENVIRONMENT = os.getenv("ENVIRONMENT", "prod")
SCRIPT_VERSION = os.getenv("SCRIPT_VERSION", "1.1.3")
LOGGING_ENDPOINT = os.getenv("LOGGING_ENDPOINT", "https://gakai.co/api/event")
CLIENT_API_TOKEN = os.getenv("CLIENT_API_TOKEN")


def check_ip():
    try:
        response = requests.get('https://api.ipify.org')
        if response.status_code == 200:
            return response.text.strip()
        else:
            return "Error: Unable to retrieve public IP address"
    except Exception as e:
        return f"Error: {e}"


def get_geoL(currentIP):
    try:
        geoResp = requests.get(f'http://ip-api.com/json/{currentIP}')
        return geoResp.json()
    except Exception as e:
        return {"error": str(e)}


def send_email(currentIP, now, os_name, location):
    print(f'Sending email to: {RECEIVER_EMAIL}')
    port = 465
    smtp_server = "smtp.gmail.com"
    msg = EmailMessage()
    msg.set_content(
        f"Hello there,\n\nThis is an automated message from your server Hyotoko, do not reply.\n"
        f"A new WAN IP was set up by your ISP in {location.get('city', 'Unknown')} - {location.get('country', 'Unknown')}, "
        f"make sure to update your VPN with the most recent IP.\n\n"
        f"Last update check: {now}\n"
        f"Current location: {location.get('city', 'Unknown')}, {location.get('regionName', 'Unknown')} - {location.get('country', 'Unknown')}\n"
        f"Information checked from: {os_name}\n\n"
        f"New IP\n---------------------------\n{currentIP}\n---------------------------\n\n"
        f"Updates will check every 2 hours after any power outage or network disruption."
    )
    msg['Subject'] = f"⚡️ Hyotoko IP updated from {location.get('countryCode', 'XX')}"
    msg['From'] = SENDER_EMAIL
    msg['To'] = RECEIVER_EMAIL

    context = ssl.create_default_context()
    with smtplib.SMTP_SSL(smtp_server, port, context=context) as server:
        server.login(SENDER_EMAIL, GOOGLE_PASS)
        server.send_message(msg, from_addr=SENDER_EMAIL, to_addrs=RECEIVER_EMAIL)


def current_data():
    with open('data.json', 'r', encoding='utf-8') as f:
        return json.load(f)


def osCheck():
    if sys.platform.startswith('linux'):
        return "Linux"
    elif sys.platform.startswith('darwin'):
        return "MacOS"
    elif sys.platform.startswith('win32'):
        return "Windows"
    else:
        return "Unknown"


def deltaT(delta):
    seconds = round(delta.total_seconds(), 2)
    if seconds < 60:
        return f'{seconds} seconds'
    minutes = round(seconds / 60, 2)
    if minutes < 60:
        return f'{minutes} minutes'
    hours = round(minutes / 60, 2)
    if hours < 24:
        return f'{hours} hours'
    days = round(hours / 24, 2)
    return f'{days} days'


# === Main Process ===
if __name__ == '__main__':
    start_time = timeit.default_timer()
    processDate = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    runOS = osCheck()
    currentIP = check_ip()
    location = get_geoL(currentIP)

    error_details = ""
    media_sent = []
    ip_updated = False

    if not os.path.isfile('data.json'):
        data = {
            "last-run": {
                "os": runOS,
                "ip-update": False,
                "processDate": processDate,
                "processTime": 0,
                "time-delta": "N/A",
                "notification-sent": processDate,
                "location": location
            },
            "new-status": {
                "new-date": processDate,
                "new-ts": datetime.now(timezone.utc).timestamp(),
                "new-ip": currentIP
            },
            "old-status": {}
        }
    else:
        data = current_data()
        if currentIP != data['new-status']['new-ip']:
            print(f"\n\nISP UPDATES\n\n{location.get('org', 'Unknown')} has updated your IP.\n"
                  f"Last update: {datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')}\n"
                  f"Location: {location.get('city', 'Unknown')} - {location.get('region', 'Unknown')}, {location.get('countryCode', 'XX')}\n\n"
                  f"New IP:\n{'-' * 13}\n{currentIP}\n{'-' * 13}\n")

            data['last-run']['os'] = runOS
            data['last-run']['ip-update'] = True
            data['last-run']['processDate'] = processDate
            previous_ts = data['new-status'].get('new-ts', datetime.now(timezone.utc).timestamp())
            delta_readable = deltaT(timedelta(seconds=datetime.now(timezone.utc).timestamp() - previous_ts))
            data['last-run']['time-delta'] = delta_readable
            data['last-run']['location'] = location

            try:
                send_email(currentIP, processDate, runOS, location)
                media_sent.append("email")
            except Exception as e:
                error_details += f"Email error: {e}; "

            try:
                send_push(PUSHOVER_USER, PUSHOVER_TOKEN, currentIP, processDate, runOS, location)
                media_sent.append("push")
            except Exception as e:
                error_details += f"Push error: {e}; "

            data['last-run']['notification-sent'] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
            data['old-status'][processDate] = {
                "old-ts": data['new-status']['new-ts'],
                "old-ip": data['new-status']['new-ip']
            }

            data['new-status']['new-date'] = processDate
            data['new-status']['new-ts'] = datetime.now(timezone.utc).timestamp()
            data['new-status']['new-ip'] = currentIP
            ip_updated = True
        else:
            data['last-run']['ip-update'] = False
            data['last-run']['location'] = location
            print("No IP changes right now.")

    end_time = timeit.default_timer()
    processTime = end_time - start_time
    data['last-run']['processTime'] = processTime

    # Save updated state
    with open('data.json', 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

    # === Prepare and send log to /api/event ===
    payload = {
        "timestamp": processDate,
        "duration": processTime,
        "success": True,
        "device": "Ubuntu-Hyotoko",
        "media": media_sent,
        "script_name": SCRIPT_NAME,
        "script_version": SCRIPT_VERSION,
        "environment": ENVIRONMENT,
        "error_details": error_details,
        "changes_count": 1 if ip_updated else 0,
        "host": socket.gethostname(),
        "process_id": os.getpid(),
        "correlation_id": str(uuid.uuid4())
    }

    event_payload = {
        "meta": {
            "project": "gakai.co",
            "db": "serviceDashboard",
            "collection": "clientStatus"
        },
        "payload": payload
    }

    headers = {
        "Authorization": f"Bearer {CLIENT_API_TOKEN}",
        "Content-Type": "application/json"
    }

    try:
        response = requests.post(LOGGING_ENDPOINT, headers=headers, json=event_payload, timeout=5)
        if response.status_code in [200, 201]:
            print("✅ Execution logged to /api/event")
        else:
            print(f"⚠️ Logging failed: {response.status_code} {response.text}")
    except Exception as e:
        print(f"🚫 Exception during logging: {e}")
