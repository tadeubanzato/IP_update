# send_push_notification.py

import requests
from datetime import datetime

def send_push(user, token, current_ip, timestamp, os_name, location):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] 📲 Sending Pushover notification...")

    payload = {
        "message": (
            f"📡 New Hyotoko IP detected:\n\n"
            f"{current_ip}\n"
            f"Location: {location.get('city', 'Unknown')} - {location.get('country', 'Unknown')}\n"
            f"Time: {timestamp}"
        ),
        "title": "Hyotoko IP Change Alert",
        "user": user,
        "token": token,
        "priority": 0
    }

    response = requests.post("https://api.pushover.net/1/messages.json", data=payload)

    if response.status_code == 200:
        print(f"[{datetime.now().strftime('%H:%M:%S')}] ✅ Pushover notification sent.")
    else:
        print(f"[{datetime.now().strftime('%H:%M:%S')}] ❌ Failed to send Pushover notification: {response.status_code}")
        print(response.text)
