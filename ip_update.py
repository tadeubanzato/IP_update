#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ip_udate.py
# Google hyotoko pass: qqzugdeqjpvzvoge

from dotenv import load_dotenv

import smtplib, ssl, json, sys, os
from requests import get
from email.message import EmailMessage
from datetime import datetime

def check_ip ():
    ip = get('https://api.ipify.org').text
    # print('My public IP address is: {}'.format(ip))
    return ip

def send_email (currentIP,now,os):
    port = 465  # For SSL
    smtp_server = "smtp.gmail.com"
    sender_email = os.environ.get("sender-email")  # Load sender email from .env
    receiver_email = os.environ.get("receiver-email")  # Load receiver email from .env
    password = os.environ.get("google-pass") # Load password from .env

    msg = EmailMessage()
    msg.set_content(f"Hyotoko's IP was updated by the ISP, make sure to use the most updated version on your VPN.\n\nInformation checked from {os}\nLast updated check was: {now}\nNew IP is: {currentIP}\n\nUpdate checks happens every 2 hours, the IP might have updated sooner.")
    msg['Subject'] = f"📡 Hyotoko IP just got updated"
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


if __name__ == '__main__':
    ## Don't foget to create a .env file with the information
    ## google-pass = GOOGLE APP PASSWORD (see readme)
    ## sender-email = SENDER EMAIL
    ## receiver-email = RECEIVER EMAIL

    load_dotenv() # load .env information

    data = current_data() # Load JSON function
    currentIP = check_ip () # Get current data
    os = osCheck () # Check OS
    now = str(datetime.now()) # Get current time

    data['check-status']['last-check'] = now
    data['check-status']['os'] = os

    if currentIP != data['update-status']['old-ip']:
        send_email (currentIP,now,os)
        data['update-status']['last-update'] = now
        data['update-status']['old-ip'] = currentIP

    with open('data.json', 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)