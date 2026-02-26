from aiohttp import web
from fastapi import FastAPI,Request,Response
import requests
from dotenv import load_dotenv
import os
load_dotenv()
from langchain_core.messages import HumanMessage
from model import chat_llm
from tockens import get_access_token



app = FastAPI(title="AI Bot",description="you can ask any questions to solve")
@app.post("/app/messages")
async def getMessages(req:Request):

    activity=await req.json()
    service_url = activity["serviceUrl"].rstrip("/")
    conversation_id = activity["conversation"]["id"]
    tenant_id = activity["conversation"]["tenantId"]
    activity_id = activity["id"]
    token = await get_access_token(tenant_id)


    if not token:
        return
    agent=await chat_llm()
    
    reply_text=await llm_messages(agent,activity,conversation_id)

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
    return Response(status_code=200)


async def llm_messages(agent,request,config_id):
    print("\n" + "="*60)

    msg_type = request.get("type")
    config={"configurable":{"thread_id":config_id}}
    if msg_type == "message":
        user_text = request.get("text", "")
        response=agent.invoke({"messages": [HumanMessage(content=user_text)]}, config)
        print("---------------------------------------")
        print(user_text,response["messages"][-1].content)
        return response["messages"][-1].content
    else:
        return "Hii I am the helpfull Assistant"



if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app",host="localhost",port=8003,reload=True)