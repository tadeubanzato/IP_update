# Python IP Check
This is a python script that will check the WAN IP of a network and check if the ISP has updated it or not.
I case of update/change the script will send an email to the designated email with the new IP.

The IP will be saved in JSON file in order to compare with the older IP and in case of change will send the notificatoin.

## python-dotenv configuration
The credentials for this script are loaded using the python-detenv.
You need to create a `.env` file in the root folder of the project in the file you need to add the following lines with our sender email, receiver email and your google 16 digits password.

```python
google-pass = <google 16 digits password>
sender-email = <sender email>
receiver-email = <receiver email>
```

To loade the environment credentials from the .env file

```python
load_dotenv() # load .env information
sender = os.environ.get("sender-email")
receiver = os.environ.get("receiver-email")
google = os.environ.get("google-pass")
```

### To get your 16 digits password
To get the Google 16 digits password you need to go follow the next steps:
1. Login to your Google Account https://myaccount.google.com
2. Click on security on the left menu https://myaccount.google.com/security
3. Click on 2 Steps verification
4. Scroll down to App Password
5. Click on the > icon to add a new App
6. Create an app name and click Create
7. A popup window will show with your 16 digits password
Save this password so you can update on the IP Check Script
Direct link: https://myaccount.google.com/apppasswords?pli=1&rapt=AEjHL4O9FsLO4KIpWFl7veDJgjyfNA-2rPxmvgVm9E5NnlcK3kogsLF99FlMeGHUXDVorvZVuC1gYpsZR3mSk8Oy5CXqG7g9UA

## JSON file

The python script will update automatically the JSON file with the latest date the IP got updated, and will record the old IP information just for reference

```json
{
    "processTime": 1.3879907090013148,
    "time-delta": "28.11 seconds",
    "processDate": "2024-03-11 22:26:43.763455",
    "os": "MacOS",
    "location": {
        "city": "Redmond",
        "state": "Washington",
        "country": "US"
    },
    "old-status": {
        "old-date": "2024-03-11 22:26:14.586708",
        "old-ts": 1710221174.586719,
        "old-ip": "XX.XX.XX.XX"
    },
    "new-status": {
        "new-date": "2024-03-11 22:26:43.763442",
        "new-ts": 1710221203.763448,
        "new-ip": "XX.XX.XX.XX"
    }
}
```

## Python Dependencies
Python dependencies are:
* geocoder==1.38.1
* python-dotenv==1.0.0
* Requests==2.31.0

```python
import smtplib, ssl, json, sys
from requests import get
from email.message import EmailMessage
from datetime import datetime
```

To install dependencies simply run the below command in the same folder of the project
`pip install -r requirements.txt`

In case you want to install dependencies manually follow the pip command below.
```python
pip3 instal <depedency name>
```

The dependencies were easely exported using PipReqs https://pypi.org/project/pipreqs/

### check_ip function
The check IP function is pretty straightforward and will use https://api.ipify.org to check the device current WAM IP and return the string variable with it.
```python
def check_ip ():
    ip = get('https://api.ipify.org').text
    # print('My public IP address is: {}'.format(ip))
    return ip
```

### send_email function
This function is responsible to send the email with the new IP information once the IP gets changed by the ISP.
```python
def send_email (currentIP,now,os):
    port = 465  # For SSL
    smtp_server = "smtp.gmail.com"
    sender_email = sender  # Load sender email from .env
    receiver_email = receiver  # Load receiver email from .env
    password = google # Load password from .env

    msg = EmailMessage()
    msg.set_content(f"Hyotoko's IP was updated by the ISP, make sure to use the most updated version on your VPN.\n\nInformation checked from {os}\nLast updated check was: {now}\nNew IP is: {currentIP}\n\nUpdate checks happens every 2 hours, the IP might have updated sooner.")
    msg['Subject'] = f"📡 Hyotoko IP just got updated"
    msg['From'] = sender_email
    msg['To'] = receiver_email

    context = ssl.create_default_context()
    with smtplib.SMTP_SSL(smtp_server, port, context=context) as server:
        server.login(sender_email, password)
        server.send_message(msg, from_addr=sender_email, to_addrs=receiver_email)
```


### current_data function
This function will open the JSON file that is on the same folder of the Python script and will build a dictionary with the data so we can use during the check.

```python
def current_data ():
    # Opening JSON file
    f = open('data.json')
    # returns JSON object as a dictionary
    data = json.load(f)
    f.close()
    return data
```

### osCheck function
This function is build to check which Operational System is executing the IP check. The list is limited to Linux, MacOS or Windows, but you can check the documentation here https://ironpython-test.readthedocs.io/en/latest/library/sys.html#sys.platform

```python
def osCheck ():
    # Will check which OS has made the last check
    if sys.platform.startswith('linux'):
        os = "Linux"
    elif sys.platform.startswith('darwin'):
        os = "MacOS"
    elif sys.platform.startswith('win32'):
        os = "Windows"
    return os
```
# Main script execution
The script is essentially executed in the __main__ part of the code where essentially calls all the needed functions described above and check if the IP has changed or not.
If the IP did not change it will only update the `check-status` portion of the JSON file and nothing else.
If the IP has changed both `update-status` and `check-status` will change with the new data and the update check dates including OS.

```python
if __name__ == '__main__':
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
```



Create a Linux service by:
sudo nano /etc/systemd/system/ip_update.service

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

sudo nano /etc/systemd/system/ip_update.timer
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

sudo systemctl daemon-reexec
sudo systemctl daemon-reload
sudo systemctl enable --now ip_update.timer


# Check if timer is active
systemctl list-timers --all | grep ip_update

# Check script output
journalctl -u ip_update.service -f
