# Python IP Check
This is a python script that will check the WAN IP of a network and check if the ISP has updated it or not.
I case of update/change the script will send an email to the designated email with the new IP.

The IP will be saved in JSON file in order to compare with the older IP and in case of change will send the notificatoin.

## JSON file
```json
{
    "check-status": {
        "os": "MacOS",
        "last-check": "2023-10-28 11:21:35.547486"
    },
    "update-status": {
        "last-update": "2023-10-28 11:21:35.547486",
        "old-ip": "123.123.123.123"
    }
}
```
As I'm using this script in multiple OS I also want to record which Operational System is executing the IP check.
`"os": "MacOS",`

The script records the last check even if it the IP has not changed, so you can verify if the script is working properly.
`"last-check": "2023-10-28 11:21:35.547486"`

The update status will show the last time any change has happened in the WAN IP.
```json
    "update-status": {
        "last-update": "2023-10-28 11:21:35.547486",
        "old-ip": "123.123.123.123"
    }
```
## Python Dependencies
Python dependencies are:
- smtplig
- ssl
- json
- sys
- requests
- datetime

```python
import smtplib, ssl, json, sys
from requests import get
from email.message import EmailMessage
from datetime import datetime
```
to install any dependencies use the command
```python
pip3 instal <depedency name>
```

### SMTP outgoing email using Google
The script is developed to use Google as the outgoing SMTP server.
```python
port = 465  # For SSL
smtp_server = "smtp.gmail.com"
sender_email = "youremail@gmail.com"  # Enter your address
receiver_email = "youremail@gmail.com"  # Enter receiver address
password = "16-digits-code-from-google"
```
To get the Google 16 digits password you need to go follow the next steps:
1. Login to your Google Account https://myaccount.google.com
2. Click on security on the left menu https://myaccount.google.com/security
3. Click on 2 Steps verification
4. Scroll down to App Password
5. Click on the > icon to add a new App
6. Create an app name and click Create
7. A popup window will show with your 16 digits password
Save this password so you can update on the IP Check Script

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
    sender_email = "tadeubanzato@gmail.com"  # Enter your address
    receiver_email = "tadeubanzato@gmail.com"  # Enter receiver address
    password = "qqzugdeqjpvzvoge"

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
