# send_email_notification.py

import smtplib
import ssl
from email.message import EmailMessage
from datetime import datetime

def send_email(ip, timestamp, os_name, location, sender_email, receiver_email, google_pass):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] 📧 Sending email...")

    msg = EmailMessage()
    msg.set_content(f"""Hello there,

This is an automated message from your server Hyotoko.

A new WAN IP was set up by your ISP in {location.get('city', 'Unknown')} - {location.get('country', 'Unknown')}.

Time: {timestamp}
Location: {location.get('city', 'Unknown')} - {location.get('regionName', 'Unknown')}, {location.get('country', 'Unknown')}
New IP:
----------------------
{ip}
----------------------

Stay secure,
Hyotoko Bot
""")
    msg['Subject'] = f"⚡️ Hyotoko IP updated ({location.get('countryCode', '??')})"
    msg['From'] = sender_email
    msg['To'] = receiver_email

    context = ssl.create_default_context()
    with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=context) as server:
        server.login(sender_email, google_pass)
        server.send_message(msg)
