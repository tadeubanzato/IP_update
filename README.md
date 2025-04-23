# 🌐 Python Dynamic IP Monitor (Private Use)

This is a private-use Python script that monitors your public WAN IP address and performs the following actions if it changes:

- Sends a notification email using Gmail (App Passwords)
- Sends an optional Pushover push notification
- Updates a subdomain A record in **Cloudflare DNS** via API (acts as a DDNS client)
- Logs all events and metadata to a local JSON file
- Optionally logs to a remote API endpoint
- Can be scheduled as a background `systemd` timer service on Linux

---

## 📦 Dependencies

Install dependencies using:

```bash
pip install -r requirements.txt
```

### Required Packages:

- `requests`
- `python-dotenv`

---

## 🔐 .env Configuration

Create a `.env` file in the root directory:

```ini
GOOGLE_PASS=your_google_16_digit_password
SENDER_EMAIL=your_email@gmail.com
RECEIVER_EMAIL=recipient_email@example.com

PUSHOVER_USER=your_pushover_user_key
PUSHOVER_TOKEN=your_pushover_api_token

CLIENT_API_TOKEN=your_api_logging_token
LOGGING_ENDPOINT=https://yourdomain.com/api/event

CF_TOKEN=your_cloudflare_api_token
CF_ZONE=example.com
CF_SUBDOMAIN=matrix

ENVIRONMENT=production
SCRIPT_VERSION=2.0
```

To get a Google App Password:
1. Enable 2FA on your Google account
2. Go to: https://myaccount.google.com/apppasswords
3. Create a new password for "Mail"
4. Copy and paste the 16-digit password into `.env`

---

## 📁 Tracker File: `jnd_IPUpdate_tracker.json`

Tracks new and old IPs, location info, and timestamps:

```json
{
  "last-run": {
    "processDate": "2025-04-23T12:34:56Z",
    "os": "Linux",
    "ip-update": true,
    "location": {
      "city": "Redmond",
      "country": "US"
    },
    "processTime": 0.42,
    "time-delta": "28.11 seconds",
    "notification-sent": "2025-04-23T12:34:56Z"
  },
  "new-status": {
    "new-date": "2025-04-23T12:34:56Z",
    "new-ip": "203.0.113.5",
    "new-ts": 1713890000.123456
  },
  "old-status": {
    "new-ip": "203.0.113.4",
    "new-date": "2025-04-23T12:00:00Z",
    "new-ts": 1713888000.987654
  }
}
```

---

## 📫 Email Module

Uses Gmail with App Passwords to notify you of an IP change. Moved to `send_email_notification.py`.

---

## ☁️ Cloudflare DDNS Integration

This script updates a **specific subdomain** using your Cloudflare API token. No third-party DDNS services required — it's a direct integration with Cloudflare’s official API.

---

## 🧩 File Structure

```
.
├── ip_update.py                 # Main orchestrator script
├── send_email_notification.py  # Email notification logic
├── send_push_notification.py   # Optional push notification handler
├── jnd_IPUpdate_tracker.json   # Local IP tracking file
├── .env                         # Environment variables
└── requirements.txt             # Python dependencies
```

---

## 🔄 Run Every 15 Minutes (via systemd)

### Service File

`/etc/systemd/system/ip_update.service`

```ini
[Unit]
Description=IP Update + Cloudflare DDNS Script
Wants=network-online.target
After=network-online.target

[Service]
Type=simple
ExecStart=/usr/bin/python3 /usr/local/bin/ip_update.py
WorkingDirectory=/usr/local/bin
StandardOutput=journal
StandardError=journal
Restart=on-failure
```

### Timer File

`/etc/systemd/system/ip_update.timer`

```ini
[Unit]
Description=Run IP update script every 15 minutes

[Timer]
OnBootSec=5min
OnUnitActiveSec=15min
AccuracySec=1s
Persistent=true

[Install]
WantedBy=timers.target
```

### Enable & Start

```bash
sudo systemctl daemon-reexec
sudo systemctl daemon-reload
sudo systemctl enable --now ip_update.timer
```

---

## 🧪 Monitoring & Logs

```bash
# Check if timer is active
systemctl list-timers --all | grep ip_update

# View script logs
journalctl -u ip_update.service -f
```

---

## 📌 Notes

- 🔒 This script is intended for **personal/private use** only.
- No root access required unless writing to protected directories.
- Runs well on Ubuntu/Debian-based systems.
