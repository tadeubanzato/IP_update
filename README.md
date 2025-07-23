
# 🌐 JND Cloudflare DDNS Updater

A lightweight Python service that keeps your Cloudflare DNS A record updated with your current public IP. It sends email and push notifications on IP changes and maintains a JSON history for auditing.

---

## 📁 Folder Structure

```
/home/tadeu/Python/IP_update/
├── .venv/                      # Python virtual environment
├── jnd_cloudflare_DDNS.py      # Main DDNS updater script
├── send_email_notification.py  # Email notification helper
├── send_push_notification.py   # Push notification helper
├── config.toml                 # Configuration file (enable/interval)
├── .env                        # Environment variables (API keys, secrets)
└── /var/lib/jnd/ip_history.json # IP history log (auto-created)
```

---

## ⚙️ Installation

### 1. Clone the repo
```bash
git clone <your-repo-url> ~/Python/IP_update
cd ~/Python/IP_update
```

### 2. Create virtual environment
```bash
sudo apt install python3-venv python3-pip -y
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Install dependencies
```bash
pip install -r requirements.txt
```
(or manually install)
```bash
pip install requests python-dotenv toml
```

---

## 📦 Configuration

### `.env` file
Create `.env` in `/home/tadeu/Python/IP_update`:
```
CF_TOKEN=your-cloudflare-api-token
CF_ZONE=yourdomain.com
CF_SUBDOMAIN=subdomain
LOGGING_ENDPOINT=https://your-logging-endpoint
CLIENT_API_TOKEN=your-client-api-token
SENDER_EMAIL=you@example.com
RECEIVER_EMAIL=you@example.com
GOOGLE_PASS=your-app-password
PUSHOVER_USER=pushover-user-key
PUSHOVER_TOKEN=pushover-app-token
ENVIRONMENT=production
```

### `config.toml`
```toml
[jnd_cloudflare_ddns]
enabled = true
interval_seconds = 120  # Check every 2 minutes
```

---

## 🖥️ systemd Service

### Create service file
```bash
sudo nano /etc/systemd/system/jnd_cloudflare_ddns.service
```

Paste:
```ini
[Unit]
Description=JND Cloudflare DDNS Updater
After=network-online.target
Wants=network-online.target
StartLimitIntervalSec=60
StartLimitBurst=3

[Service]
Type=simple
User=tadeu
WorkingDirectory=/home/tadeu/Python/IP_update
Environment=PYTHONUNBUFFERED=1
ExecStart=/home/tadeu/Python/IP_update/.venv/bin/python /home/tadeu/Python/IP_update/jnd_cloudflare_DDNS.py

Restart=on-failure
RestartSec=5

StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

### Enable & start
```bash
sudo systemctl daemon-reload
sudo systemctl enable --now jnd_cloudflare_ddns.service
```

---

## 📊 Monitoring
View logs:
```bash
journalctl -u jnd_cloudflare_ddns.service -f
```

Stop or restart:
```bash
sudo systemctl stop jnd_cloudflare_ddns.service
sudo systemctl restart jnd_cloudflare_ddns.service
```

---

## 📝 Features
✅ Detects IP change and updates Cloudflare  
✅ Sends Email + Push notifications (if Cloudflare update succeeds)  
✅ Logs each change with timestamp, location, Cloudflare update status  
✅ Configurable check interval via `config.toml`  
✅ Graceful shutdown with systemd  

---

## 📂 IP History Example
`/var/lib/jnd/ip_history.json`
```json
{
  "ip": "177.94.75.127",
  "timestamp": "2025-07-23T06:37:56.088955+00:00",
  "location": {
    "city": "Jundiaí",
    "country": "Brazil"
  },
  "cloudflare_update": "skipped"
}
```

---

## 🚀 Authors
- 🛠 Maintained by Tadeu
- 💡 Inspired by Home_IPUpdates service
