import requests

def send_push(user,token,currentIP,date,os,location):
    payload = {"message": f'New IP for Hyotoko in {location.city} - {currentIP} updated {date.strftime("%D")}', "user": user, "token": token}
    requests.post('https://api.pushover.net/1/messages.json', data=payload, headers={'User-Agent': 'This is a test'})
    print(f'New IP for Hyotoko in {location.city} - {currentIP} updated {date.strftime("%D")}')


# ### IFTTT
# import requests

# api_key = 'djsP4Oa3F1pydVqw78R3m7WxpemO0FS4L42OTxBiQ26'
# event = 'HyotokoPush'
# url = 'https://maker.ifttt.com/trigger/{e}/with/key/{k}/'.format(e=event,k=api_key)
# payload = {'value1': 'Hyotoko Notification', 'value2': 'value 2', 'value3': 'value3'}
# requests.post(url, data=payload)