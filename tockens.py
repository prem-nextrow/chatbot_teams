import requests
import os
from dotenv import load_dotenv

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