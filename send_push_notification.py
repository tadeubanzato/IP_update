# send_push_notification.py

import requests

def send_push(user,token,currentIP,date,os,location):
    print(f'Sending Push Notification to Pushover')
    payload = {"message": f'New Hyotoko IP: {currentIP}\nLocation: {location["city"]} last update: {date.strftime("%D")}', "user": user, "token": token}
    requests.post('https://api.pushover.net/1/messages.json', data=payload, headers={'User-Agent': 'This is a test'})