#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ip_udate.py

from push_notification import send_push # Push Notification Enablement

from dotenv import load_dotenv
import smtplib, ssl, json, sys, os, ssl, timeit
import requests
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

def check_ip():
    try: 
        response = requests.get('https://api.ipify.org') 
        if response.status_code == 200: 
            return response.text 
        else: 
            return "Error: Unable to retrieve public IP address" 
    except Exception as e: 
        return f"Error: {e}" 

def find_location():
    # g.city
    # g.state
    # g.state_long
    # g.country
    # g.country_long
    try:
        location = geocoder.ip('me')
        return location
    except Exception as e: 
        return f"Error: {e}"
    

def get_geoL(currentIP):
    # GeoLocation from https://ip-api.com/docs/api:json
    try:
        geoResp = requests.get(f'http://ip-api.com/json/{currentIP}')
        return geoResp.json()
    except Exception as e: 
        return f"Error: {e}"
        

def send_email(currentIP,now,os,location):
    print(f'Sending email to: {receiver}')
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

def current_data():
    # Opening JSON file
    f = open('data.json')
    # returns JSON object as a dictionary
    data = json.load(f)
    f.close()
    return data

def osCheck():
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
    runOS = osCheck() # Check OS (linux, mac, pc)
    currentIP = check_ip() # Get Current IP
    location = get_geoL(currentIP) # Get IP's Geolocation

    if not os.path.isfile('data.json'):
        data = {"last-run":{"os":runOS, "ip-update": False, "processDate":processDate,"processTime":0,"time-delta":"N/A","notification-sent":str(datetime.now()),"location":location},"new-status":{"new-date":str(datetime.now()),"new-ts":datetime.now().timestamp(),"new-ip":check_ip ()},"old-status":{}}
    else:
        data = current_data() # Get current JSON information
        OldData={}
        if currentIP != data['new-status']['new-ip']:
            print(f'\n\nISP UPDATES\n\n{location["org"]} - updated your IP\nLast update: {datetime.now()}\nLocation: {location["city"]} - {location["region"]}, {location["countryCode"]}\n\nYour new IP:\n{"-"*13}\n{currentIP}\n{"-"*13}\n')

            # Build New Data and Swap Old
            data['last-run']['os'] = runOS
            data['last-run']['ip-update'] = True
            data['last-run']['processDate'] = processDate
            deltaT = str(deltaT(datetime.fromtimestamp(datetime.now().timestamp()) - datetime.fromtimestamp(data['new-status']['new-ts'])))
            data['last-run']['time-delta'] = deltaT
            data['last-run']['location'] = location

            # Send Email and Push Notification
            send_email (currentIP,datetime.now(),runOS,location)
            send_push (user,token,currentIP,datetime.now(),runOS,location)
            data['last-run']['notification-sent'] = str(datetime.now())

            # Swap Old Data
            # OldData = {processDate:{"old-date": data['new-status']['new-date'],"old-ts": data['new-status']['new-ts'],"old-ip": data['new-status']['new-ip']}}
            OldData = {"old-ts": data['new-status']['new-ts'],"old-ip": data['new-status']['new-ip']}
            data['old-status'][processDate] = OldData

            # Update New Data
            data['new-status']['new-date'] = processDate
            data['new-status']['new-ts'] = datetime.now().timestamp()
            data['new-status']['new-ip'] = currentIP

        else:
            data['last-run']['ip-update'] = False
            print(f'No IP changes right now.')

    # End time processing
    end_time = timeit.default_timer()
    data['last-run']['processTime'] = end_time - start_time

    # Save JSON file with identation and UTF-8 encoding
    with open('data.json', 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)
