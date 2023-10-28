#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ip_udate.py
# Google hyotoko pass: qqzugdeqjpvzvoge

import json
from requests import get
import smtplib, ssl
from email.message import EmailMessage
from datetime import datetime

def check_ip ():
    ip = get('https://api.ipify.org').text
    # print('My public IP address is: {}'.format(ip))
    return ip

def send_email (currentIP,date):
    port = 465  # For SSL
    smtp_server = "smtp.gmail.com"
    sender_email = "tadeubanzato@gmail.com"  # Enter your address
    receiver_email = "tadeubanzato@gmail.com"  # Enter receiver address
    password = "qqzugdeqjpvzvoge"

    msg = EmailMessage()
    msg.set_content(f"Hyotoko's IP was updated by the ISP, make sure to use the most updated version on your VPN.\n\nLast check was: {date}\nNew IP is: {currentIP}\n\n")
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
    
    # returns JSON object as 
    # a dictionary
    data = json.load(f)
    f.close()
    return data


if __name__ == '__main__':
    data = current_data()
    currentIP = check_ip ()

    if currentIP != data['old-ip']:
        send_email (currentIP,str(datetime.now()))
        data['last-check'] = str(datetime.now())
        data['old-ip'] = 'test'

        with open('data.json', 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=4)