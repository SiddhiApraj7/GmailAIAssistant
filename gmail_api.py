from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
import os
from datetime import datetime, timezone, timedelta
import json
import pytz
import base64
import time
import requests
from agentic import EmailProcessingController
import re

# Authenticate and build Gmail API service
def gmail_authenticate():
    SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']
    creds = None
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        with open('token.json', 'w') as token:
            token.write(creds.to_json())

    service = build('gmail', 'v1', credentials=creds)
    return service

def fetch_emails(service, user_id):
    
    add_user_url = 'http://127.0.0.1:8000/add-user'
    update_user_url = 'http://127.0.0.1:8000/update-user'
    user = {
        "user_id": user_id
    }
    user_response = requests.post(add_user_url, json=user)
    if user_response.status_code not in [200, 201]:
        print(f"Failed to add user with id {user_id}. Status code: {user_response.status_code}")
        return
    
    # Define the IST timezone
    ist_timezone = pytz.timezone('Asia/Kolkata')
    
    # Get the current time in IST
    now_ist = datetime.now(ist_timezone)
    now_unix = int(time.mktime(now_ist.timetuple()))
    
    response_data = user_response.json()
    
    if user_response.status_code == 200:
        print(f"Code = 200")
        print(response_data.get("last_batch_time"))
        last_batch_time = response_data.get("last_batch_time")
        query = f'after:{last_batch_time} before:{now_unix}'
        print("Gmail API Query:", query)
    elif user_response.status_code == 201:
        print(f"Code = 201")
        six_hours_ago_ist = now_ist - timedelta(hours=6)
        six_h_unix = int(time.mktime(six_hours_ago_ist.timetuple()))
        print(six_h_unix)
        query = f'after:{six_h_unix} before:{now_unix}'
        print("Gmail API Query:", query)
    
    update_user_payload = {
        "user_id": user_id,
        "last_batch_time": now_unix
    }
    update_user_response = requests.post(update_user_url, json=update_user_payload)
    print(f"Status code for user update: {update_user_response.status_code}")

    # Call the Gmail API to fetch emails
    results = service.users().messages().list(userId='me', q=query).execute()
    messages = results.get('messages', [])
    
    emails_data = []

    if not messages:
        print("No messages found.")
    else:
        for message in messages:
            # Get the email details
            msg = service.users().messages().get(userId='me', id=message['id']).execute()

            # Extract the required details
            message_id = msg['id']
            subject = None
            body = None
            sender = None
            unique_id = None
            
            email_timestamp_ms = int(msg['internalDate'])
            email_timestamp_unix = email_timestamp_ms // 1000

            for header in msg['payload']['headers']:
                if header['name'] == 'Subject':
                    subject = header['value']
                elif header['name'] == 'From':
                    sender = header['value']
            
            email_match = re.search(r'<([^>]+)>', sender)
            if email_match:
                sender_email = email_match.group(1)
            else:
                sender_email = sender
        
            # Extract the plain body (handle both plain text and HTML formats)
            parts = msg['payload'].get('parts', [])
            if parts:
                for part in parts:
                    if part['mimeType'] == 'text/plain':
                        body = base64.urlsafe_b64decode(part['body']['data']).decode('utf-8')
                        #body = " ".join(body.split()[:3000])
                        break
                    elif part['mimeType'] == 'text/html' and body is None:
                        body = base64.urlsafe_b64decode(part['body']['data']).decode('utf-8')
                        #body = " ".join(body.split()[:3000])
            
            # Create a dictionary with message id, subject, and body
            unique_id = f"{email_timestamp_unix}_{sender_email}"
            email_data = {
                'subject': subject,
                'body': body,
                'timestamp': email_timestamp_unix,
                'sender': sender_email,
                "unique_id": unique_id
            }
            emails_data.append(email_data)
    
    # Save the collected emails data to a JSON file
    with open('emails.json', 'w') as f:
        json.dump(emails_data, f, indent=2)

    return emails_data

def batch_process_emails(user_id):
    with open('emails.json', 'r') as f:
        emails = json.load(f)
    
    search_email_url = 'http://127.0.0.1:8000/find-email'
    store_email_url = 'http://127.0.0.1:8000/store-email'
    
    email_processor = EmailProcessingController()
    
    for email in emails:
        unique_id = email.get('unique_id')
        if not unique_id:
            print("No unique_id found for this email. Skipping...")
            continue
        email_subject = email.get('subject')
        email_body = email.get('body')
        
        payload = {
            "user_id": user_id,
            "unique_id": unique_id
        }
        search_response = requests.get(search_email_url, json=payload)
        
        if search_response.status_code == 200:
            data = search_response.json()
            if data.get('exists'):
                print(f"Email with unique_id {unique_id} already exists. Skipping...")
                continue
        
        print(f"Email with unique_id {unique_id} does not exist. Processing...")
        
        json_response = email_processor.process_email(email_subject, email_body)
        #print(json_response)
        json_response["user_id"] = user_id
        json_response["unique_id"] = unique_id
        json_response["labeled"] = "False"
        json_response["labels"] = []
        store_response = requests.post(store_email_url, json=json_response)
                
        if store_response.status_code == 200:
            print(f"Email with unique_id {unique_id} stored successfully.")
        else:
            print(f"Failed to store email with unique_id {unique_id}. Status code: {store_response.status_code}")

"""if __name__ == '__main__':
    service = gmail_authenticate()
    batch_process_emails()
    #fetch_emails_for_testing(service)"""
