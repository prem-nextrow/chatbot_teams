from aiohttp import web
from botbuilder.schema import Activity
import requests
from dotenv import load_dotenv
import os
load_dotenv()
from langchain_openai import AzureChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage


llm = AzureChatOpenAI(
    azure_endpoint=os.getenv("AZURE_END_POINT"),   
    api_version=os.getenv("AZURE_VERSION"),       
    azure_deployment=os.getenv("AZURE_DEPLOYMENT"),
    api_key=os.getenv("AZURE_API_KEY"),           
    temperature=0.7
)


def get_access_token(Tenant_Id):
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


def send_reply(activity, reply_text):
  
    service_url = activity["serviceUrl"].rstrip("/")
    conversation_id = activity["conversation"]["id"]
    tenant_id = activity["conversation"]["tenantId"]
    activity_id = activity["id"]
    token = get_access_token(tenant_id)
    if not token:
        return

    url = f"{service_url}/v3/conversations/{conversation_id}/activities/{activity_id}"
    payload = {
        "type": "message",
        "from": activity["recipient"],
        "conversation": activity["conversation"],
        "recipient": activity["from"],
        "replyToId": activity_id,
        "text": reply_text
    }

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    response = requests.post(url, json=payload, headers=headers)


async def messages(req: web.Request) -> web.Response:
    print("\n" + "="*60)

    body = await req.json()
    print(body)
    activity = Activity().deserialize(body)

    

    msg_type = body.get("type")
    if msg_type == "message":
        user_text = body.get("text", "")
        reply = llm.invoke([SystemMessage(content="you are a an ai which can answer for any damn question in simplest form and can also talk in such a way like human "),HumanMessage(content=user_text)])
        send_reply(body,reply.content)

    return web.Response(status=200)

app = web.Application()
app.router.add_post("/app/messages", messages)

if __name__ == "__main__":
    web.run_app(app, host="127.0.0.1", port=3030)