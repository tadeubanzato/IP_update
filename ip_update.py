#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ip_udate.py

from push_notification import send_push # Push Notification Enablement

from dotenv import load_dotenv
import smtplib, ssl, json, sys, os, ssl, timeit
from requests import get
from email.message import EmailMessage
from datetime import datetime
import geocoder

## Don't foget to create a .env file with the information
## google-pass = GOOGLE APP PASSWORD (see readme)
## sender-email = SENDER EMAIL
## receiver-email = RECEIVER EMAIL

load_dotenv() # load .env information
sender = os.environ.get("sender-email")
receiver = os.environ.get("receiver-email")
google = os.environ.get("google-pass")
user = os.environ.get("pushover-user")
token = os.environ.get("pushover-token")

def check_ip ():
    ip = get('https://api.ipify.org').text
    print(f'This machine public IP address is: {ip}')
    return ip

def find_location():
    # g.city
    # g.state
    # g.state_long
    # g.country
    # g.country_long
    return geocoder.ip('me')

def send_email (currentIP,now,os,location):
    location = find_location()
    port = 465  # For SSL
    smtp_server = "smtp.gmail.com"
    sender_email = sender  # Load sender email from .env
    receiver_email = receiver  # Load receiver email from .env
    password = google # Load password from .env

    msg = EmailMessage()
    msg.set_content(f"Hello there,\n\nThis is an automated message from your server Hyotoko, do not reply.\nA new WAN IP was setup by your ISP in {location.city} - {location.country}, make sure to use the most updated IP on your VPN.\n\nLast update check: {now}\nCurrent location: {location.city}, {location.state} - {location.country}\nInformation checked from: {os}\n\nNew IP\n---------------------------\n{currentIP}\n---------------------------\n\nUpdates will check every 2 hours after any power outage or server fail to connect to the internet.")
    msg['Subject'] = f"⚡️ Hyotoko IP just got updated from {location.country}"
    msg['From'] = sender_email
    msg['To'] = receiver_email

    context = ssl.create_default_context()
    with smtplib.SMTP_SSL(smtp_server, port, context=context) as server:
        server.login(sender_email, password)
        server.send_message(msg, from_addr=sender_email, to_addrs=receiver_email)

def current_data ():
    # Opening JSON file
    f = open('data.json')
    # returns JSON object as a dictionary
    data = json.load(f)
    f.close()
    return data

def osCheck ():
    # Will check which OS has made the last check
    if sys.platform.startswith('linux'):
        os = "Linux"
    elif sys.platform.startswith('darwin'):
        os = "MacOS"
    elif sys.platform.startswith('win32'):
        os = "Windows"
    return os

def deltaT(delta):
    if round(delta.total_seconds(),2) < 60:
        deltax = f'{round(delta.total_seconds(),2)} seconds'
    elif round(delta.total_seconds(), 2) >= 60 and round(delta.total_seconds() / 60, 2) < 60:
        deltax = f'{round(delta.total_seconds() / 60, 2)} minutes'
    elif round(delta.total_seconds() / 60, 2) >= 60 and round(delta.total_seconds() / (60*60),2) < 24:
        deltax = f'{round(delta.total_seconds() / (60*60), 2)} hours'
    elif round(delta.total_seconds() / (60*60),2) >= 24:
        deltax = f'{round((delta.total_seconds() / (60*60)) / 24, 2)} days' 
    else:
        deltax = "Faz uma caralhada"
    return deltax

if __name__ == '__main__':

    start_time = timeit.default_timer() # Start Process Timer
    processDate = str(datetime.now()) # Current Process Time
    currentIP = check_ip () # Get Current IP
    runOS = osCheck() # Check OS (linux, mac, pc)
    location = find_location() # Get IP's Geolocation

    if not os.path.isfile('data.json'):
        end_time = timeit.default_timer()
        data = {"processDate": processDate, "processTime": end_time - start_time, "time-delta": "N/A", "os": runOS, "location": {"city": location.city, "state": location.state, "country": location.country}, "old-status": {"old-date": "N/A", "old-ts": "N/A", "old-ip": "N/A"}, "new-status": {"new-date": str(datetime.now()), "new-ts": datetime.now().timestamp(), "new-ip": currentIP}}
    else:
        data = current_data() # Get current JSON information
        if currentIP != data['new-status']['new-ip']:
            # Build New Data and Swap Old
            data['processDate'] = str(datetime.now())
            deltaT = str(deltaT(datetime.fromtimestamp(datetime.now().timestamp()) - datetime.fromtimestamp(data['new-status']['new-ts'])))
            data['time-delta'] = deltaT
            data['os'] = runOS
            data['location']['city'] = location.city
            data['location']['state'] = location.state
            data['location']['country'] = location.country

            # Swap Old Data
            data['old-status']['old-date'] = data['new-status']['new-date']
            data['old-status']['old-ts'] = data['new-status']['new-ts']
            data['old-status']['old-ip'] = data['new-status']['new-ip']

            # Update New Data
            data['new-status']['new-date'] = str(datetime.now())
            data['new-status']['new-ts'] = datetime.now().timestamp()
            data['new-status']['new-ip'] = currentIP

            # Send Email and Push Notification
            send_email (currentIP,datetime.now(),runOS,location)
            send_push (user,token,currentIP,datetime.now(),runOS,location)

            end_time = timeit.default_timer()
            data['processTime'] = end_time - start_time
        else:
            print(f'Current IP remains the same: {currentIP}')

    # Save JSON file with identation and UTF-8 encoding
    with open('data.json', 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)
