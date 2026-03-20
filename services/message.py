
import requests
from dotenv import load_dotenv
import os
load_dotenv()
from langchain_core.messages import HumanMessage
from agents.model import create_mcp_agent,llm_messages
from services.tockens import get_access_token,google_tokens


async def process_slack_message(user_message, channel):
    agent = await create_mcp_agent()
    BOT_TOKEN = os.getenv("SLACK_BOT_TOKEN")
    bot_reply = await llm_messages(agent, user_message, channel)

    if bot_reply:
        requests.post(
            "https://slack.com/api/chat.postMessage",
            headers={
                "Authorization": f"Bearer {BOT_TOKEN}",
                "Content-Type": "application/json"
            },
            json={
                "channel": channel,
                "text": bot_reply
            }
        )

async def process_teams_message(activity):

    service_url = activity["serviceUrl"].rstrip("/")
    conversation_id = activity["conversation"]["id"]
    tenant_id = activity["conversation"]["tenantId"]
    activity_id = activity["id"]
    msg_type = activity.get("type")

    if msg_type != "message":
        return

    user_text = activity.get("text", "")


    token = await get_access_token(tenant_id)
    if not token:
        return


    agent = await create_mcp_agent()


    reply_text = await llm_messages(agent, user_text, conversation_id)

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

    requests.post(url, json=payload, headers=headers)


async def google_process_message(data):
    space_name = data["chat"]["messagePayload"]["space"]["name"]
    thread_name = data["chat"]["messagePayload"]["message"]["thread"]["name"]
    mytext = data["chat"]["messagePayload"]["message"]["text"]
    chat_service =  await  google_tokens()
    message = {
        "text": mytext,
        "thread": {"name": thread_name} 
    }
    
    chat_service.spaces().messages().create(
        parent=space_name,
        body=message,


    ).execute()
   