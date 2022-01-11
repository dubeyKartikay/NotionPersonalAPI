import pickle
import json
import time
from datetime import datetime, timedelta
from pprint import pprint

from requests.api import head

from apiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
import requests

# Getting the google api ready
creds = pickle.load(open("google_creds.pkl","rb"))
service = build('calendar', 'v3', credentials=creds)


# Getting the notion api ready
with open("APIkey.json","r") as f:
        apiKey = json.load(f)["SyncCourseToGC_Notion"]
auth_header = {"Authorization":f'Bearer {apiKey}',"Notion-Version":"2021-08-16" ,"Content-Type": "application/json"}

with open("notion_page_properties_id.json","r") as f:
        ids_of_properties = json.load(f)

database_id = "8312731af42044b6908b8c76e19323d0"


def poll():
    filters = {"filter":{"property":"SyncToCalendar","checkbox":{"equals":True}}}
    print("Pollig started")
    while True:
        res = requests.post(f"https://api.notion.com/v1/databases/{database_id}/query",headers=auth_header,data=json.dumps(filters)).json()
        print("Polling is going on!")
        if res["results"] != []:
            main(res)
        time.sleep(60)

def error_check(res):
    if res.status_code != 200:
      raise Exception("API Error ! in Get_page_data",res.json())  

def get_page_propertiy_responses(page_id,ids_of_properties):
  response ={}
  for key,value in ids_of_properties.items():
    response[key] = requests.get(f"https://api.notion.com/v1/pages/{page_id}/properties/{value}",headers=auth_header)
    error_check(response[key])
    time.sleep(0.5)

  return response

def get_page_data(page_id):
    page_data = {}
    res = get_page_propertiy_responses(page_id,ids_of_properties)

    page_data["Due Date"] =  datetime.strptime(res["Due Date"].json()['date']['start'],"%Y-%m-%dT%H:%M:%S.%f%z") 
    page_data["Class Code"] = res["Class Code"].json()['select']['name']
    page_data["Type"] = res["Type"].json()['select']['name']
    page_data["Name"] = res["Name"].json()['results'][0]['title']['plain_text']
    page_data["page_id"] = page_id
    page_data["notion_page_url"] = f"https://www.notion.so/{page_id.replace('-','')}"

    return page_data

def mark_as_done(page_id):
  data = {
  "properties": {
    ids_of_properties["SyncToCalendar"]: { "checkbox":False }
  }
}
  res = requests.patch(f"https://api.notion.com/v1/pages/{page_id}",headers=auth_header,data=json.dumps(data))
  print(res.status_code)
  pprint(res.json())


def publish_event_to_GC(page_data):
    start_time = page_data["Due Date"]-timedelta(hours=3)

    event = {
  'summary': f'{page_data["Name"]} form {page_data["Class Code"]}' ,
  'description': page_data["notion_page_url"],
  'start': {
    'dateTime':start_time.strftime("%Y-%m-%dT%H:%M:%S"),
    'timeZone': 'Asia/Kolkata',
  },
  'end': {
    'dateTime': page_data["Due Date"].strftime("%Y-%m-%dT%H:%M:%S") ,
    'timeZone': 'Asia/Kolkata',
  },
  'reminders': {
    'useDefault': False,
    'overrides': [
      {'method': 'email', 'minutes': 5 *24 * 60},
      {'method': 'popup', 'minutes': 24 * 60} if page_data['Type'] == "Assignment" else "",
    ],
  },
}
    response_event = service.events().insert(calendarId='kartikaydubey11@gmail.com', body=event).execute()

    if response_event["status"]=="confirmed":
      mark_as_done(page_data["page_id"])
    time.sleep(0.1)

def main(new_pages):
    page_ids =[]
    for page in new_pages["results"]:
        page_ids.append(page["id"])

    events_data =[]
    print(page_ids)

    for page_id in page_ids:

        page_data = get_page_data(page_id)
        events_data.append(page_data)
    pprint(events_data)

    for event in events_data:
        publish_event_to_GC(event)
    # mark_as_done(page_ids)


poll()