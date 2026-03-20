import requests
import os
from dotenv import load_dotenv
from google.oauth2 import service_account
from googleapiclient.discovery import build

load_dotenv()

async def get_access_token(Tenant_Id):
    url = f"https://login.microsoftonline.com/{Tenant_Id}/oauth2/v2.0/token"
    data = {
        "grant_type": "client_credentials",
        "client_id":os.getenv("APP_ID"),
        "client_secret":os.getenv("APP_PASSWORD"),
        "scope": "https://api.botframework.com/.default"
    }
    response = requests.post(url, data=data)
    print(f"[TOKEN] Status: {response.status_code}")
    if response.status_code != 200:
        print(f"[TOKEN] Error: {response.json()}")
        return None
    return response.json().get("access_token")

async def google_tokens():


  SCOPES = ['https://www.googleapis.com/auth/chat.bot']

  creds = service_account.Credentials.from_service_account_file(
    'the-method-488707-m2-54dbb5cc5454.json', scopes=SCOPES
)

# 3. Build the Chat API service
  chat_service = build('chat', 'v1', credentials=creds)
  return chat_service