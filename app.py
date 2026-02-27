from aiohttp import web
from fastapi import FastAPI,Request,Response,BackgroundTasks
import requests
from dotenv import load_dotenv
import os
load_dotenv()
from langchain_core.messages import HumanMessage
from model import chat_llm,llm_messages
from services.message import process_slack_message,process_teams_message
from tockens import get_access_token



app = FastAPI(title="AI Bot",description="you can ask any questions to solve")


@app.post("/app/teams/messages")
async def getTeamsMessages(req:Request):
    activity=await req.json()
    await process_teams_message(activity)
    return Response(status_code=200)


@app.post("/app/slack/messages")
async def getSlackMessage(req:Request,background_task:BackgroundTasks):
    data = await req.json()
    print(data)
    if(data.get("type")=="url_verification"):
        return {"challenge":data.get("challenge")}
    events = data.get("event")
    if(events.get("type")=="message" and not events.get("bot_id") and not events.get("subtype")):
        user_message = events.get("text")
        channel = events.get("channel")
        background_task.add_task(process_slack_message,user_message,channel)
    return "",200





if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app",host="localhost",port=8003,reload=True)